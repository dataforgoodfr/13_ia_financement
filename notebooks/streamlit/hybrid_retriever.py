import pandas as pd
import time
import streamlit as st
import hashlib
from time import time as timing
import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import datetime

import dotenv

dotenv.load_dotenv("/home/chougar/Documents/GitHub/Formation_datascientest/DL-NLP/.env")



#====config llm
model_qa_name="gpt-4o-mini"
llm_qa = ChatOpenAI(model_name=model_qa_name, temperature=0.2, streaming=True)
llm_evaluator = ChatOpenAI(model_name="gpt-4o", temperature=0.2)

# Embeddings model definition
model_emb_name="text-embedding-3-small"
embedding_model = OpenAIEmbeddings(model=model_emb_name)
#===============



#=======create retrievers
def hybrid_retriever(faiss_db, docs, selected_retriever, selected_reranker):
    from langchain_community.retrievers import TFIDFRetriever
    from langchain_core.runnables import chain
    from langchain.schema import Document
    from pydantic import BaseModel, Field
    import string

    if isinstance(docs[0], dict):
        docs = [
            Document(page_content=d["page_content"], metadata=d.get("metadata", {}))
            for d in docs  # Assurez-vous que chaque dict a bien "page_content"
        ]
        
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

    def build_llm_reranker():

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
    
    @st.cache_resource
    def build_specialized_reranker():
        from sentence_transformers import CrossEncoder
        reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
        return reranker

        
    @chain
    def combine_retrievers(query: str, dense=dense, sparse=sparse, selected_retriever=selected_retriever, selected_reranker=selected_reranker, reranker_threshold=5, top_k=8) -> list:
        """
            #### Inputs:
            * query: user query \n
            * dense: dense retriever built with langchain vectorStore (chroma, faiss) "ex: faiss_db.as_retriever" \n
            * sparse: sparse retriever built with langchain retrievers (TFIDF ...) "ex: TFIDFRetriever.from_documents" \n            
            * reranker_threshold: threshold to consider to filter document relevancy, as evaluated by a reranker from 1 to 10
            * top_k: top n documents relevant, according to the reranker scoring

            #### Outputs:
            * a list of documents is str format, scored and sorted
        """
        query = query["question"]

        if selected_retriever=="all":
            dense_results = dense.invoke(query)
            sparse_results = sparse.invoke(query)
            lexical_results= lexical(query)
            # Fusionner
            results = dense_results + sparse_results + lexical_results
        elif selected_retriever=="dense":
            results = dense.invoke(query)                        
        elif selected_retriever=="sparse":
            results = dense.invoke(query)
        elif selected_retriever=="lexical":
            results = lexical(query)

        # Supprimer les doublons
        unique_results = {doc.page_content: doc for doc in results}.values()

        # Reranking
        t=timing()
        if selected_reranker=="llm":
            reranker=build_llm_reranker()
            reranked_results=[(doc.page_content, reranker.invoke({"question": query, "document": doc.page_content}).score) for doc in list(unique_results)]
            sorted_results = sorted(reranked_results, key=lambda x: x[1], reverse=True)
            # Filtrage (score >= 5)
            filtered_results = [doc for doc in sorted_results if doc[1] >= reranker_threshold]            
        elif selected_reranker=="specialized":
            reranker=build_specialized_reranker()
            reranked_scores = reranker.predict([(query, doc.page_content) for doc in unique_results])
            reranked_results=sorted(zip(unique_results, reranked_scores), key=lambda x: x[1], reverse=True)
            filtered_results=[(doc[0].page_content, doc[1]) for doc in reranked_results]
        print(f"reranking time: {timing()-t}")
        #reranked_results = reranker.predict([(query, doc.page_content) for doc in unique_results])
        # sorted_results = sorted(zip(unique_results, reranked_results), key=lambda x: x[1], reverse=True)
        


        pipeline_args["sources"]=filtered_results[:top_k]
        return [doc for doc, _ in filtered_results[:top_k]]

    sources= combine_retrievers    
    return sources
    

#=======================



#========create full rag pipeline
def build_hybrid_rag_pipeline(faiss_db, split_docs=[], selected_retriever="all", selected_reranker="llm", llm=llm_qa):
    """
    #### Inputs:
    * selected_retriever: combine dense, sparse and lexical retrievers. "all" by default \n
    """
    from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda

    retriever= hybrid_retriever(faiss_db, split_docs, selected_retriever, selected_reranker)
    pipeline_args["retriever"]=retriever
    
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


   # Chaîne principale avec streaming natif
    lcel_qa_chain = (
        RunnableParallel({
            "context": retriever,
            # "sources": retriever,
            "input": RunnablePassthrough()
        })
        | rag_prompt
        | llm
        | StrOutputParser()
    )

        

    return lcel_qa_chain


#====================================


