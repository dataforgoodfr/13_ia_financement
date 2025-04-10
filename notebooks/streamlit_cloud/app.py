import torch._classes
import asyncio
import nest_asyncio
import streamlit as st
from rag_pipelines import process_new_doc, process_existing_doc, QA_pipeline, update_hybrid_rag_wrapper
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import os
import pandas as pd
import json
import types


#=========corrections incompatibilités streamlit / event loop
#=============== nécessaire pour streaming des réponses graphRAG
# Patch the event loop to allow nested async calls
nest_asyncio.apply()
#==========fin

#=================== Correction conflit event loops torch/streamlit
# Save the original __getattr__ method
original_getattr = torch._classes._Classes.__getattr__

# Define a patched version to handle __path__
def patched_getattr(self, attr):
    if attr == "__path__":
        # Explicitly block access to __path__
        raise AttributeError(f"'{self.__class__.__name__}' has no attribute '__path__'")
    return original_getattr(self, attr)

# Apply the patch
torch._classes._Classes.__getattr__ = patched_getattr
#===============fin



# chargement du log des documents dispo en DB
def load_pp_traces(doc_category: str):
    st.markdown(f"### Documents {doc_category.upper()} chargés:", unsafe_allow_html=True)

    # charger les hashes
    files_paths=["hybridrag_hashes.json", "graphrag_hashes.json"]
    table=pd.DataFrame([])

    for file_path in files_paths:
        exising_hashes={}
        if os.path.exists(file_path):                
            t=pd.read_json(file_path,).T
            table=pd.concat([table, t], axis=0)

    # préparer les hashes
    if len(table)>0:
        # enlever les lignes en double hybrid rag/ graph rag
        table=table.drop_duplicates(subset=["Nom du doc","Titre auto","Taille du texte (en car)"])
        table=table.sort_values("Date de création", ascending=False)
        table=table[table["doc_category"]==doc_category].drop(columns=["rag_type"])
        table['Date de création'] = pd.to_datetime(table['Date de création']).dt.floor('s')

        st.dataframe(table.reset_index(drop=True))
        st.markdown("---")
        return table
        
    else:
        st.write("Aucun document pour le moment")
        st.markdown("---")
        return []

def stream_pathRAG_response(stream_resp, response_container):
    async def stream_response():
        response_buffer = StringIO()        
        
        # Get the existing event loop
        loop = asyncio.get_event_loop()
        
        # Process the async generator
        async for chunk in stream_resp["response_stream"]:
            response_buffer.write(chunk)
            response_container.markdown(response_buffer.getvalue())

        st.session_state["full_response"] = response_buffer.getvalue()
        response_buffer.close()


    # Run in Streamlit's existing event loop
    loop = asyncio.get_event_loop()
    loop.run_until_complete(stream_response())

def stream_hybridRAG_response(stream_resp, response_container):
    # 1. Créer un buffer pour accumuler la réponse
    response_buffer = StringIO()
    response_container = st.empty()  # Conteneur vide pour mise à jour dynamique

    for chunk in stream_resp["response_stream"]:
    # Ajouter le token au buffer
        response_buffer.write(chunk)
        # Mettre à jour le conteneur avec le contenu accumulé
        response_container.markdown(response_buffer.getvalue())

    # 3. Récupérer la réponse complète
    st.session_state["full_response"] = response_buffer.getvalue()
    response_buffer.close()



