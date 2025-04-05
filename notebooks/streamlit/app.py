import streamlit as st
from rag_pipelines import process_new_doc, process_existing_doc, QA_pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import os
import pandas as pd
import json
import types



# chargement du log des documents dispo en DB
def load_pp_traces(doc_category):
    st.markdown(f"### Documents {doc_category.upper()} chargés:", unsafe_allow_html=True)

    file_path="docs_hashes.json"
    exising_hashes={}
    if os.path.exists(file_path):                
        table=pd.read_json(file_path,).T
        table=table.sort_values("Date de création", ascending=False)
        table=table[table["doc_category"]==doc_category]
        table['Date de création'] = pd.to_datetime(table['Date de création']).dt.floor('s')
        if len(table)>0:
            st.dataframe(table.reset_index(drop=True))
            st.markdown("---")
        else:
            st.write("Aucun document pour le moment")
            st.markdown("---")

        return table
    else:        
        st.write("Aucun document pour le moment")
        st.markdown("---")
        return []



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
            messages=process_new_doc(uploaded_doc, doc_named_user, doc_category)
            
            for message in messages:
                st.markdown(message, unsafe_allow_html=True)

        #===============================================
        
        
        #========Interactions PP existant
        
        elif selected_doc_name:
            hash=df_existing_docs[df_existing_docs[f"Nom du doc"]==selected_doc_name].index.values[0]
            st.session_state["selected_pp_name"]=selected_doc_name
            for message in process_existing_doc(hash, selected_doc_name, doc_category):
                st.markdown(message, unsafe_allow_html=True)
        #===============================================


    st.title("IA financement 13")

    # menu
    st.sidebar.title("Sommaire")
    pages=[
        "Guide d'utilisation", 
        "Chargement PP",
        "Chargement asso",
        "Remplir un AAP", 
    ]
    st.session_state["pages"]=pages
    
    page=st.sidebar.radio("Aller vers", pages)
    st.session_state["selected_page"]=page
    
    # page d'accueil
    if page == pages[0]:
        st.write("### Guide")
        st.write("Faire des millions :)")









    # page chargement de la PP
    if page == pages[1]:
      
        build_ui_pp_asso('pp')


    if page == pages[2]:
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
        user_query=st.text_input(label="Votre question", placeholder="")
        st.session_state["user_query"]=user_query
        
        btn_process_user_query=st.button(label="Chercher", key="process_user_query")
        st.session_state["btn_process_user_query"]=btn_process_user_query
        #=======================================






        #============Gestion des interactions===========
        # vérifier qu'une question est posée
        if (user_query!="" and btn_process_user_query) or (uploaded_aap is not None and btn_process_aap):
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

                # QA_pipeline va retourner plusieurs types de messages

                # 1. la réponse sous forme de flux à diffuser sur l'UI, + la question initiale posée
                if isinstance(resp, dict) and "response_stream" in resp:
                    # rappel de la question
                    st.markdown(f"#### Question:\n", unsafe_allow_html=True)
                    st.markdown(resp["question"])
                    

                    st.markdown(f"#### Réponse:\n", unsafe_allow_html=True)                
                    
                    # 1. Créer un buffer pour accumuler la réponse
                    response_buffer = StringIO()
                    response_container = st.empty()  # Conteneur vide pour mise à jour dynamique

                    for chunk in resp["response_stream"]:
                    # Ajouter le token au buffer
                        response_buffer.write(chunk)
                        # Mettre à jour le conteneur avec le contenu accumulé
                        response_container.markdown(response_buffer.getvalue())

                    # 3. Récupérer la réponse complète
                    st.session_state["full_response"] = response_buffer.getvalue()
                    response_buffer.close()

                    
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

if __name__ == "__main__":
    main()