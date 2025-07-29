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
import json
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document
import networkx as nx
from pyvis.network import Network
from PathRAG.llm import gpt_4o_mini_complete, openrouter_complete, ollama_embed_if_cache
from openai import OpenAI
from functools import partial
import pandas as pd
import time


# Get the directory of the current script (e.g., app.py)
SCRIPT_DIR = Path(__file__).parent.resolve()
WORKING_DIR = SCRIPT_DIR/"storage/graph_stores/"
graphrag_pipeline_args={}



# Fonction LLM personnalisée vers OpenRouter
# OPENROUTER_MODEL="nvidia/llama-3.3-nemotron-super-49b-v1:free"
OPENROUTER_MODEL_graph_creation="google/gemma-3-27b-it:free"
OPENROUTER_MODEL_graph_read="google/gemma-3-27b-it:free"

# Choix du provider
USE_OPENROUTER = True  # Basculer entre OpenAI et OpenRouter

# Configuration OpenRouter
if USE_OPENROUTER:
    api_key = "clé"
    os.environ["OPENROUTER_API_KEY"] = api_key

    # Création d'une fonction partielle avec le modèle fixé
    llm_func_creation = partial(
        openrouter_complete,
        model=OPENROUTER_MODEL_graph_creation
    )

    llm_func_read = partial(
        openrouter_complete,
        model=OPENROUTER_MODEL_graph_read
    )    
else:
    llm_func = gpt_4o_mini_complete    

#============vérif si doc bien traité:    
def check_doc_processed(text):
    # generate hash fqor curr text
    yield "Génération du hash"
    hash_text=hashlib.sha256(text.encode('utf-8')).hexdigest()


    # load existing hashes
    file_path="graphrag_hashes.json"
    file_path=SCRIPT_DIR/file_path
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

