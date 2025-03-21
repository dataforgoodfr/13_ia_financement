
# =========================
# charger le texte
#==========================

from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import os
import asyncio
from lightrag import LightRAG, QueryParam
# from lightrag.llm.openai import gpt_4o_mini_complete, gpt_4o_complete, openai_embed
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.llm.ollama import ollama_embed
from lightrag.utils import EmbeddingFunc
# from lightrag.llm.hf import hf_model_complete, hf_embed
# from transformers import AutoModel, AutoTokenizer
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.utils import setup_logger
import time
from time import time as timing
import numpy as np



os.environ['GROQ_API_KEY']="xxx"

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

size=len(full_text)
chunk_size=int(size/10)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_size*0.2)

docs = text_splitter.split_text(full_text)






# ================================
# traiter le texte:
# 1. chunk
# 2. embedding
# 3. KG graph via llm
# 4. stockage de la DB + graph
#=================================


setup_logger("lightrag", level="INFO")

async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], keyword_extraction=False, **kwargs
) -> str:
    return await openai_complete_if_cache(
        "qwen-2.5-32b",
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
        **kwargs
    )



async def initialize_rag():
    rag = LightRAG(
        working_dir="./data/lightrag_db_groq",
        llm_model_max_async=1,        
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=768,
            max_token_size=8192,
            func=lambda texts: ollama_embed(
                texts,
                embed_model="nomic-embed-text"
            )
        ),
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
    i=0
    for doc in docs:
        t=timing()
        rag.insert(doc)
        print(f"---->Insert doc {i}, size {len(doc)}, time {timing()-t} sec\n")
        i+=1
        time.sleep(90)

    # Basic CSV export (default format)
    rag.export_data("knowledge_graph_full_groq.csv")
    

if __name__ == "__main__":
    main()