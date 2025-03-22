import streamlit as st
from hybrid_retriever import process_pp
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from io import StringIO


st.cache_data
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

def main():
    
    st.title("Projet compagnon immo")
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

    if page == pages[1]:

        
        st.write('### Charger un PP')

        btn_mahakam= st.button("Mahakam project")
        max_size=st.number_input(label='Max size')

        if btn_mahakam:
            text=load_doc()
            # Créer un conteneur pour afficher les messages
            message_container = st.empty()            

            messages=""
            for message in process_pp(text[: len(text)-int(max_size)]):
                messages+=message+"<br>"
                message_container.markdown(messages, unsafe_allow_html=True)  # Mettre à jour le contenu du conteneur                
            

    if page == pages[2]:
        st.write("### Remplir un AAP")

if __name__ == "__main__":
    main()