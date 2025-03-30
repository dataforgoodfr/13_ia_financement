import streamlit as st

st.sidebar.title("Sommaire")
page = st.sidebar.radio("Aller à", ["Introduction", "Chargement des présentations de projets", "Chargement des appels à projets"])
with st.sidebar:
    st.image("SOS.png")
    st.image("D4G.png")
    st.write("### Projet DataForGood")

if page == "Introduction":
    import page1_intro
    page1_intro.run()

elif page == "Chargement des présentations de projets":
    import page2_projets
    page2_projets.run()

elif page == "Chargement des appels à projets":
    import page3_aap
    page3_aap.run()