pipeline_args={}
def process_new_doc_as_hybrid(pages: list, doc_name: str, doc_category):
    """
    #### Function definition:
    Process a new document following these steps:
    1. Generate a hash for the document and check its existence in a historical hash table \n
    2. If the document does not exist: \n
    * Cut it into chunks
    * Store the chunks in a vector/graph database
    * Save the database
    * Update the hash table
    3. Inform the user that the application is ready

    #### Inputs :
    **pages**: a list of pages in langchain Document format\n
    **doc_name**: a meaningful name given by the user

    #### Results:\n
    A generator function containing return information in str format.

    """
    

    #============vérif si PP traitée:    
    def check_doc_processed(text):
        # generate hash for curr text
        yield "Génération du hash"
        hash_text=hashlib.sha256(text.encode('utf-8')).hexdigest()

    
        # load existing hashes
        file_path="docs_hashes.json"
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






    #=====chunk text
    def chunk_text(pages):
        chunk_size=500
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_size*0.2)
        splited_docs= text_splitter.split_documents(pages)
        return splited_docs
    #===============


    #======create DB
    def create_db(docs, text, id, embedding_model=embedding_model, doc_name=doc_name):
        db_path = f"./storage/vector_stores/{id}/"        

        faiss_db = FAISS.from_documents(docs, embedding_model,)   
        faiss_db.save_local(db_path)



        # load existing hashes
        
        #@st.cache_data
        def save_hash_trace_hashes(text, hash_title, doc_name, doc_category):
            file_path="docs_hashes.json"
            exising_hashes={}
            if os.path.exists(file_path):                
                with open(file_path, 'r') as f:
                    exising_hashes= json.load(f)                    
                    
            exising_hashes[hash_text] = {
                "Nom du PP": doc_name, 
                "Titre auto": hash_title, 
                "Taille du texte (en car)": len(text),
                "Date de création": str(datetime.datetime.now()),
                "doc_category": doc_category
            }
            with open(file_path, 'w') as f:
                json.dump(exising_hashes, f)            
        
        # génerer un titre basé sur les 10000 premiers caractères
        prompt_pp_title=f"""
            Based on the folling context;\n
                {text[:10000]}

            Generate a very short and representative title useful to store an embedding index of the text
        """

        llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
        hash_title=llm.invoke(prompt_pp_title)

        if doc_name==None or doc_name=="":
            prompt_doc_name=f"""
                Based on the folling title;\n
                    {hash_title.content}

                Generate a very short label, in 3 words max
            """        
            doc_name=llm.invoke(prompt_doc_name)
            doc_name=doc_name.content
            
        save_hash_trace_hashes(text, hash_title.content, doc_name, doc_category)
        
        return (faiss_db, hash_title.content, doc_name)




    
    #===============

    print("check_doc_processed")
    # Appeler la fonction génératrice
    full_text = "\n\n".join([doc.page_content for doc in pages])
    generator = check_doc_processed(full_text)

    # Itérer sur le générateur pour exécuter le code et récupérer les messages
    for message in generator:
        # feedback de vérification
        if isinstance(message, str):
            yield (message)
        # feedback nouveau PP 
        elif isinstance(message, tuple):
            pp_processed=message[0]
            hash_text=message[1]
            yield "Traitement du document en cours"

            
            
            yield "1. Fragmentation du document"
            splitted_docs=chunk_text(pages)
            pipeline_args["split_docs"]=splitted_docs
            
            yield "2. Stockage du document en base vectorielle"
            faiss_db_args=create_db(splitted_docs, full_text, id=hash_text)
            faiss_db=faiss_db_args[0]
            faiss_db_PPtitle=faiss_db_args[1]
            faiss_db_PPname=faiss_db_args[2]
            pipeline_args["db"]=faiss_db

            yield f"""
                Document stocké sous: <br>
                **Hash**: {hash_text}<br>
                **Titre auto généré**: {faiss_db_PPtitle}<br>
                **Nom donné**: {faiss_db_PPname}
            """

            
            pipeline_args["final_chain"]=build_hybrid_rag_pipeline(faiss_db, splitted_docs, selected_reranker="specialized")
            yield "3. Création de la chaîne hybride RAG"
            

            msg="5. Traitement terminé avec succès ! Posez vos questions :)"
            print(msg)
            yield msg

            yield {"pipeline_args": pipeline_args}


# @st.cache_resource
def process_existing_doc_as_hybrid(hash: str, doc_name: str, doc_category: str):
    """
    #### Function definition:
    Load a storage associated with an existing document by following these steps:
    1. Take the hash corresponding to the selected document
    2. Load the associated storages and retrievers 
    3. Inform the user that the application is ready

    #### Inputs :
        **hash**: the hash code in a str format associated with the document/storage, which corresponds to the PP name given by the user when the document was processed first, and the storage created
    **doc_name**: the PP name of the document selected by the user

    #### Outputs:
        A generator function containing return information in str format.

    """


    #=======load DB

    # 1. Spécifiez le chemin du dossier contenant les fichiers FAISS
    db_path = f"./storage/vector_stores/{hash}/"


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
    # all_ids = docstore._dict.keys() 

    # Extraire les textes complets
    # split_docs = [docstore.search(doc_id).page_content for doc_id in all_ids]

    # 2. Récupérer tous les IDs des documents
    all_ids = list(faiss_db.index_to_docstore_id.values())

    # 3. Extraire les documents avec métadonnées
    split_docs = []
    for doc_id in all_ids:
        doc = docstore.search(doc_id)
        split_docs.append({
            "page_content": doc.page_content,
            "metadata": doc.metadata,
            "page_number": doc.metadata.get("page", "N/A")  # Numéro de page spécifique
        })

    pipeline_args["split_docs"]=split_docs
    #================================





    #==============charger la pipeline de rag
    rag_pipeline= build_hybrid_rag_pipeline(faiss_db, split_docs, selected_reranker="specialized")
    pipeline_args["final_chain"]=rag_pipeline
    yield "2. Création de la chaîne hybride RAG"

    yield "3. Traitement terminé avec succès ! Posez vos questions :)"

    yield {"pipeline_args": pipeline_args}
    
