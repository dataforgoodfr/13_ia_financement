import streamlit as st

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


# Bannière principale affichant le titre et un sous-titre
st.markdown(
    """
    <div class="main-title">
        <h1>IA pour répondre aux appels à projets</h1>
        <p>Optimisez vos réponses grâce à l'intelligence artificielle</p>
    </div>
    """,
    unsafe_allow_html=True
)



# Sidebar avec sommaire et images centrées
st.sidebar.title("Sommaire")
page = st.sidebar.radio("Aller à", ["Introduction", "Chargement des présentations de projets", "Chargement des appels à projets"])
with st.sidebar:
    st.image("SOS.png")
    st.image("D4G.png")
    st.write("### Projet DataForGood")

# Navigation vers les pages
if page == "Introduction":
    import page1_intro
    page1_intro.run()
elif page == "Chargement des présentations de projets":
    import page2_projets
    page2_projets.run()
elif page == "Chargement des appels à projets":
    import page3_aap
    page3_aap.run()
