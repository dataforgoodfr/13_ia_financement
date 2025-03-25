import streamlit as st
from hybrid_retriever import process_new_pp, process_existing_pp, QA_pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import os
import pandas as pd
import json


def load_doc():
    # Load the PDF
    print("load pdf")
    pdf_file_path = './data/PROJECT DOCUMENT MAHAKAM 2023-2025_balise.pdf'
    loader = PyPDFLoader(pdf_file_path)
    pages = loader.load()

    # nettoyage
    bruits=["Planète Urgence | FOREST Programme"]
    for doc in pages:
        for bruit in bruits:
            if bruit in doc.page_content:
                doc.page_content=doc.page_content.replace(bruit, "")
    # del empty docs
    pages = [doc for doc in pages if len(doc.page_content)>0]

    full_text=""
    for p in pages:
        full_text+=p.page_content

    return full_text

def load_pp_traces():
    st.markdown("### PP chargés:", unsafe_allow_html=True)

    file_path="pp_hashes.json"
    exising_hashes={}
    if os.path.exists(file_path):                
        table=pd.read_json(file_path).T
        table=table.sort_values("Date de création", ascending=False)
        st.dataframe(table)

        return table
    else:
        return []


def main():

    st.title("IA financement 13")
    st.sidebar.title("Sommaire")
    pages=[
        "Guide d'utilisation", 
        "Charger un PP",
        "Remplir un AAP", 
        "Mettre à jour un PP",
    ]
    
    page=st.sidebar.radio("Aller vers", pages)

    
    if page == pages[0]:
        st.write("### Guide")
        st.write("Faire des millions :)")

    if page == pages[1]:

        
        


        # charger traces des PP existantes:
        df_existing_pp= load_pp_traces()



        st.write('### Charger un nouveau PP')    
        col1, col2, col3 = st.columns(3, vertical_alignment="bottom")
        with col1:
            btn_new_pp= st.button("Charger PP")
        with col2:
            pp_name=st.text_input(label="Nom du PP", placeholder="Saisie obligatoire")
        with col3:
            max_size=st.number_input(label='PP max size', step=10)

        input_file= st.file_uploader(label="Charger un PP")

        st.markdown('<hr>', unsafe_allow_html=True)


        st.write('### Utiliser un PP existant')
        col4, col5 = st.columns(2, vertical_alignment="bottom", )
        with col4:
            list_pp_names=[]
            if len(df_existing_pp)>0:
                list_pp_names=df_existing_pp["Nom du PP"].unique()
            
            existing_pp_name= st.selectbox(label="Choisir PP", options=list_pp_names)
        with col5:
            btn_existing_pp= st.button("Utiliser PP")

        if btn_new_pp:
            text=load_doc()
            # Créer un conteneur pour afficher les messages
            st.markdown("Status:", unsafe_allow_html=True)   

            messages=""
            print(f"pp_name: {pp_name}")
            for message in process_new_pp(text[: len(text)-int(max_size)], pp_name):
                if isinstance(message, str):
                    messages=message+"<br>"
                    st.markdown(messages, unsafe_allow_html=True)  # Mettre à jour le contenu du conteneur                

        elif btn_existing_pp:
            hash=df_existing_pp[df_existing_pp["Nom du PP"]==existing_pp_name].index.values[0]
            for message in process_existing_pp(hash, existing_pp_name):
                st.markdown(message, unsafe_allow_html=True)


    if page == pages[2]:        
        st.write("#### Charger un AAP")
        input_file= st.file_uploader(label="Charger un AAP")
        st.markdown("------------", unsafe_allow_html=True)
        st.write("#### Saisie manuelle")
        query=[st.text_input(label="Votre question", placeholder="")]
        launch_query=st.button(label="Chercher")
        if launch_query:
            for resp in QA_pipeline(query):
                if isinstance(resp, dict):
                    st.markdown(f"#### Réponse:\n {resp['answer']}", unsafe_allow_html=True)
                    st.markdown("-----", unsafe_allow_html=True)
                    for source in resp['sources']:
                        st.markdown(f"#### Sources:\n {source}", unsafe_allow_html=True)
                elif isinstance(resp, str):
                    st.markdown(resp, unsafe_allow_html=True)
if __name__ == "__main__":
    main()