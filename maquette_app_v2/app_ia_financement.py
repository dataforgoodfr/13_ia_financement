import streamlit as st
import pathlib

# Font definition and global config is in the config.toml file

# --- CSS styling ---

def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

css_path = pathlib.Path("styles.css")
load_css(css_path)


# --- Sidebar ---
st.sidebar.title("Mon Compte")
st.sidebar.image("img/logo_D4G_no_text_back.png", width=100)
st.sidebar.markdown("---")


# buttons menu sidebar
menu = ["📝 Nouveau formulaire", "📚 Ma bibliothèque", "ⓘ Guide d'utilisation"]
menu_keys = ["formulaire", "biblio", "guide"]
for item, key in zip(menu, menu_keys):
    st.sidebar.button(item, key=key)    

# buttons sidebar - à propos
st.sidebar.button("ⓘ À propos", key="about") 
st.sidebar.image("img/github_logo.png", width=50)


# --- Main header ---
st.title("DossierIA+")
st.header("Facilitez vos réponses aux demandes de subventions")
st.write("""DossierIA+ pré-remplit automatiquement vos formulaires à partir de vos documents sources. **En quelques clics, votre dossier est prêt !**  
         Vous gardez le contrôle pour les ajuster facilement, tout en gagnant un temps précieux. Conçue par et pour les associations, cette solution vous aide à maximiser l’impact de vos actions en vous permettant de vous concentrer sur l’essentiel.""")
st.divider() 

# --- 1st step Project uploading documents ---
st.header("Etape 1 - Chargez vos documents")
st.subheader("Votre projet")

# Drag and drop multiple files
uploaded_project_files = st.file_uploader("**Chargez les documents présentant votre projet** (note de cadrage, dossier de présentation, budget, annexes, etc.) ", 
    accept_multiple_files=True, type=['pdf', 'docx', 'csv'], key='proj')
if uploaded_project_files is not None:
    for uploaded_file in uploaded_project_files:
        st.write(f"Fichier {uploaded_file.name} importé avec succès.")
                
# Renaming and upload 1 file
col1, col2 = st.columns([4, 1], vertical_alignment="center")
with col1:
    proj_name = st.text_input("**Titre de votre projet**", placeholder="Ex. : Prévention des zoonoses au Cambodge", key='proj_name')

with col2:
    upload_button = st.button("Importer", key='btn_proj')
    if upload_button:
        if proj_name:
            st.success(f"Projet '{proj_name}' importé avec succès.")
        else:
            st.warning("Veuillez saisir un titre de projet avant d'importer.")


# Uploading documents from the library 
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
uploaded_asso_files = st.file_uploader("**Chargez les documents présentant votre association** (présentation institutionnelle, statuts, rapports d’activité, etc.)) ", 
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
    response_files = st.file_uploader("**Chargez le formulaire à remplir** (format PDF, DOCX ou CSV)",  
                                     accept_multiple_files=True, type=['pdf', 'docx', 'csv'], key='response_template')
    if response_files is not None:
        for uploaded_file in response_files:
            st.write(f"Fichier {uploaded_file.name} importé avec succès.")
    
    response_text = st.text_input("**Ou posez une question manuellement ou à l'oral**", placeholder="Ex : Qui sont les bénéficiaires du projet ?", key='response_text')

    with st.expander("Paramètres"):
        st.slider("Niveau de détail", 1, 5, 3, key='detail_level')

    if st.button("Lancer la réponse", key='btn_response'):
        if response_files or response_text:
            st.success("Question traitée avec succès.")
        else:
            st.warning("Veuillez charger un fichier ou saisir une question.")



# --- Donate link button ---
st.link_button("Faire un don", "https://www.groupe-sos.org/faire-un-don/")