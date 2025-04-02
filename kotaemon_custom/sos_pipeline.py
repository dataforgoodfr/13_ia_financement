import os
import glob
import PyPDF2
import docx
from kotaemon.base import Document
from kotaemon.storages import LanceDBDocumentStore
from kotaemon.storages.vectorstores.chroma import ChromaVectorStore
from kotaemon.embeddings import OpenAIEmbeddings

# Chemins pour le docstore et le vector store
DOCSTORE_PATH = "./ktem_app_data/user_data/docstore"
CHROMA_PATH   = "./ktem_app_data/user_data/chroma"

# Récupère DATA_ROOT (monté dans /app/data)
DATA_ROOT = os.environ.get("DATA_ROOT", "/app/data")

# Mode d'embeddings : "openai", "local", ou "none"
EMBEDDING_MODE = os.environ.get("EMBEDDING_MODE", "local").lower()
print(f"[sos_pipeline] EMBEDDING_MODE={EMBEDDING_MODE}")

# Wrapper pour HuggingFaceEmbeddings via langchain
class LangchainHuggingFaceEmbeddings:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        from langchain_community.embeddings import HuggingFaceEmbeddings
        self.hf = HuggingFaceEmbeddings(model_name=model_name)
    def __call__(self, texts):
        embeddings = self.hf.embed_documents(texts)
        return [emb.tolist() if hasattr(emb, "tolist") else emb for emb in embeddings]

def read_pdf_text(pdf_path: str) -> str:
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def read_docx_text(docx_path: str) -> str:
    doc_file = docx.Document(docx_path)
    paragraphs = [para.text for para in doc_file.paragraphs]
    return "\n".join(paragraphs)

def main_ingest():
    docstore = LanceDBDocumentStore(path=DOCSTORE_PATH)
    vectorstore = ChromaVectorStore(
        persist_directory=CHROMA_PATH,
        collection_name="default"
    )
    
    if EMBEDDING_MODE == "openai":
        print("[sos_pipeline] Using OpenAIEmbeddings for ingestion.")
        embedding_model = OpenAIEmbeddings(model="text-embedding-ada-002")
    elif EMBEDDING_MODE == "local":
        print("[sos_pipeline] Using local embeddings (LangchainHuggingFaceEmbeddings) for ingestion.")
        embedding_model = LangchainHuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    else:
        print("[sos_pipeline] No embeddings will be computed (EMBEDDING_MODE != 'openai' and != 'local').")
        embedding_model = None

    pdf_files = glob.glob(os.path.join(DATA_ROOT, "**", "*.pdf"), recursive=True)
    docx_files = glob.glob(os.path.join(DATA_ROOT, "**", "*.docx"), recursive=True)
    all_files = pdf_files + docx_files

    for file_path in all_files:
        print(f"Ingesting: {file_path}")
        if file_path.lower().endswith(".pdf"):
            text_content = read_pdf_text(file_path)
        elif file_path.lower().endswith(".docx"):
            text_content = read_docx_text(file_path)
        else:
            print(f"[sos_pipeline] Format non supporté: {file_path}")
            continue

        doc = Document(
            page_content=text_content,
            metadata={"source": os.path.basename(file_path)}
        )
        doc_ids = docstore.add([doc])
        doc_id = doc_ids[0] if doc_ids else None

        if embedding_model is not None:
            embedding_list = embedding_model([text_content])
            embedding = embedding_list[0]
            vectorstore.add(
                [embedding],
                metadatas=[{"doc_id": doc_id, "source": os.path.basename(file_path), "text": text_content}]
            )

    print("[sos_pipeline] Ingestion complete!")

if __name__ == "__main__":
    main_ingest()
