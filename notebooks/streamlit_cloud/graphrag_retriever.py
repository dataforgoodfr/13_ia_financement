"""@article{chen2025pathrag,
  title={PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths},
  author={Chen, Boyu and Guo, Zirui and Yang, Zidan and Chen, Yuluo and Chen, Junze and Liu, Zhenghao and Shi, Chuan and Yang, Cheng},
  journal={arXiv preprint arXiv:2502.14902},
  year={2025}
}"""

import hashlib
from time import time as timing
import os
import os
from PathRAG import PathRAG, QueryParam
from PathRAG.llm import gpt_4o_mini_complete
import json
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import dotenv



WORKING_DIR = "./storage/graph_stores/"


dotenv.load_dotenv(".env")

base_url="https://api.openai.com/v1"
os.environ["OPENAI_API_BASE"]=base_url

graphrag_pipeline_args={}

#============vérif si doc bien traité:    
def check_doc_processed(text):
    # generate hash for curr text
    yield "Génération du hash"
    hash_text=hashlib.sha256(text.encode('utf-8')).hexdigest()


    # load existing hashes
    file_path="graphrag_hashes.json"
    
    def load_hashes(file_path=file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    
    print("load hashes")
    yield "Chargement de l'historique de hashage Graph RAG"
    exising_hashes=load_hashes()

    # check if current text has been processed with its hash 
    # 1. hash exists, exit
    print("check hash")
    if hash_text in exising_hashes:
        msg="Ce document a déjà été traité"
        print(msg)
        print(hash_text)
        yield msg

        
    # 2. hash do not exist, return confirmation to streamlit and continue processins
    else:
        
        msg="Nouveau document identifié"
        yield msg
        print(msg)
        print(hash_text)


        yield (False, hash_text)

#================

def create_graphdb(pages: list, doc_name: str, doc_title: str, doc_category: str,):
    
    def save_hash_info(hash_text, doc_name, doc_title, doc_category, text):
        import datetime
        file_path="graphrag_hashes.json"
        exising_hashes={}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                exising_hashes= json.load(f)                    
                
        exising_hashes[hash_text] = {
            "Nom du doc": doc_name, 
            "Titre auto": doc_title, 
            "Taille du texte (en car)": len(text),
            "Date de création": str(datetime.datetime.now()),
            "doc_category": doc_category,
            "rag_type": "graph"
        }

        with open(file_path, 'w') as f:
            json.dump(exising_hashes, f)


    # extraire le texte des pages
    full_text = "\n\n".join([doc.page_content for doc in pages])
    
    text_to_insert=full_text#[: int(len(full_text)*0.02)]
    #===================

    generator = check_doc_processed(text_to_insert)

    # Itérer sur le générateur pour exécuter le code et récupérer les messages
    for message in generator:
        # feedback de vérification
        if isinstance(message, str):
            yield (message)
        # feedback nouveau doc
        elif isinstance(message, tuple):
            doc_processed=message[0]
            hash_text=message[1]
            
            # init store pipelines
            graphrag_pipeline_args[f"rag_{doc_category}"]={}

            
            # init pathrag
            rag = PathRAG(
                working_dir=f'{WORKING_DIR}{hash_text}',
                llm_model_func=gpt_4o_mini_complete,  
            )


            yield "Création de la chaîne Graph RAG en cours"
            

            
            # base line texte de 100 000 caractères
            estimed_time=(len(text_to_insert)*180)/100000
            yield f"Temps estimé: {int(estimed_time+60)} secondes"

            estimed_tokens=(len(text_to_insert)*330000)/100000
            yield f"Consommation de tokens estimée: {int(estimed_tokens)} tokens (90% input / 10% output)"

            t=timing()
            #========création du graph
            rag.insert(text_to_insert)
            tf=timing()-t

            yield f"Création de la chaîne Graph RAG en {int(tf)} secondes"

            save_hash_info(hash_text, doc_name, doc_title, doc_category, text_to_insert)

            graphrag_pipeline_args[f"rag_{doc_category}"]=rag
            yield {"pipeline_args": graphrag_pipeline_args[f"rag_{doc_category}"]}

def load_existing_graphdb(hash, doc_category):
    # check existence du dossier corresondant au hash    
    
    if os.path.exists(f"{WORKING_DIR}{hash}")==False:
        yield "Aucune base graph trouvée"
        return


    yield f"""
        ----------------
        #### Graph RAG retriever
        Chargement de la base Graph RAG
    """
    rag = PathRAG(
        working_dir=f'{WORKING_DIR}{hash}',
        llm_model_func=gpt_4o_mini_complete,  
    )
    yield "**Graph RAG chargé**"
    graphrag_pipeline_args[f"rag_{doc_category}"]=rag
    yield {"pipeline_args": graphrag_pipeline_args[f"rag_{doc_category}"]}
