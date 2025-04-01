import streamlit as st
from rag_pipelines import process_new_doc, process_existing_pp, QA_pipeline
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import StringIO
import os
import pandas as pd
import json
import types


def load_doc():
    # Load the PDF
    print("load pdf")
    @st.cache_data
    def load():
        pdf_file_path = './data/PROJECT DOCUMENT MAHAKAM 2023-2025_balise.pdf'
        loader = PyPDFLoader(pdf_file_path)
        pages = loader.load()
        
        return pages
    st.file_uploader
    pages = load()

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
        table=pd.read_json(file_path,).T
        table=table.sort_values("Date de création", ascending=False)
        table['Date de création'] = pd.to_datetime(table['Date de création']).dt.floor('s')
        st.dataframe(table.reset_index(drop=True))

        return table
    else:
        return []


def main():

    st.title("IA financement 13")

    # menu
    st.sidebar.title("Sommaire")
    pages=[
        "Guide d'utilisation", 
        "Charger un PP",
        "Remplir un AAP", 
        "Mettre à jour un PP",
    ]
    
    page=st.sidebar.radio("Aller vers", pages)

    
    # page d'accueil
    if page == pages[0]:
        st.write("### Guide")
        st.write("Faire des millions :)")









    # page chargement de la PP
    if page == pages[1]:
      
        
        # charger traces des PP existantes:
        df_existing_pp= load_pp_traces()




        #======== UI Charger un nouveau PP
        # UI provisoire
        st.write('### Charger un nouveau PP')    
        st.markdown('----------------UI de testing-----------------', unsafe_allow_html=True)
        col1_prov, col2_prov, col3_prov = st.columns(3, vertical_alignment="bottom")
        with col1_prov:
            btn_new_pp_prov= st.button("Charger PP")
        with col2_prov:
            pp_name_prov=st.text_input(label="Nom prov du PP", placeholder="Saisie obligatoire")
        with col3_prov:
            max_size=st.number_input(label='PP max size', step=10)

        st.markdown('<hr>', unsafe_allow_html=True)

        # UI définitive
        st.markdown('------------------UI définitive--------------', unsafe_allow_html=True)
        uploaded_pp= st.file_uploader(label="Charger un PP", type=["pdf","docx"], accept_multiple_files=True)
        col1_new_pp, col2_new_pp = st.columns(2, vertical_alignment="bottom")
        with col1_new_pp:
            pp_name=st.text_input(label="Nom du PP", placeholder="Saisie obligatoire")
        with col2_new_pp:
            btn_new_pp= st.button("Traiter", key='btn_pp')


        st.markdown('<hr>', unsafe_allow_html=True)

        
        uploaded_asso= st.file_uploader(label="Charger les informations de l'association", type=["pdf","docx"], accept_multiple_files=True)
        col1_asso_info, col2_asso_info = st.columns(2, vertical_alignment="bottom")
        with col1_asso_info:
            asso_name=st.text_input(label="Nom de l'association", placeholder="Saisie obligatoire")
        with col2_asso_info:
            btn_asso= st.button("Traiter", key='btn_asso')

        
        st.markdown('<hr>', unsafe_allow_html=True)

        #===============================================





        #========UI Utiliser un PP existant
        st.write('### Utiliser un PP existant')
        col4, col5 = st.columns(2, vertical_alignment="bottom", )
        with col4:
            list_pp_names=[]
            if len(df_existing_pp)>0:
                list_pp_names=df_existing_pp["Nom du PP"].unique()
            
            existing_pp_name= st.selectbox(label="Choisir PP", options=list_pp_names)
        with col5:
            btn_existing_pp= st.button("Utiliser PP")
        #================================================




        #========Interactions nouveau PP
        # prov
        if btn_new_pp_prov and pp_name_prov!="":
            text=load_doc()
            # Créer un conteneur pour afficher les messages
            st.markdown("Status:", unsafe_allow_html=True)   

            messages=""
            print(f"pp_name: {pp_name_prov}")
            for message in process_new_doc(text[: len(text)-int(max_size)], pp_name_prov):
                #if isinstance(message, str):
                messages=message+"<br>"
                st.markdown(messages, unsafe_allow_html=True)  # Mettre à jour le contenu du conteneur                


        # définitif
        if uploaded_pp is not None and pp_name!="" and btn_new_pp:
            messages=process_new_doc(uploaded_pp, pp_name, "pp")
            
            for message in messages:
                st.markdown(message, unsafe_allow_html=True)

        #===============================================
        

        #========Interactions nouveau doc association
        if uploaded_asso is not None and asso_name!="" and btn_asso:
            messages=process_new_doc(uploaded_asso, asso_name, "asso")
            
            for message in messages:
                st.markdown(message, unsafe_allow_html=True)

        #===============================================
        #         
        
        #========Interactions PP existant
        elif btn_existing_pp:
            hash=df_existing_pp[df_existing_pp["Nom du PP"]==existing_pp_name].index.values[0]
            for message in process_existing_pp(hash, existing_pp_name):
                st.markdown(message, unsafe_allow_html=True)
        #===============================================







    # chargement AAP
    if page == pages[2]:        
        st.write("#### Charger un AAP")
        input_file= st.file_uploader(label="Charger un AAP")
        st.markdown("------------", unsafe_allow_html=True)
        st.write("#### Saisie manuelle")
        
        
        query=[st.text_input(label="Votre question", placeholder="")]        

        launch_query=st.button(label="Chercher")
        if launch_query:
            for resp in QA_pipeline(query):
                full_response=""
                if isinstance(resp, types.GeneratorType):
                    #for r in resp:
                    st.markdown(f"#### Réponse:\n", unsafe_allow_html=True)
                    # st.write_stream(stream=resp)
                    
                    
                    # 1. Créer un buffer pour accumuler la réponse
                    response_buffer = StringIO()
                    response_container = st.empty()  # Conteneur vide pour mise à jour dynamique

                    for chunk in resp:
                    # Ajouter le token au buffer
                        response_buffer.write(chunk)
                        # Mettre à jour le conteneur avec le contenu accumulé
                        response_container.markdown(response_buffer.getvalue())

                    # 3. Récupérer la réponse complète
                    full_response = response_buffer.getvalue()
                    response_buffer.close()

                    
                    st.markdown("-----", unsafe_allow_html=True)

                    
                    print(full_response)                    

                elif isinstance(resp, dict) and 'sources' in resp:
                    st.markdown(f"#### Sources:\n", unsafe_allow_html=True)
                    
                    for source in resp["sources"]:
                        st.markdown(f"**Source**:<br>{source[0]}", unsafe_allow_html=True)
                        st.markdown(f"**Score**: {source[1]}", unsafe_allow_html=True)
                elif isinstance(resp, dict) and 'uid' in resp:
                    resp["response"]=full_response
                    st.markdown(f"**Metadata**: {resp}", unsafe_allow_html=True)
                elif isinstance(resp, str):                    
                    st.markdown(f"{resp}", unsafe_allow_html=True)

if __name__ == "__main__":
    main()