def create_graphdb(text: str, doc_name: str, doc_title: str=None, doc_category: str=None):
    
    def save_hash_info(text, hash_text, doc_name, doc_title="", doc_category=""):
        import datetime
        
        def get_text_metadata(text, metadata):
            prompt = f"""
            I need you to take a close look at a text and propose a {metadata}.
            Given the following extract: {text}
            Propose a short {metadata} for this text.
            Reply only with the proposed {metadata}, without any comment.
            """


            # Initialize the OpenAI client
            llm = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )

                # Invoke the model with the formatted prompt
            resp= llm.chat.completions.create(
                model="mistralai/mistral-small-3.1-24b-instruct:free",
                messages=[        
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
            )

            
            return resp.choices[0].message.content
        

        file_path="graphrag_hashes.json"
        file_path=SCRIPT_DIR/file_path
        exising_hashes={}
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                exising_hashes= json.load(f)                    

        if doc_name=="":
            doc_name=get_text_metadata(text[:15000], "name")        
        if doc_title=="":
            doc_title=get_text_metadata(text[:15000], "title")

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


    
    text_to_insert=text#[: int(len(full_text)*0.02)]
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
            
   
            rag = PathRAG(
                working_dir=f'{WORKING_DIR}/{hash_text}',
                llm_model_func=llm_func_creation,  # Retirez le lambda redondant
                embedding_func=ollama_embed_if_cache,
                llm_model_max_async=8
            )         

            yield "Création de la chaîne Graph RAG en cours"
            

            
            # base line texte de 100 000 caractères
            estimed_time=(len(text_to_insert)*180)/100000
            yield f"Temps estimé: {int(estimed_time+60)} secondes"

            estimed_tokens=(len(text_to_insert)*330000)/100000
            yield f"Consommation de tokens estimée: {int(estimed_tokens)} tokens (90% input / 10% output)"

            t=timing()
            #========création du graph
            # asyncio.run(rag.ainsert(text_to_insert))
            rag.insert(text_to_insert)
            tf=timing()-t

            yield f"Création de la chaîne Graph RAG en {int(tf)} secondes"
            
            save_hash_info(text, hash_text, doc_name, doc_title, doc_category)

            yield f"Création du visuel du graphe de connaissances"
            build_knowledge_graph_vis(hash_text, WORKING_DIR)

            # graphrag_pipeline_args[f"rag_{doc_category}"]=rag
            load_existing_graphdb(hash_text, doc_category)
            
            yield {
                "pipeline_args": {
                    "rag": rag,
                    "llm_graph_creation": OPENROUTER_MODEL_graph_creation, 
                    "llm_graph_QA": OPENROUTER_MODEL_graph_read,
                }
            }

def load_existing_graphdb(doc_name):    
    if doc_name=="":
        yield "Fournir le nom du graphe à charger"
        return
    
    file_path="graphrag_hashes.json"
    file_path=SCRIPT_DIR/file_path
    exising_hashes={}
    if os.path.exists(file_path):        
        exising_hashes= pd.read_json(file_path)
        _exising_hashes=exising_hashes.to_dict()
        
        hash_text=None
        for el in _exising_hashes.items():
            if el[1]["Nom du doc"].lower()==doc_name.lower():
                hash_text=el[0]
        
        if hash_text==None:
            yield "⛔ Graphe inexistant"
            return
    else:
        yield "⛔ Aucun graphe disponible"
        return
    

    # build_knowledge_graph_vis(hash, WORKING_DIR)
    # check existence du dossier corresondant au hash        
    if os.path.exists(f"{WORKING_DIR}/{hash_text}")==False:
        yield "⛔ Aucune base graph trouvée"
        return

    graphrag_pipeline_args[f"hash"]=hash_text

    yield f"""
        ----------------
        #### Graph RAG retriever
        Chargement de la base Graph RAG
    """

    # Configuration du RAG avec Ollama comme embedding
    rag = PathRAG(
        working_dir=f'{WORKING_DIR}/{hash_text}',
        llm_model_func=llm_func_read,  # Retirez le lambda redondant
        embedding_func=ollama_embed_if_cache,
        llm_model_max_async=6
    ) 

    yield "**✅ Graph RAG chargé**"
    graphrag_pipeline_args[f"rag_{doc_name}"]=rag
    yield {
        "pipeline_args": {
            "rag": rag,
            "llm_graph_creation": OPENROUTER_MODEL_graph_creation, 
            "llm_graph_QA": OPENROUTER_MODEL_graph_read,
        }
    }


def build_knowledge_graph_vis(hash_text, WORKING_DIR):
    import numpy as np

    def graph_summary_simple(G, net):
        nodes=list(G.nodes(data=True))
        entities=set([node[1]["entity_type"].replace('"', "") for node in nodes if node[1]["entity_type"].find('UNKNOWN')==-1])

        edges=list(G.edges(data=True))

        nodes_sizes=[node["size"] for node in net.nodes]
        edges_widths=[edge[2]["width"] for edge in edges]

        summary = {
            'LLM utilisé': OPENROUTER_MODEL_graph_creation,
            'Taille du graphe': {
                'Nombre de noeuds': G.number_of_nodes(),
                'Nombre de liens': G.number_of_edges(),
                # 'Densité (0-1)': np.round(nx.density(G),3),
            },
            'Diversité': {
                'Type de noeuds': len(entities)-1,
                'Liste des noeuds': list(entities),
                "Taille des noeuds": {"min": np.min(nodes_sizes), "median": np.median(nodes_sizes), "max": np.max(nodes_sizes)},                
                'Force des liens': {"min": np.min(edges_widths), "median": np.median(edges_widths), "max": np.max(edges_widths)},
                # "Coefficient de clustering": np.round(nx.average_clustering(G), 3),
                # 'Connexions moyennes par concept': f"{sum(dict(G.degree()).values()) / G.number_of_nodes():.1f}"
            },
            "nodes_sizes": nodes_sizes,
            "edges_widths": edges_widths,

        }
        return summary


    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)
        
    # Load the GraphML file
    graphStore_path=WORKING_DIR/ f'{hash_text}/graph_chunk_entity_relation.graphml'
    graphStore_path="/".join(graphStore_path.parts).replace("//", "/")

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
        "#BAB0AC",  # Gray
        "#8CD17D",  # Light Green
        "#F1CE63",  # Light Yellow
        "#B0AFC3",  # Lavender
        "#FFBE7D",  # Peach
        "#D3D3D3",  # Light Gray

        # Nouvelles couleurs ajoutées
        "#003366",  # Dark Blue
        "#30D5C8",  # Turquoise
        "#FF00FF",  # Magenta
        "#4B0082",  # Indigo
        "#FF6F61",  # Coral
        "#FFD700",  # Gold
        "#800000",  # Maroon
        "#000080",  # Navy
        "#808000",  # Olive
        "#FA8072",  # Salmon
        "#DA70D6",  # Orchid
        "#DC143C",  # Crimson
        "#F0E68C",  # Khaki
        "#6A5ACD",  # SlateBlue
        "#00BFFF"   # DeepSkyBlue
    ]

    # Define color madocumenting for node groups
    color_madocumenting = {}
    entity_types_set=set(n["entity_type"] for n in net.nodes)
    for entity in entity_types_set:
        if entity=="UNKNOWN":
            color_madocumenting[entity]= "#BAB0AC"#gray
        elif entity!="UNKNOWN" and len(tableau_colors)>0:
            color_madocumenting[entity]= tableau_colors.pop()
        else:
            color_madocumenting[entity]="#000000"


    # Node customization with proper checks for attributes
    for node in net.nodes:#[:50]:

        # Example: Set node size based on degree
        node['size'] = G.degree[node['id']] * 2

        # Set node color based on group (if available)
        try:
            node['color'] = color_madocumenting[node['entity_type']]
        except Exception as e:
            print(e)
            node['color']="#000000"
        
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
        # edge['arrows'] = 'to' if False else None
        
        # Reduce edge width
        width=edge['width']
        edge['width'] = 1

        # give a title
        descr_edge=edge["description"].replace("<SEP>", "\n")
        keywords_edge=edge["keywords"].replace("<SEP>", "\n")
        edge["title"]=f"""**Relation informations:**
            - Description: {descr_edge.replace('"',"")}
            - Keywords: {keywords_edge.replace('"',"")}
            - From: {edge["from"].replace('"',"")}
            - To: {edge["to"].replace('"',"")}
            - Force: {width}
        """

    # Physics settings for better layout
    net.physics = True
    net.options = {
        "physics": {
            "enabled": True,
            "stabilization": {"iterations": 100},
            "barnesHut": {"gravitationalConstant": -8000, "springLength": 200}
        }
    }

    # Save and display the network    
    graphVis_path=WORKING_DIR/ f'{hash_text}/knowledge_graph.html'
    graphVis_path="/".join(graphVis_path.parts).replace("//", "/")
    
    net.save_graph(graphVis_path)


    # save graph params
    file_path=SCRIPT_DIR/"graphrag_hashes.json"
    def load_hashes(file_path=file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
        
    exising_hashes=load_hashes()

    exising_hashes[hash_text]["graph_attrs"]=graph_summary_simple(G, net)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(exising_hashes, f, cls=NumpyEncoder, indent=2)
    except Exception as e:
        print(e)

def load_knowledgeGraph_vis():
    if "hash" not in graphrag_pipeline_args:
        yield "Veuillez charger un document"
        return
    
    hash_text= graphrag_pipeline_args[f"hash"]


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
    doc_name=exising_hashes[hash_text]["Nom du doc"]
    graphVis_path=WORKING_DIR/ f'{hash_text}/knowledge_graph.html'

    yield (graphVis_path, doc_name)
