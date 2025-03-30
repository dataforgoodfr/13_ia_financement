
import streamlit as st
import os

def run():
    st.title("IA pour répondre aux appels à projets")
    
    image_path = "D4G.jpeg"
    if os.path.exists(image_path):
        st.image(image_path)
    else:
        st.warning("Image D4G.jpeg non trouvée dans le dossier 'notebooks'.")
    
    st.markdown("""
    ---
    ## 🧠 Projet – IA financement

    **L'objectif de ce projet est de développer une intelligence artificielle pour faciliter la réponse des associations aux appels à projets publics et privés.**

    ---
    """)

    st.header("📘 Description")
    st.markdown("""
    *IA - financement* est une initiative portée par **Groupe SOS** et **Planète Urgence**, visant à réduire le temps et les ressources nécessaires pour répondre aux appels à projets publics et privés – une source clé de financement pour les associations.

    Les associations consacrent une part significative de leurs ressources à cette tâche.  
    Selon une étude de **Humentum (2020)**, en moyenne **24% du temps des ONG** est dédié à la recherche et à la réponse aux appels à projets, mobilisant l'équivalent d'**un mi-temps** par organisation.

    Ce projet permettra aux associations de se concentrer sur les **aspects stratégiques et qualitatifs**, en automatisant les étapes les plus fastidieuses du processus.

    ---
    """)

    st.header("🛠️ Fonctionnalités clés")
    st.markdown("""
    - 📄 Analyse automatique des documents de présentation des projets
    - 🔍 Extraction des questions dans les appels à projets
    - 🧠 RAG (Retrieval-Augmented Generation) avec génération automatique de réponses
    - 📝 Génération d’un document Word prêt à être soumis
    - 🗣️ Multilingue : français et anglais
    - 🧩 **Open source** et co-construit avec les associations
    """)

    st.markdown("---")
    st.info("Cette solution est conçue **par et pour** les associations afin de maximiser l'impact de leurs actions, en facilitant l'accès aux financements.")
