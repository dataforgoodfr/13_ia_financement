import pandas as pd
import geopandas as gpd
import numpy as np
import time
import streamlit as st
import hashlib
from time import time as timing
import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
import datetime

import dotenv

dotenv.load_dotenv("/home/chougar/Documents/GitHub/Formation_datascientest/DL-NLP/.env")

def process_pp(text, pp_name=None):

    #============vérif si PP traitée:    
    def check_pp_processed(text):
        # generate hash for curr text
        yield "Génération du hash"
        hash_text=hashlib.sha256(text.encode('utf-8')).hexdigest()

    
        # load existing hashes
        file_path="pp_hashes.json"
        #@st.cache_data
        def load_hashes(file_path=file_path):
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return json.load(f)
            return {}
        
        print("load hashes")
        yield "Chargement de l'historique de hashage"
        exising_hashes=load_hashes()

        # check if current text has been processed with its hash 
        # 1. hash exists, exit
        print("check hash")
        if hash_text in exising_hashes:
            msg="Ce PP a déjà été traité"
            print(msg)
            print(hash_text)
            yield msg

            
        # 2. hash do not exist, return confirmation to streamlit and continue processins
        else:
            
            msg="Nouveau PP identifié"
            yield msg
            print(msg)
            print(hash_text)


            yield (False, hash_text)

    #================




    #====config llm
    model_qa_name="gpt-4o-mini"
    llm_qa = ChatOpenAI(model_name=model_qa_name, temperature=0.2)
    llm_evaluator = ChatOpenAI(model_name="gpt-4o", temperature=0.2)

    # Embeddings model definition
    model_emb_name="text-embedding-3-small"
    embedding_model = OpenAIEmbeddings(model=model_emb_name)
    #===============





    #=====chunk text
    def chunk_text(text):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=400)
        return text_splitter.split_text(text)            
    #===============


    #======create DB
    def create_db(docs, text, id, embedding_model=embedding_model, pp_name=pp_name):
        db_path = f"./vector_stores/{id}/"        

        faiss_db = FAISS.from_texts(docs, embedding_model,)   
        faiss_db.save_local(db_path)



        # load existing hashes
        
        #@st.cache_data
        def save_hash_trace_hashes(text, hash_title, pp_name):
            file_path="pp_hashes.json"
            exising_hashes={}
            if os.path.exists(file_path):                
                with open(file_path, 'r') as f:
                    exising_hashes= json.load(f)                    
                    
            exising_hashes[hash_text] = {
                "Nom du PP": pp_name, 
                "Titre auto": hash_title, 
                "Taille du texte (en car)": len(text),
                "Date de création": str(datetime.datetime.now())
            }
            with open(file_path, 'w') as f:
                json.dump(exising_hashes, f)            
        
        # génerer un titre basé sur les 10000 premiers caractères
        prompt_pp_title=f"""
            Based on the folling context;\n
                {text[:10000]}

            Generate a very short and representative title useful to store an embedding index of the text
        """

        prompt_pp_name=f"""
            Based on the folling title;\n
                {text[:10000]}

            Generate a very short label, in 3 words max
        """        
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        hash_title=llm.invoke(prompt_pp_title)

        if pp_name==None:
            pp_name=llm.invoke(prompt_pp_name)
            pp_name=pp_name.content
            
        save_hash_trace_hashes(text, hash_title.content, pp_name)
        
        return (faiss_db, hash_title.content)

    #=======load DB


    #==============



    #=======create retrieve
    
    
    #===============

    print("check_pp_processed")
    # Appeler la fonction génératrice
    generator = check_pp_processed(text)

    # Itérer sur le générateur pour exécuter le code et récupérer les messages
    for message in generator:
        # feedback de vérification
        if isinstance(message, str):
            yield (message)
        # feedback nouveau PP 
        elif isinstance(message, tuple):
            pp_processed=message[0]
            hash_text=message[1]
            yield "Traitement du PP en cours"
            time.sleep(2)
            
            
            yield "1. Fragmentation du PP"
            docs=chunk_text(text)
            
            yield "2. Stockage du PP en base vectorielle"
            faiss_db_args=create_db(docs, text, id=hash_text)
            faiss_db=faiss_db_args[0]
            faiss_db_title=faiss_db_args[1]

            yield f"""
                PP stocké sous: <br>
                **Hash**: {hash_text}<br>
                **Titre auto généré**: {faiss_db_title}<br>
                **Nom donné**: {pp_name}
            """

            yield "3. Création du retriever hybride"
            
            msg="4. Traitement terminé avec succès !"
            print(msg)
            yield msg
            


