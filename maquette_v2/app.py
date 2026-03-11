import streamlit as st

# --- Custom CSS ---
def local_css(css: str):
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

custom_css = r"""
/* Sidebar */
.sidebar .sidebar-content {
    background-color: #F2F2F2;
}
[data-testid="stSidebarNav"] {
    padding-top: 2rem;
}

/* Buttons */
.css-1emrehy.edgvbvh3 {
    background-color: #FF7F7F !important;
    color: white !important;
    border-radius: 0.5rem;
}

/* File Uploader */
.css-1kyxreq.egzxvld2 {
    border: 1px dashed #CCCCCC;
    border-radius: 0.5rem;
    padding: 1rem;
}

/* Containers */
.block-frame {
    padding: 1rem;
    margin-bottom: 2rem;
    border-bottom: 1px solid #E0E0E0;
}
"""

local_css(custom_css)

# --- Sidebar ---
st.sidebar.markdown("### Mon Compte")
st.sidebar.image("assets/logo_D4G.png", width=120)
st.sidebar.markdown("---")
menu = ["Nouveau formulaire", "Bibliothèque", "Guide d'utilisation"]
for item in menu:
    st.sidebar.button(item)

# st.sidebar.markdown("---")
# st.sidebar.markdown("[GitHub](https://github.com)")
# st.sidebar.markdown("\n---\n[À propos](#)")

# --- Main header ---
st.title("DossierIA+")
st.subheader("Facilitez vos réponses aux demandes de subventions")
st.write(
    "Facilitez vos réponses grâce à l'intelligence artificielle..."
)

# --- Projet & Association Section ---
col1, col2 = st.columns(2)
with col1:
    st.header("Votre projet")
    project_file = st.file_uploader("Ou faites glisser et déposez vos fichiers ici", type=['pdf', 'docx'], key='proj')
    proj_name = st.text_input("Nom associé aux fichiers", placeholder="Saisie obligatoire")
    if st.button("Traiter", key='btn_proj'):
        st.success("Projet traité")
    st.write("---")
    proj_lib = st.selectbox("Ou utilisez des documents de la bibliothèque", ["Présentation Projet Mahakam"], key='proj_lib')
    if st.button("Traiter", key='btn_proj_lib'):
        st.success("Bibliothèque projet traité")

with col2:
    st.header("Votre association")
    assoc_file = st.file_uploader("Ou faites glisser et déposez vos fichiers ici", type=['pdf', 'docx'], key='assoc')
    assoc_name = st.text_input("Nom associé aux fichiers", placeholder="Saisie obligatoire", key='assoc_name')
    if st.button("Traiter", key='btn_assoc'):
        st.success("Association traitée")
    st.write("---")
    assoc_lib = st.selectbox("Ou utilisez des documents de la bibliothèque", ["Présentation Planète Urgence"], key='assoc_lib')
    if st.button("Traiter", key='btn_assoc_lib'):
        st.success("Bibliothèque association traité")

st.markdown("---")

# --- Formulaire de réponse ---
st.header("Remplir un formulaire de réponse")
response_file = st.file_uploader("Ou faites glisser et déposez votre fichier ici", type=['pdf', 'docx'], key='response')
response_text = st.text_input("Ou saisissez une question manuellement", placeholder="Votre question")
with st.expander("Paramètres"):
    st.slider("Niveau de détail", 1, 5, 3)
if st.button("Traiter", key='btn_response'):
    st.success("Question traitée")

st.markdown("---")

# --- Affichage des réponses ---
st.header("Vos réponses")

# Exemple de Q&A
qa_list = [
    {"q": "Lorem ipsum dolor sit amet... ?", "a": "Sed ut perspiciatis unde omnis iste natus error sit voluptatem..."},
    {"q": "At vero eos et accusamus et justo odio dignissimos ducimus ?", "a": "Nam libero tempore, cum soluta nobis est eligendi optio cumque nihil impedit..."}
]
for qa in qa_list:
    st.subheader("Question")
    st.write(qa["q"])
    st.subheader("Réponse")
    st.write(qa["a"])
    st.markdown("---")

if st.button("Télécharger les réponses (Format DOCX)"):
    st.info("Génération du document en cours...")
