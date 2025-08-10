# Import personal functions
from rag_pipelines import process_new_doc, process_existing_doc, QA_pipeline, update_hybrid_rag_wrapper
from graphrag_retriever import load_knowledgeGraph_vis
from read_answer_aap import Read_Questions_in_docx, Write_Answers_in_docx

# import langchain libraries
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# import other libraries
from io import StringIO
import asyncio
import nest_asyncio
import os
import pandas as pd
import json
from pathlib import Path
import streamlit as st

# pour télécharger l'AAP en docx
from docx import Document
from docx.shared import Pt
from io import BytesIO

# Patch torch.classes pour éviter l'erreur de Streamlit
import torch


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

# Get the directory of the current script (e.g., app.py)
# SL: add 1 more level parent because homepage is in pages folder
SCRIPT_DIR = Path(__file__).parent.parent.resolve()


#doc_category: the type of document, must be 'pp' or 'asso'


#=================== UI v2 Streamlit app
# Font definition and global config off the streamlit app is in the config.toml file

# --- CSS styling ---

def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path =SCRIPT_DIR/ "styles.css"
#css_path = pathlib.Path("styles.css")
load_css(css_path)


# --- Homepage config ---
st.set_page_config(
    page_title="DossierIA+",
    page_icon=":clipboard:",
    layout="wide",
    initial_sidebar_state="auto",
)

# --- Sidebar ---
st.sidebar.title("Mon Compte")
st.sidebar.image(SCRIPT_DIR/ "img/logo_D4G_no_text_back.png", width=100)
st.sidebar.markdown("**Bienvenue dans DossierIA+ !**")

# --- Main header ---
st.title("DossierIA+")
st.header("Facilitez vos réponses aux demandes de subventions")
st.write("""DossierIA+ pré-remplit automatiquement vos formulaires à partir de vos documents sources. **En quelques clics, votre dossier est prêt !**  
         Vous gardez le contrôle pour les ajuster facilement, tout en gagnant un temps précieux. Conçue par des bénévoles de Data For Good avec les associations du groupe SOS pour les associations, cette solution vous aide à maximiser l’impact de vos actions en vous permettant de vous concentrer sur l’essentiel.""")
st.divider() 

# --- 1st step Project uploading documents pp ---
# Notification zone if a document is uploaded in session state or not
zone_notif_doc_charge=st.empty()
if "current_pp_in_use" in st.session_state:
    zone_notif_doc_charge.success(f"""Document chargé: {st.session_state["current_pp_in_use"]}""")
else:
    zone_notif_doc_charge.warning(f"Veuillez charger un document projet")

st.header("Etape 1 - Chargez vos documents")
st.subheader("Votre projet")

# Drag and drop multiple files UI
uploaded_project_files = st.file_uploader("**Chargez les documents présentant votre projet** (note de cadrage, dossier de présentation, budget, annexes, etc.) ", 
    accept_multiple_files=True, type=['pdf', 'docx', 'csv'], key='uploader_proj')

if uploaded_project_files is not None:
    st.session_state["uploaded_pp"]=uploaded_project_files
    for uploaded_file in uploaded_project_files:
        st.write(f"Fichier {uploaded_file.name} importé avec succès.")
                
# Naming file, upload 1 file from the library and process uploaded file
col1, col2 = st.columns([4, 1], vertical_alignment="center")
with col1:
    proj_name = st.text_input("**Titre de votre projet**", placeholder="Ex. : Prévention des zoonoses au Cambodge", key='proj_name')

with col2:
    upload_button = st.button("Importer", key='btn_proj')
    st.session_state["upload_button"]=upload_button
    if upload_button:
        if proj_name and uploaded_project_files:
            st.session_state["uploaded_pp"]=uploaded_project_files
            with st.spinner("Wait for it...", show_time=True):
                for message in process_new_doc(uploaded_project_files, proj_name, "pp"):
                    st.markdown(message, unsafe_allow_html=True)

            st.session_state["current_pp_in_use"]=proj_name
            st.success(f"✅ Projet '{proj_name}' importé avec succès.")
            with zone_notif_doc_charge:
                    st.success(f"""Document chargé: {st.session_state[f"current_pp_in_use"]}""")
        else:
            st.warning("Veuillez saisir un titre de projet avant d'importer.")



# Uploading documents from the library UI
col1, col2 = st.columns([4, 1], vertical_alignment="center")
with col1:
    proj_lib = st.selectbox("Ou utilisez des documents de la bibliothèque", ["Présentation Projet Mahakam"], key='proj_lib')
with col2:
    upload_lib_button = st.button("Charger", key='btn_proj_lib')
    if upload_lib_button:
        st.success("Projet de la bibliothèque importé avec succès.")


        
# --- Association uploading documents ---
st.subheader("Votre association")

# Drag and drop multiple files
uploaded_asso_files = st.file_uploader("**Chargez les documents présentant votre association** (présentation institutionnelle, statuts, rapports d’activité, etc.) ", 
    accept_multiple_files=True, type=['pdf', 'docx', 'csv'], key='assoc')
if uploaded_asso_files is not None:
    for uploaded_file in uploaded_asso_files:
        st.write(f"Fichier {uploaded_file.name} importé avec succès.")
                
# Renaming and upload 1 file
col1, col2 = st.columns([4, 1], vertical_alignment="center")
with col1:
    assoc_name = st.text_input("**Nom associé aux fichiers**", placeholder="Ex : Présentation Forêts en Danger", key='assoc_name')
with col2:
    upload_button = st.button("Importer", key='btn_asso')
    if upload_button:
        if assoc_name:
            st.success(f"Projet '{assoc_name}' importé avec succès.")
        else:
            st.warning("Veuillez saisir un titre de projet avant d'importer.")

# Uploading documents from the library 
col1, col2 = st.columns([4, 1], vertical_alignment="center")
with col1:
    assoc_lib = st.selectbox("Ou utilisez des documents de la bibliothèque", ["Présentation Projet Mahakam"], key='assoc_lib')
with col2:
    upload_lib_button = st.button("Charger", key='btn_assoc_lib')
    if upload_lib_button:
        st.success("Projet de la bibliothèque importé avec succès.")
st.divider() 

# --- 2nd step Project proposal template ---
st.header("Etape 2 - Sélectionnez le formulaire à compléter")
with st.container(key='template_container'):
    response_files = st.file_uploader("**Chargez le formulaire à remplir** (format DOCX)",  
                                     accept_multiple_files=True, type='docx', key='response_template')
    if response_files is not None:
        for uploaded_file in response_files:
            st.write(f"Fichier {uploaded_file.name} importé avec succès.")
    
    response_text = st.text_input("**Ou posez une question manuellement**", placeholder="Ex : Qui sont les bénéficiaires du projet ?", key='response_text')

    with st.expander("Paramètres"):
        st.slider("Niveau de détail (réponse simple à détaillée)", 1, 5, 3, key='detail_level')

    if st.button("Lancer la réponse", key='btn_response'):
        if response_files or response_text:
            st.success("Question traitée avec succès.")
        else:
            st.warning("Veuillez charger un fichier ou saisir une question.")




# --- Donate and github link buttons ---
col1, col2 = st.columns(2)
with col1:
    st.html('<a class="github_link" href="https://github.com/dataforgoodfr/13_ia_financement/" target="_blank">ⓘ À propos de DossierIA+</a>')
with col2:
    st.html('<a class="donate_link" href="https://dataforgood.fr/docs/donation/" target="_blank">Faire un don ➚</a> ')


#=================== End UI v2 Streamlit app