import streamlit as st
from rag_pipelines import process_new_doc, process_existing_doc, QA_pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import os
import pandas as pd
import json
import types
from read_answer_aap import Read_Questions_in_docx, Write_Answers_in_docx
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

# correction erreur pytorch
import sys
import types

# Patch torch.classes pour éviter l'erreur de Streamlit
import torch

# torch.classes n'a pas de __path__, donc on le remplace par un faux module
if isinstance(torch.classes, types.ModuleType):
    torch.classes.__path__ = []
## fin correction


# chargement du log des documents dispo en DB
def load_pp_traces(doc_category: str):
    st.markdown(f"### Documents {doc_category.upper()} chargés:", unsafe_allow_html=True)

    # Get the directory of the current script (e.g., app.py)
    SCRIPT_DIR = Path(__file__).parent.resolve()

    # charger les hashes
    files_paths=[SCRIPT_DIR/ "hybridrag_hashes.json", SCRIPT_DIR/"graphrag_hashes.json"]
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

    st.set_page_config(
        page_title="IA pour répondre aux appels à projets",
        layout="wide"
    )
    
        # --- CSS personnalisé avec background bleu ciel clair ---
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&family=Roboto:wght@400;500&display=swap');
        
        /* Fond général et header */
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Roboto', sans-serif;
            background: linear-gradient(90deg, #ADD8E6 30%, #FEE7EC 90%);
            



        }
        [data-testid="stHeader"] {
            background: linear-gradient(90deg, #ADD8E6 30%, #FEE7EC 90%);
            
        }
        
        /* Bannière principale avec image centrée */
        .main-title {
            text-align: center;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            color: #003366;
        }
        .main-title h1 {
            font-family: 'Montserrat', sans-serif;
            font-size: 3rem;
            margin: 10px 0 0;
        }
        .main-title p {
            font-size: 1.2rem;
            margin: 8px 0 0;
        }
        /* Style pour l'image de la bannière : centrée et occupant 80% de la largeur */
        .main-title img {
            display: block;
            margin-left: auto;
            margin-right: auto;
            width: 80%;
            max-height: 300px;
            object-fit: contain;
        }
        
        /* Sidebar : on applique le dégradé à l'ensemble de la sidebar 
        et on centre les images */
        [data-testid="stSidebar"] {
        /*background: linear-gradient(90deg, #8EC0FA 30%, #FFDDE0 90%) !important;*/
        background: linear-gradient(90deg, #0D5C78 0%, #8EC0FA 50%, #2A6351 100%);
        padding: 20px;
        border-radius: 0 0 12px 0;
        }
        [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        }
        
        /* Bouton personnalisé */
        .stButton > button {
            linear-gradient(90deg, #6495ED 30%, #FFB6C1 90%) !important;
            color: #003366;
            border-radius: 8px;
            border: 2px solid #CCCCFF;
            padding: 10px 24px;
            font-size: 1.1rem;
            font-weight: 600;
            transition: background-color 0.3s ease, transform 0.2s ease;
        }
        .stButton > button:hover {
            background: linear-gradient(90deg, #6495ED 30%, #FFB6C1 90%) !important;
            transform: scale(1.03);
        }
        
        /* Espacement des colonnes */
        div[data-testid="column"] {
            padding: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    #================ Bannière principale affichant le titre et un sous-titre
    st.markdown(
        """
        <div class="main-title">
            <h1>IA pour répondre aux appels à projets</h1>
            <p>Optimisez vos réponses grâce à l'intelligence artificielle</p>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    with st.sidebar:
        st.image("SOS.png")
        st.image("D4G.png")
        st.write("### Projet DataForGood")
        

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

                #with tempfile.TemporaryDirectory(dir="temp") as tmpdirname:
                output_aap = "output_aap"
                safe_name = os.path.basename(uploaded_aap.name)  # Nettoyer le nom du fichier
                file_path = os.path.join(output_aap, safe_name)

                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "wb") as f:
                    f.write(uploaded_aap.getbuffer())

                log_dir = os.path.join(output_aap, "logs")
                os.makedirs(log_dir, exist_ok=True)

                with st.spinner("🔍 Extraction des questions en cours..."):
                    extracted_questions = Read_Questions_in_docx(
                        PathFolderSource=output_aap + "/",
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
            # responses = QA_pipeline(queries)
            # st.write("Réponses brutes reçues :", responses)# je n'ai pas de reponses

            all_responses_to_write = []

            for resp in QA_pipeline(queries):
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
                    if resp["question_close_or_open"] == "open":
                        resp["response"] = "Graphrag pipeline à venir"
                    else:
                        resp["response"] = st.session_state.get("full_response", "")

                    all_responses_to_write.append(resp) 

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

                # ✅ Cas string brut
                elif isinstance(resp, str):
                    st.markdown(resp, unsafe_allow_html=True)

            # ✅ Une seule écriture à la fin
            if all_responses_to_write:
                output_file_path, qa_file_path = Write_Answers_in_docx(
                    PathFolderSource=output_aap,
                    PathForOutputsAndLogs=output_aap,
                    List_UIDQuestionsSizeAnswer=all_responses_to_write
            )

                st.success("📄 Les réponses ont été écrites dans les documents.")

                # Bouton pour télécharger le fichier Word avec réponses
                with open(output_file_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Télécharger le document avec réponses",
                        data=file,
                        file_name=output_file_path.split("/")[-1],
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                # Bouton pour télécharger le fichier Q&A
                with open(qa_file_path, "rb") as file:
                    st.download_button(
                        label="⬇️ Télécharger le fichier Q&A",
                        data=file,
                        file_name=qa_file_path.split("/")[-1],
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                            
            

if __name__ == "__main__":
    main()