def main():
    
    def build_ui_pp_asso(doc_category: str):
        
        # charger traces des PP existantes:
        df_existing_docs= load_pp_traces(doc_category)




        #======== UI Charger un nouveau doc

        # UI définitive        
        uploaded_doc= st.file_uploader(label=f"Charger un document {doc_category.upper()}", type=["pdf","docx"], accept_multiple_files=True, key="uploader_doc")
        st.session_state[f"uploaded_{doc_category}"]=uploaded_doc

        session_state=st.session_state
        print(session_state)
        col1_new_doc, col2_new_doc = st.columns(2, vertical_alignment="bottom")
        with col1_new_doc:
            doc_named_user=st.text_input(label=f"Nom du document {doc_category.upper()}", placeholder="Saisie obligatoire")
        with col2_new_doc:
            btn_new_doc= st.button("Traiter", key=f'btn_{doc_category}')
            st.session_state["btn_new_doc"]=btn_new_doc


        st.markdown('<hr>', unsafe_allow_html=True)


        #===============================================





        #========UI Utiliser un doc existant
        st.write(f'### Utiliser un document {doc_category.upper()} existant')
        col4_existing_doc, col5_existing_doc = st.columns(2, vertical_alignment="bottom", )
        with col4_existing_doc:
            list_doc_names=[]
            if len(df_existing_docs)>0:
                list_doc_names=df_existing_docs[f"Nom du doc"].unique()
            
            selected_doc_name= st.selectbox(label=f"Choisir un document {doc_category}", options=list_doc_names)
        # with col5_existing_doc:
        #     btn_existing_doc= st.button(f"Charger", key=f"btn_process_{doc_category}")
        #================================================




        #========Interactions nouveau PP
        # définitif
        if uploaded_doc is not None and doc_named_user!="" and btn_new_doc:
            st.session_state[f"uploaded_{doc_category}"]=uploaded_doc
            with st.spinner("Wait for it...", show_time=True):
                messages=process_new_doc(uploaded_doc, doc_named_user, doc_category)
                
                for message in messages:
                    st.markdown(message, unsafe_allow_html=True)

        #===============================================
        
        
        #========Interactions PP existant
        
        elif selected_doc_name:
            hash=df_existing_docs[df_existing_docs[f"Nom du doc"]==selected_doc_name].index.values[0]
            st.session_state["selected_pp_name"]=selected_doc_name
            
            with st.spinner("Wait for it...", show_time=True):
                for message in process_existing_doc(hash, selected_doc_name, doc_category):
                    st.markdown(message, unsafe_allow_html=True)
        #===============================================


    st.title("IA financement 13")

    # menu
    st.sidebar.title("Sommaire")
    pages_map={
        "Guide d'utilisation": 0, 
        "Chargement PP": 1,
        "Chargement asso": 2,
        "Remplir un AAP": 3, 
        "Paramètres": 4, 
    }
    pages=[k for k in pages_map.keys()]

    #persistance
    index_sommaire=0
    if 'sidebar' in st.session_state:
        index_sommaire= pages_map[st.session_state["sidebar"]]
    
    page=st.sidebar.radio("Aller vers", pages, key="sidebar", index=index_sommaire)
    
    
    # page d'accueil
    if page == pages[0]:
        st.session_state["selected_page"]=page
        st.write("### Guide")
        st.write("Faire des millions :)")









    # page chargement de la PP
    if page == pages[1]:
        st.session_state["selected_page"]=page
      
        build_ui_pp_asso('pp')


    if page == pages[2]:
        st.session_state["selected_page"]=page
        build_ui_pp_asso('asso')


    # ===============Q/A AAP ou directe
    if page == pages[3]:        
        
        #==========UI questions AAP==========        
        st.write("#### Charger un AAP")
        uploaded_aap= st.file_uploader(label="Charger un AAP", type=["docx", "json"], accept_multiple_files=False, key="uploader_aap")
        st.session_state["uploaded_aap"]=uploaded_aap
        btn_process_aap=st.button(label="Traiter", key="process_aap")
        st.session_state["btn_process_aap"]=btn_process_aap
        st.markdown("------------", unsafe_allow_html=True)
        #=======================================
        





        #==========UI question directe==========
        
        st.write("#### Saisie manuelle")
        # rappel dernière question
        user_query=st.text_input(label="Votre question", placeholder="", value="")
        
        
        col_btn_userQuery, buf, col_reranker_select, col_top_k=st.columns([1, 0.5, 1, 1])
        with col_btn_userQuery:
            btn_process_user_query=st.button(label="Chercher", key="process_user_query")
        
        #=======================================


        #=========paramètres en cours

        if "selected_reranker" in st.session_state and st.session_state["selected_reranker"]!="":
            with col_reranker_select:
                st.write(f"""Used reranker: {st.session_state["selected_reranker"]}""")
        else:
            with col_reranker_select:
                st.write(f"Used reranker: specialized")

        if "top_k_docs_user" in st.session_state:
            with col_top_k:
                st.write(f"Used top_k documents: {st.session_state['top_k_docs_user']}")
        else:
            with col_top_k:
                st.write(f"Used top_k documents: {10}")



        #### rappel de la dernière Q/A 
        response_container = st.empty() 
        if "full_response" in st.session_state:         
            query_value=""
            if "user_query" in st.session_state:
                query_value=st.session_state["user_query"]

            # st.markdown(f"#### Réponse:\n", unsafe_allow_html=True)                                           
            response_container.markdown(f"""
                #### Question: 
                {query_value}
                \n
                #### Réponse:
                {st.session_state["full_response"]}
            """, unsafe_allow_html=True)




        #============Gestion des interactions===========
        # vérifier qu'une question est posée
        if (user_query!="" and btn_process_user_query) or (uploaded_aap is not None and btn_process_aap):
            #= reset de la réponse affichée
            response_container.markdown("")
            st.session_state["user_query"]=user_query
            #====== déterminer si requête manuelle ou process AAP
            #1. requête manuelle
            if btn_process_user_query:
                queries=[{"question": user_query}]
            #2. process AAP
            elif btn_process_aap:
                raw_values=uploaded_aap.getvalue()
                queries=json.loads(raw_values)

            #======parcourir les questions et les transmettre à QA pipeline
            for resp in QA_pipeline(queries):
                with st.spinner("Wait for it...", show_time=True):
                    # QA_pipeline va retourner plusieurs types de messages

                    # 1. la réponse sous forme de flux à diffuser sur l'UI, + la question initiale posée
                    if isinstance(resp, dict) and "response_stream" in resp:
                        # rappel de la question
                        st.markdown(f"#### Question:\n", unsafe_allow_html=True)
                        st.markdown(resp["question"])
                        

                        st.markdown(f"#### Réponse:\n", unsafe_allow_html=True)                
                        #response_container = st.empty()

                        # diffusion PathRag
                        if "pathrag_stream" in resp:
                            stream_pathRAG_response(stream_resp=resp, response_container = response_container)
                        
                        # diffusion hybrid RAG
                        elif "hybridrag_stream" in resp:       
                            stream_hybridRAG_response(stream_resp=resp, response_container = response_container)

                        
                        st.markdown("-----", unsafe_allow_html=True)

                        
                        
                    # 2. les sources utilisées par le rag
                    elif isinstance(resp, dict) and 'sources' in resp:
                        st.markdown(f"#### Sources:\n", unsafe_allow_html=True)
                        
                        for source in resp["sources"]:
                            st.markdown(f"**Source**:<br>{source[0]}", unsafe_allow_html=True)
                            st.markdown(f"**Score**: {source[1]}", unsafe_allow_html=True)

                    # 3. les métadonnées (uid, question, type), et la réponse complète du flux 1 ci dessus
                    elif isinstance(resp, dict) and 'uid' in resp:
                        resp["response"]=st.session_state["full_response"]
                        st.markdown(f"**Metadata**: {resp}", unsafe_allow_html=True)
                        print("metadata:", resp)
                    elif isinstance(resp, str):                    
                        st.markdown(f"{resp}", unsafe_allow_html=True)


    # ===============Paramètres
    elif page == pages[4]:
        
        st.markdown("### Paramètres de la chaîne hybride", unsafe_allow_html=True)
        st.markdown("""
            #### Reranker:
            Sert à noter la pertinence des fragments de documents correspondants à la question, seuls les plus pertinents sont envoyés au LLM.
                    
            * Le reranker 'specialized' est rapide et gratuit.
            * Le reranker 'llm' (gpt4o-mini adapté) est lent et payant, mais plus précis.
                    
            Changer de reranker si la réponse produite n'est pas satisfaisante

            #### Top K documents:
            Sert à déterminer le nombre de fragments de documents sélectionnés pour constituer le contexte présenté au LLM, après notation et classement.
                    
            * Réduire ce nombre permet d'augmenter la capacité du LLM à se concentrer sur un contexte précis, mais réduit aussi la diversité des sources, privant le LLM de la bonne information.
            * Augmenter ce nombre permet d'augmenter la diversé des sources et informations nécessaires pour répondre à la réponse, mais peut introduire d'avantage 
            de confusion pour le LLM qui se voit présenté un contexte plus large.

            Changer ce nombre si la réponse n'est pas satisfaisante        
            
            **Conseil**: Changer de reranker en priorité si la réponse produite n'est pas satisfaisante, et éviter de dépasser top K 14
                                        
        """)
        
        "st.session_state", st.session_state

        # rappel du reranker
        last_reranker=""
        reranker_map={"specialized":0, 'llm':1}
        if "selected_reranker" in st.session_state and st.session_state["selected_reranker"]!="":
            last_reranker=st.session_state["selected_reranker"]
        
        
        st.write(f"Dernier reranker utilisé: {last_reranker}")
        reranker=st.selectbox(
            "Changer de reranker",
            options=["specialized", "llm"],
        )

        # rappel du top K
        top_k_user_input=st.empty()
        if 'top_k_docs_user' in st.session_state:                        
            "avant", st.session_state["top_k_docs_user"]
            top_k_docs_selected= top_k_user_input.number_input(label="Top K documents", key="top_k_user_input", value=st.session_state["top_k_docs_user"], min_value=4, max_value=18)
            
        else:
            "avant", st.session_state["top_k_docs_user"]
            top_k_docs_selected= top_k_user_input.number_input(label="Top K documents", key="top_k_user_input",  value=10, min_value=4, max_value=18)
            
            
        st.session_state["top_k_docs_user"]=top_k_docs_selected
        "après", st.session_state["top_k_docs_user"]

        change_hybridrag_params=st.button("Mise à jour", key="update_hybrid_rag_params")

        if change_hybridrag_params:
            st.session_state["selected_reranker"]= reranker
            feedback= update_hybrid_rag_wrapper(reranker, top_k=top_k_docs_selected)
            st.write(f"""{feedback}""")
                    


if __name__ == "__main__":
    main()