import os
import glob
import PyPDF2
import docx
import gradio as gr
import shutil
from kotaemon.base import Document
from kotaemon.storages import LanceDBDocumentStore
from kotaemon.storages.vectorstores.chroma import ChromaVectorStore
from kotaemon.embeddings import OpenAIEmbeddings
from llama_index.core.vector_stores.types import VectorStoreQuery

from sos_flowsettings import KH_CHAT_LLM, KH_VECTORSTORE

# Chemins pour le docstore et le vector store
DOCSTORE_PATH = "./ktem_app_data/user_data/docstore"
CHROMA_PATH   = "./ktem_app_data/user_data/chroma"

# Récupère DATA_ROOT (monté dans /app/data)
DATA_ROOT = os.environ.get("DATA_ROOT", "/app/data")
print(f"[sos_pipeline] DATA_ROOT={DATA_ROOT}")

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

def reset_data():
    try:
        shutil.rmtree(DOCSTORE_PATH)
        shutil.rmtree(CHROMA_PATH)
        return "Docstore et vectorstore supprimés."
    except Exception as e:
        return f"Erreur : {str(e)}"

def assistant_aap_ui():
    with gr.Blocks() as demo:
        gr.Markdown("## Assistant AAP - Génération de réponses à partir des documents")

        with gr.Row():
            aap_file = gr.File(label="AAP à remplir (.docx)", file_types=['.docx'])
            pp_file = gr.File(label="PP associé (.pdf/.docx)", file_types=['.pdf', '.docx'])

        question_output = gr.Textbox(label="Questions extraites", lines=10)
        reponse_output = gr.Textbox(label="Réponses générées", lines=10)
        bouton = gr.Button("Générer les réponses")
        bouton.click(fn=lambda: ("à implémenter", "à implémenter"), outputs=[question_output, reponse_output])

        with gr.Row():
            reset_btn = gr.Button("Réinitialiser la base")
            reset_output = gr.Textbox(label="Logs de reset", lines=2)
            reset_btn.click(fn=reset_data, outputs=reset_output)

    return demo

def answer_question_with_context(question: str) -> str:
    print(f"[sos_pipeline] Question reçue : {question}")

    query_obj = VectorStoreQuery(
        query_str=question,
        similarity_top_k=3
    )

    results = KH_VECTORSTORE._client.query(query_obj)

    if not results or not results.nodes:
        return "Aucun contexte trouvé pour répondre à la question."

    context = "\n\n".join([node.text for node in results.nodes])
    prompt = f"""Réponds à la question suivante en te basant uniquement sur le contexte fourni.

### Contexte :
{context}

### Question :
{question}

### Réponse :"""

    response = KH_CHAT_LLM.invoke(prompt)
    return response.content

if __name__ == "__main__":
    main_ingest()
