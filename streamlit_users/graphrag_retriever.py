"""@article{chen2025pathrag,
  title={PathRAG: Pruning Graph-based Retrieval Augmented Generation with Relational Paths},
  author={Chen, Boyu and Guo, Zirui and Yang, Zidan and Chen, Yuluo and Chen, Junze and Liu, Zhenghao and Shi, Chuan and Yang, Cheng},
  journal={arXiv preprint arXiv:2502.14902},
  year={2025}
}"""

import hashlib
from time import time as timing
import os
from pathlib import Path
from PathRAG import PathRAG, QueryParam
from PathRAG.llm import gpt_4o_mini_complete
import json
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import networkx as nx
from pyvis.network import Network

import dotenv

dotenv.load_dotenv(".env")

# Get the directory of the current script (e.g., app.py)
SCRIPT_DIR = Path(__file__).parent.resolve()


WORKING_DIR = SCRIPT_DIR/"storage/graph_stores/"




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
            graphrag_pipeline_args[f"hash"]=hash_text
            
            # init pathrag
            rag = PathRAG(
                working_dir=f'{WORKING_DIR}/{hash_text}',
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

            yield f"Création du visuel du graphe de connaissances"
            build_knowledge_graph_vis(hash_text)

            graphrag_pipeline_args[f"rag_{doc_category}"]=rag
            
            yield {"pipeline_args": graphrag_pipeline_args[f"rag_{doc_category}"]}

def load_existing_graphdb(hash, doc_category):
    # check existence du dossier corresondant au hash        
    if os.path.exists(f"{WORKING_DIR}/{hash}")==False:
        yield "Aucune base graph trouvée"
        return

    graphrag_pipeline_args[f"hash"]=hash

    yield f"""
        ----------------
        #### Graph RAG retriever
        Chargement de la base Graph RAG
    """
    rag = PathRAG(
        working_dir=f'{WORKING_DIR}/{hash}',
        llm_model_func=gpt_4o_mini_complete,  
    )
    yield "**Graph RAG chargé**"
    graphrag_pipeline_args[f"rag_{doc_category}"]=rag
    yield {"pipeline_args": graphrag_pipeline_args[f"rag_{doc_category}"]}


def build_knowledge_graph_vis(hash):
    
    # Load the GraphML file
    graphStore_path=WORKING_DIR/ f'{hash}/graph_chunk_entity_relation.graphml'
    G = nx.read_graphml(graphStore_path)
    # Create a Pyvis network
    net = Network(notebook=True, height='1080px', width='100%', bgcolor='white', font_color='black', cdn_resources='in_line')

    # Convert NetworkX graph to Pyvis network
    net.from_nx(G)


    tableau_colors = [
        "#4E79A7",  # Blue
        "#F28E2B",  # Orange
        "#E15759",  # Red
        "#76B7B2",  # Teal
        "#59A14F",  # Green
        "#EDC949",  # Yellow
        "#AF7AA1",  # Purple
        "#FF9DA7",  # Pink
        "#9C755F",  # Brown
        #"#BAB0AC",  # Gray
        "#8CD17D",  # Light Green
        "#F1CE63",  # Light Yellow
        "#B0AFC3",  # Lavender
        "#FFBE7D",  # Peach
        "#D3D3D3"   # Light Gray
    ]

    # Define color mapping for node groups
    color_mapping = {}
    entity_types_set=set(n["entity_type"] for n in net.nodes)
    for entity in entity_types_set:
        if entity=="UNKNOWN":
            color_mapping[entity]= "#BAB0AC"#gray
        elif entity!="UNKNOWN" and len(tableau_colors)>0:
            color_mapping[entity]= tableau_colors.pop()


    # Node customization with proper checks for attributes
    for node in net.nodes:#[:50]:

        # Example: Set node size based on degree
        node['size'] = G.degree[node['id']] * 2

        # Set node color based on group (if available)
        node['color'] = color_mapping[node['entity_type']]
        
        # Add hover information (safely accessing attributes)
        descr=node["description"].split("<SEP>")[0]
        descr=descr+" ..." if len(descr)>100 else descr
        node_info = f"Node: {node.get('label')}\nNode type: {node['entity_type']} \nDescr: {descr}"
        if 'group' in node:
            node_info += f"<br>Group: {node['group']}"
        node['title'] = node_info

    # Edge customization
    for edge in net.edges:
        # Disable arrows
        edge['arrows'] = 'to' if False else None
        
        # Reduce edge width
        edge['width'] = 1

    # Physics settings for better layout
    net.physics = True
    net.options = {
        "physics": {
            "enabled": True,
            "stabilization": {"iterations": 1000},
            "barnesHut": {"gravitationalConstant": -8000, "springLength": 200}
        }
    }

    # Save and display the network    
    graphVis_path=WORKING_DIR/ f'{hash}/knowledge_graph.html'
    net.save_graph(graphVis_path)    


def load_knowledgeGraph_vis():
    if "hash" not in graphrag_pipeline_args:
        yield "Veuillez charger un PP"
        return
    
    hash= graphrag_pipeline_args[f"hash"]


    # load existing hashes
    file_path=SCRIPT_DIR/"graphrag_hashes.json"
    
    def load_hashes(file_path=file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    
    print("load hashes")
    yield "Chargement de l'historique de hashage Graph RAG"
    exising_hashes=load_hashes()
    doc_name=exising_hashes[hash]["Nom du doc"]
    graphVis_path=WORKING_DIR/ f'{hash}/knowledge_graph.html'

    yield (graphVis_path, doc_name)
