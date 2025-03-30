import streamlit as st
import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate

# Récupération de la clé API
api_key = os.getenv("OPENAI_API_KEY")

# Fonction pour sauvegarder un fichier (temporairement)
def save_uploaded_file(uploaded_file):
    temp_path = os.path.join("temp", uploaded_file.name)
    os.makedirs("temp", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.read())
    return temp_path

# Fonction pour lire le contenu d'un document
def extract_content_text(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        documents = loader.load()
    elif ext == ".docx":
        loader = Docx2txtLoader(file_path)
        documents = loader.load()
    else:
        st.error("❌ Format non pris en charge : uniquement PDF ou DOCX.")
        return []
    return [doc.page_content for doc in documents]

# Définition des variables de session
vector_store = None
questions = []
answers = []

def run():
    global vector_store, questions, answers

    st.title("📁 Chargement des présentations de projet")
    st.write("Chargez ici vos documents `.pdf` ou `.docx` pour construire une base de connaissance exploitable par IA.")

    if not api_key:
        st.error("❌ Clé API OpenAI manquante. Veuillez définir la variable d'environnement `OPENAI_API_KEY`.")
        return

    uploaded_docs = st.file_uploader("Téléversez un ou plusieurs documents", type=["pdf", "docx"], accept_multiple_files=True)

    if uploaded_docs:
        docs = []

        for file in uploaded_docs:
            temp_path = save_uploaded_file(file)
            ext = os.path.splitext(temp_path)[-1].lower()

            if ext == ".pdf":
                loader = PyPDFLoader(temp_path)
            elif ext == ".docx":
                loader = Docx2txtLoader(temp_path)
            else:
                st.warning(f"Format non supporté : {file.name}")
                continue

            docs.extend(loader.load())

        # Découpage du contenu en chunks et Création des embeddings et vector store
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)
        chunks = splitter.split_documents(docs)
        embeddings = OpenAIEmbeddings(api_key=api_key)
        vector_store = FAISS.from_documents(chunks, embeddings)

        # Sauvegarde dans la session Streamlit
        st.session_state["vector_store"] = vector_store

        st.success(f"✅ {len(uploaded_docs)} document(s) chargé(s) et vectorisé(s).")

    # Test manuel 
    with st.expander("💬 Tester avec une question manuelle"):
        test_question = st.text_input("Posez une question sur les documents chargés")

        if st.button("Lancer la recherche"):
            if "vector_store" not in st.session_state:
                st.error("Aucun document chargé. Veuillez en importer avant de poser une question.")
            else:
                vector_store = st.session_state["vector_store"]
                retrieved_docs = vector_store.similarity_search(test_question)
                context = "\n\n".join(doc.page_content for doc in retrieved_docs)

                prompt = PromptTemplate.from_template("""
                Tu es chargé de projet pour une association. Tu dois répondre à des appels à projets.
                Utilise les documents fournis comme contexte pour répondre.
                Si tu ne sais pas, dis-le

                Contexte : {context}
                Question : {question}
                Réponse :
                """)

                llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
                response = llm.invoke(prompt.format(question=test_question, context=context))

                st.markdown("### ✏️ Réponse générée")
                st.write(response.content)
