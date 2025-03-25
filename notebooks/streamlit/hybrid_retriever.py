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
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import datetime

import dotenv

dotenv.load_dotenv("/home/chougar/Documents/GitHub/Formation_datascientest/DL-NLP/.env")



#====config llm
model_qa_name="gpt-4o-mini"
llm_qa = ChatOpenAI(model_name=model_qa_name, temperature=0.2)
llm_evaluator = ChatOpenAI(model_name="gpt-4o", temperature=0.2)

# Embeddings model definition
model_emb_name="text-embedding-3-small"
embedding_model = OpenAIEmbeddings(model=model_emb_name)
#===============



#=======create retrievers
def hybrid_retriever(faiss_db, docs):
    from langchain.retrievers import TFIDFRetriever
    from langchain_core.runnables import chain
    from langchain.schema import Document
    from pydantic import BaseModel, Field
    import string

    docs=[Document(doc) for doc in docs]
    dense = faiss_db.as_retriever(
        search_kwargs={
            "k": 8, 
            "fetch_k": 24
        },
        search_type= "mmr"
    )

    
    sparse = TFIDFRetriever.from_documents(
        documents=docs,
        k=8,
        tfidf_params={"min_df":1,
                "max_df":2,
                "ngram_range":(1, 2)}
    )



    def lexical(query, top_k=6, documents=docs, print_keywords=False):
        def remove_punctuation(text):
            text_no_punctuation = text.translate(str.maketrans('', '', string.punctuation))
            words = text_no_punctuation.split()
            return words           


        system_prompt_exact="""Extract the most relevant keywords from the following text to facilitate searching for important documents containing these terms. 
            Only provide the extracted keywords, without additional text or explanations.
        """

        system_prompt_synonyms="""
            Extract the most relevant keywords from the following text to facilitate searching for important documents.  

            - For each extracted keyword, also include its closest synonyms.  
            - Return all keywords and synonyms in a **single flat list**, without categorization, explanations, or additional text.  
            - Ensure the extracted terms are meaningful and relevant to the text's context.  

            ### **Output Format:**  
            A **comma-separated** flat list of keywords and their closest synonyms.  
        """

        prompt_extract_keyworks = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt_exact),
                ("human", "{question}"),
            ]
        )
        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        llm_extract_keyworks = prompt_extract_keyworks | llm | StrOutputParser()            
        query_keywords = llm_extract_keyworks.invoke({"question":query})
        
        query_keywords = remove_punctuation(query_keywords)  # Liste des mots-clés dans la requête
        if print_keywords:
            print(query_keywords)

        results = []


        for doc in documents:
            doc_text = doc.page_content.lower()
            # Compter les cooccurrences des mots-clés dans le document
            keyword_matches = sum(1 for word in query_keywords if word.lower() in doc_text)
            # Pondérer le score par la densité des mots-clés
            try:
                score = keyword_matches / len(doc_text.split())
            except Exception as e:
                print(e)
                score=0

            results.append((doc, score))

        # Trier les résultats par score
        ranked_results = sorted(results, key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked_results[:top_k]]

    def build_reranker():

        # Data model
        class GradeDocuments(BaseModel):
            """Score for relevance check on retrieved documents."""

            score: int = Field(
                description="Documents are relevant to the question, score from 1 (not relevant) to 10 (perfectly relevant)"
            )


        # LLM with function call
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm_grader = llm.with_structured_output(GradeDocuments)

        # Prompt
        system = """You are a grader assessing relevance of a retrieved document to a user question. \n
            It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
            If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant. \n
            Give a score from 1 (not relevant) to 10 (perfectly relevant) to indicate whether the document is relevant to the question."""
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
            ]
        )

        reranker = grade_prompt | structured_llm_grader
        
        # template:
        #eval=reranker.invoke({"question": question, "document": doc_txt}).score
        
        return reranker
    

    @chain
    def combine_retrievers(query, dense=dense, sparse=sparse, top_k=8):
        query = query["question"]
        dense_results = dense.get_relevant_documents(query)
        sparse_results = sparse.get_relevant_documents(query)
        lexical_results= lexical(query)

        # Fusionner
        combined_results = dense_results + sparse_results + lexical_results

        # Supprimer les doublons
        unique_results = {doc.page_content: doc for doc in combined_results}.values()

        # Reranking
        reranker=build_reranker()
        t=timing()
        reranked_results=[(doc.page_content, reranker.invoke({"question": query, "document": doc.page_content}).score) for doc in list(unique_results)]
        print(f"reranking time: {timing()-t}")
        #reranked_results = reranker.predict([(query, doc.page_content) for doc in unique_results])
        # sorted_results = sorted(zip(unique_results, reranked_results), key=lambda x: x[1], reverse=True)
        sorted_results = sorted(reranked_results, key=lambda x: x[1], reverse=True)

        # Filtrage (score >= 5)
        filtered_results = [doc for doc in sorted_results if doc[1] >= 5]

        return [doc for doc, _ in filtered_results[:top_k]]

    return combine_retrievers

