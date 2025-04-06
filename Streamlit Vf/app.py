import streamlit as st
from rag_pipelines import process_new_doc, process_existing_doc, QA_pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import os
import pandas as pd
import json
import types
from read_answer_aap import Read_Questions_in_docx
import tempfile
from pathlib import Path

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
        import page1_intro
        page1_intro.run()


    # page chargement de la PP
    if page == pages[1]:
      
        build_ui_pp_asso('pp')


    if page == pages[2]:
        build_ui_pp_asso('asso')


    # =============== Q/A AAP ou directe
    if page == pages[3]:
        st.write("#### Charger un AAP")
        uploaded_aap = st.file_uploader(
            label="Charger un AAP", 
            type=["docx", "json"], 
            accept_multiple_files=False, 
            key="uploader_aap"
        )
        st.session_state["uploaded_aap"] = uploaded_aap

        if st.button("Traiter", key="process_aap"):
            st.session_state["trigger_aap"] = True

        st.markdown("------------", unsafe_allow_html=True)

        st.write("#### Saisie manuelle")
        user_query = st.text_input(label="Votre question", placeholder="")
        st.session_state["user_query"] = user_query

        if st.button("Chercher", key="process_user_query"):
            st.session_state["trigger_query"] = True

        queries = []

        # === Saisie manuelle ===
        if st.session_state.get("trigger_query") and user_query.strip() != "":
            queries = [{"question": user_query}]
            st.session_state["trigger_query"] = False  # reset

        # === Traitement AAP (json/docx) ===
        elif st.session_state.get("trigger_aap") and uploaded_aap is not None:
            st.session_state["trigger_aap"] = False  # reset

            if uploaded_aap.name.endswith(".json"):
                raw_values = uploaded_aap.getvalue()
                queries = json.loads(raw_values)

            elif uploaded_aap.name.endswith(".docx"):
                st.info("📄 Traitement automatique du fichier AAP...")

                list_of_SizeWords_OK = [
                    " MAX", " MIN", " CARACT", " CHARACT", " LIGNE", " LINE", " SIGN", " PAGE",
                    " PAS EXC", " NOT EXCEED", " MOTS", " WORDS"
                ]
                list_of_SizeWords_KO = [
                    " SIGNAT", " MAXIMI", " MONTH", " MOIS", " ANS", " ANNé", " YEAR", " DAY", " JOUR",
                    " DURéE", " DURATION", " IMPACT", " AMOUNT", " MONTANT"
                ]
                TagQStart = "<>"
                TagQEnd = "</>"

                with tempfile.TemporaryDirectory(dir="temp") as tmpdirname:
                    file_path = os.path.join(tmpdirname, uploaded_aap.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_aap.getbuffer())
                    log_dir = os.path.join(tmpdirname, "logs")
                    os.makedirs(log_dir, exist_ok=True)

                    with st.spinner("🔍 Extraction des questions en cours..."):
                        extracted_questions = Read_Questions_in_docx(
                            PathFolderSource=tmpdirname + "/",
                            PathForOutputsAndLogs=log_dir,
                            list_of_SizeWords_OK=list_of_SizeWords_OK,
                            list_of_SizeWords_KO=list_of_SizeWords_KO,
                            TagQStart=TagQStart,
                            TagQEnd=TagQEnd
                        )

                    st.success("✅ Extraction terminée")
                    st.write(f"Nombre de questions détectées : {len(extracted_questions)}")
                    queries = extracted_questions

        # === Lancer QA_pipeline si des questions sont prêtes ===
        if queries:
            st.write("QA_pipeline lancé avec :", queries) #j affiche les questions censées etre extraites
            responses = QA_pipeline(queries)
            st.write("Réponses brutes reçues :", responses)# je n'ai pas de reponses

            for resp in responses:
                # ✅ Réponse avec un flux (stream)
                if isinstance(resp, dict) and "response_stream" in resp:
                    question_text = resp.get("question", "Question inconnue")
                    st.markdown(f"#### Question :\n{question_text}")

                    response_buffer = StringIO()
                    response_container = st.empty()

                    try:
                        for chunk in resp["response_stream"]:
                            response_buffer.write(chunk)
                            response_container.markdown(response_buffer.getvalue())
                        st.session_state["full_response"] = response_buffer.getvalue()
                    except Exception as e:
                        st.error(f"Erreur lors du stream de la réponse : {e}")
                    finally:
                        response_buffer.close()
                        st.markdown("-----", unsafe_allow_html=True)

                # ✅ Cas avec UID et métadonnées uniquement
                elif isinstance(resp, dict) and "uid" in resp:
                    st.markdown("##### Métadonnées :")
                    st.json(resp)

                # ✅ Cas où uniquement des sources sont retournées
                elif isinstance(resp, dict) and "sources" in resp:
                    if resp["sources"]:
                        st.markdown("#### Sources utilisées :")
                        for source in resp["sources"]:
                            st.markdown(f"**Source :** {source[0]}")
                            st.markdown(f"**Score :** {source[1]}")
                    else:
                        st.info("ℹ️ Aucun document source n’a été utilisé ou trouvé.")

                # ✅ Cas fallback si uniquement une question sans stream
                elif isinstance(resp, dict) and "question" in resp:
                    st.markdown(f"❓ Aucune réponse générée pour : **{resp['question']}**")

                # ✅ Cas string brut
                elif isinstance(resp, str):
                    st.markdown(resp, unsafe_allow_html=True)

if __name__ == "__main__":
    main()