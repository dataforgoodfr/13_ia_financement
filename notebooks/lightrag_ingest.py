
# =========================
# charger le texte
#==========================

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger
from time import time as timing

os.environ["OPENAI_API_KEY"] = "key"

# Load the PDF
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

len(full_text)




# ================================
# traiter le texte:
# 1. chunk
# 2. embedding
# 3. KG graph via llm
# 4. stockage de la DB + graph
#=================================


setup_logger("lightrag", level="INFO")

async def initialize_rag():
    rag = LightRAG(
        working_dir="./data/lightrag_db",
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
        vector_storage="FaissVectorDBStorage",
        vector_db_storage_cls_kwargs={
            "cosine_better_than_threshold": 0.3  # Your desired threshold
        }        
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag

def main():
    # Initialize RAG instance
    rag = asyncio.run(initialize_rag())
    # Insert text
    t=timing()
    rag.insert(full_text)
    print(f"---->Insert time: {timing()-t} sec")

    # Basic CSV export (default format)
    rag.export_data("knowledge_graph_full.csv")
    

if __name__ == "__main__":
    main()