#=======================



#========create full rag pipeline
def build_rag_pipeline(faiss_db, split_docs):
    from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
    
    retriever= hybrid_retriever(faiss_db, split_docs)

    rag_prompt = ChatPromptTemplate.from_template("""
        Answer the question based **only** on the provided context.  

        - If the context contains enough information to provide a complete or partial answer, use it to formulate a detailed and factual response.  
        - If the context lacks relevant information, respond with: "I don't know."  

        ### **Context:**  
        {context}  

        ### **Question:**  
        {input}  

        ### **Answer:**  
        Provide a clear, factual, and well-structured response based on the available context. Avoid speculation or adding external knowledge.  
    """)

    lcel_qa_chain = (
        RunnableParallel({
            # "context": retriever | (lambda split_docs: "\n\n".join(d.page_content for d in split_docs)),
            "context": retriever | (lambda split_docs: "\n\n".join(d for d in split_docs)),
            "sources": retriever,
            "input": RunnablePassthrough(),
        })
        | (lambda inputs: {
            "answer": (rag_prompt | llm_qa | StrOutputParser()).invoke(inputs),
            "sources": inputs["sources"]  
        })
    )

    return lcel_qa_chain


#====================================


pipeline_args={}
def process_new_pp(text: str, pp_name: str):

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

        if pp_name==None or pp_name=="":
            pp_name=llm.invoke(prompt_pp_name)
            pp_name=pp_name.content
            
        save_hash_trace_hashes(text, hash_title.content, pp_name)
        
        return (faiss_db, hash_title.content, pp_name)




    
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
            pipeline_args["split_docs"]=docs
            
            yield "2. Stockage du PP en base vectorielle"
            faiss_db_args=create_db(docs, text, id=hash_text)
            faiss_db=faiss_db_args[0]
            faiss_db_PPtitle=faiss_db_args[1]
            faiss_db_PPname=faiss_db_args[1]
            pipeline_args["db"]=faiss_db

            yield f"""
                PP stocké sous: <br>
                **Hash**: {hash_text}<br>
                **Titre auto généré**: {faiss_db_PPtitle}<br>
                **Nom donné**: {faiss_db_PPname}
            """

            retriever=hybrid_retriever(faiss_db, docs)
            pipeline_args["retriever"]=retriever                        
            yield "3. Création du retriever hybride"

            
            pipeline_args["final_chain"]=build_rag_pipeline(faiss_db, docs)
            yield "4. Création de la chaîne QA finale"
            

            msg="5. Traitement terminé avec succès ! Posez vos questions :)"
            print(msg)
            yield msg



def process_existing_pp(hash: str, pp_name: str):


    #=======load DB

    # 1. Spécifiez le chemin du dossier contenant les fichiers FAISS
    db_path = f"./vector_stores/{hash}/"


    # 2. Chargez la base FAISS
    faiss_db = FAISS.load_local(
        folder_path=db_path,
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    )
    pipeline_args["db"]=faiss_db

    yield "1. Chargement de la DB associée"
    #==============


    #==============récup les chunks pour les retrievers sparse et lexical
    # Accéder au magasin de documents (docstore)
    docstore = faiss_db.docstore

    # Récupérer tous les IDs des documents
    all_ids = docstore._dict.keys() 

    # Extraire les textes complets
    split_docs = [docstore.search(doc_id).page_content for doc_id in all_ids]
    pipeline_args["split_docs"]=split_docs
    #================================





    #==============charger la pipeline de rag
    rag_pipeline= build_rag_pipeline(faiss_db, split_docs)
    pipeline_args["final_chain"]=rag_pipeline
    yield "2. Construction de la chaîne Question/Réponse"

    yield "3. Traitement terminé avec succès ! Posez vos questions :)"
    
    
def QA_pipeline(queries: list,):
    if "final_chain" not in pipeline_args:
        yield "Veuillez choisir un PP"
        return 
    replies=[]
    for q in queries:        
        resp=pipeline_args["final_chain"].invoke({"question": q})
        replies.append(resp)
        print(resp)
        yield resp
        

