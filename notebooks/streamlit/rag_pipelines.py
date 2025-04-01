from hybrid_retriever import process_new_doc_as_hybrid, process_existing_pp_as_hybrid
from utils import install_libreoffice, verify_libreoffice_installation, convert_docx_to_pdf
from io import StringIO, BytesIO
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_unstructured import UnstructuredLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma, FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import pandas as pd
import time
import streamlit as st
import hashlib
from time import time as timing
import os
import json

from pydantic import BaseModel, Field
import string
import datetime
import dotenv



dotenv.load_dotenv("/home/chougar/Documents/GitHub/Formation_datascientest/DL-NLP/.env")


pipeline_args={}
def process_new_doc(uploaded_files, doc_name: str, doc_category: str):
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
        **uploaded_file**: a single or list of document in docx or pdf format\n
        **doc_name**: a meaningful name given by the user
        **doc_category**: the type of document, maybe 'pp' or 'asso'

        #### Results:\n
        A generator function containing return information in str format.

    """

    # if uploaded_files!=list:
    #     uploaded_files=[uploaded_files]
    
    if doc_category=="" or doc_category not in ["pp", "asso"]:
        yield "Please provide a doc_category ('pp' or 'asso')"
        return

    def save_uploaded_file(uploaded_file, output_dir):
        from pathlib import Path

        """Sauvegarde un fichier uploadé dans un répertoire temporaire"""
        try:
            # Créer le répertoire de sortie s'il n'existe pas
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # Chemin complet du fichier
            file_path = Path(output_dir) / uploaded_file.name
            
            # Sauvegarder le fichier
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            return file_path
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde : {e}")
            return None        
    all_pages=[]
    for uploaded_file in uploaded_files:
    
        # Détection du type de fichier
        if uploaded_file.type == "application/pdf":                
            # pages=[Document_langchain(page.extract_text()) for page in pdf_reader.pages]

            file_path=save_uploaded_file(uploaded_file, "./data/uploads/pp")

            loader = PyPDFLoader(file_path)
            pages = loader.load()

            all_pages+=pages

        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":        
            #===============conversion des docx en pdf, non fonctionnel
            # yield "Conversion du docx en pdf pour prendre en charge les tableaux et images"

            # libreoffice_available= verify_libreoffice_installation()

            # if libreoffice_available==False:
            #     yield "Libre office indisponible, installation en cours"
            #     install_libreoffice()
            
            # save du docx en local avant sa conversion            
            # file_path=save_uploaded_file(uploaded_file, "./data/uploads/pp")
            
            # yield "Conversion en cours"
            # convert_docx_to_pdf(file_path, "./data/uploads/pp")
            #convert_with_unoserver(file_path, "./data/uploads/pp")

            #===============lire directement les docx
            file_path=save_uploaded_file(uploaded_file, f"./data/uploads/{doc_category}")
            loader = UnstructuredLoader(
                file_path,
                mode="elements",  # Active le parsing structurel
                strategy="fast"   # Équilibre vitesse/précision
            )
            docs = loader.load()

            full_text=""
            for doc in docs:
                full_text+=doc.page_content

            # Découpage approx par page (2400 car dans une page pleine)
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=2400,      # Nombre de caractères par chunk
                chunk_overlap=240,    # 10% de chevauchement entre chunks                
            )
            chunks= splitter.split_text(full_text)
            pages=[Document(chunk) for chunk in chunks]

            all_pages+=pages
        else:
            yield "Type de fichier non supporté"
            
            # sortie
            return



    if doc_category=='pp':
        messages= process_new_doc_as_hybrid(all_pages, doc_name)
    elif doc_category=="asso":
        messages= process_new_doc_as_hybrid(all_pages, doc_name)

    for feedback in messages:
        if isinstance(feedback, str):
            yield feedback
        elif isinstance(feedback, dict):
            pipeline_args["hybrid_pipeline"]=feedback["pipeline_args"]


def process_existing_pp(hash: str, pp_name: str):
    """
    #### Function definition:
    Load a storage associated with an existing document by following these steps:
    1. Take the hash corresponding to the selected document
    2. Load the associated storages and retrievers 
    3. Inform the user that the application is ready

    #### Inputs :
        **hash**: the hash code in a str format associated with the document/storage, which corresponds to the PP name given by the user when the document was processed first, and the storage created
    **pp_name**: the PP name of the document selected by the user

    #### Outputs:
        A generator function containing return information in str format.

    """

    #1. create vector db
    for feedback in process_existing_pp_as_hybrid(hash, pp_name):
        if isinstance(feedback, str):
            yield feedback
        elif isinstance(feedback, dict):
            pipeline_args["hybrid_pipeline"]=feedback["pipeline_args"]

def QA_pipeline(queries: list,):

    """
    ### Function definition:\n
    Build rag pipeline and submit queries\n

    ### Inputs:
    **queries**: a list of user queries, where each element is the raw query in str format

    ### Outputs:
    A generator function that contains return information for three cases, in three distinct formats:\n
    1. A str that informs that a PP document should be loaded first
    2. A sub-generator function that streams the response of the llm \n
    3. A dict that transmits the source documents produced by the rag pipeline
    """    

    def rag_chain_switcher(classification_task):
        model_qa_name="gpt-4o-mini"
        llm = ChatOpenAI(model_name=model_qa_name, temperature=0,)

        if classification_task=="open/close question":
            sys_prompt="""
                You are an intelligent assistant tasked with classifying a given question into one of two categories: "open" or "close". Your decision must be based on the nature of the question:

                Close Questions are those that ask for specific details or information. They are typically structured to elicit direct, concise answers. These questions include:
                Requests for specific data (e.g., project title, dates, budget figures).
                Questions that list multiple bullet points with clear, targeted queries.
                Inquiries that require factual, objective responses with minimal explanation.
                Open Questions require answers that involve a broader context, reasoning, or synthesis. They are designed to gather insights, multiple concepts, or overall narratives. These questions include:
                Overviews of project objectives, context, or background.
                Inquiries that ask for analysis of outcomes, challenges, or the broader impact.
                Questions that invite descriptive or exploratory responses and may need a logical deduction.
                Instructions:

                Read the question carefully.
                Analyze if the question demands detailed, specific facts (classify as "close") or if it requires explanation, synthesis, and reasoning (classify as "open").
                Output a single label: either "open" or "close".
                Examples:

                Project Name question:
                "What is the title of your project? Does the title reflect the project's field, include a geographical area, and is it engaging?"
                → close

                Project Overview question:
                "What is the project about in one concise paragraph? What are the key problems, objectives, and expected results?"
                → open

                Submitting Organization question (detailing name, address, contact, mission, history, and goals):
                → close

                Context and Background question (exploring the current situation, history, previous interventions, and policy impacts):
                → open
                                                        
                Your output should strictly be one of these two labels without additional commentary. Follow these instructions precisely to ensure accurate classification.
            """

                # Data model

            class ClassifyQuestion(BaseModel):
                """Classfication for open/close questions"""

                type: str = Field(
                    description="The question is open or close, output 'close' or 'open'"
                )
        elif classification_task=="asso question":
            sys_prompt="""
                You are a classification model designed to analyze whether a question concerns the identification of an association (also called 'lead organisation') in a funding application form. 
                A question belongs in the “yes” category if it seeks general information about the organization, such as its name, history, mission, partners or human and financial resources. 
                A question falls into the “no” category if it concerns other aspects of the project or funding application that are not directly related to the organization's identity.
                If the question is ambiguous and could reasonably fall into both categories, it should be classified as “uncertain”.

                Instructions
                If the question asks for information about the organization (name, history, mission, capabilities, members, partners, etc.), it should be classified as “uncertain”.

                If the question does not concern the organization itself, but rather the project, the project context or detailed financial aspects, it is classified as “no”.

                If the question is ambiguous and may concern both the identity of the association and another area, it is classified as “uncertain”.

                Commented examples
                Category "yes" (question relating to the association's identity)
                "Lead organisation’s primary focus ?" → yes

                "Lead organisation’s experience and expertise" → yes

                "Project leader’s full name and email address" → yes

                "The organization and its ecosystem (member of networks, affiliations, etc.)" → yes

                "Description of the organisation’s mission and vision" → yes

                "Does your organisation have a track record of managing projects of equivalent scale?" → yes

                "Does your organisation have a track record of engaging in the area of work proposed?" → yes

                "Does your organisation have the capacity to implement the proposed intervention?" → yes

                "Historical background of the applicant" → yes

                "Organization of the applicant" → yes

                "Context and Background" → yes

                "Relevant Stakeholders" → yes

                Category "uncertain" (question ambiguous beyween the identity of the association and other aspects)
                "Geographical location (regional? national?)" → uncertain

                "Annual budget in euros (last financial year)?" → uncertain

                "Number of volunteers?" → uncertain

                "Number of members?" → uncertain

                "Main partners (institutional, operational, financial)?" → uncertain

                "Description of the organization and its staff" → uncertain

                "Partners" → uncertain

                Category "no" (question not relating to the association's identity)
                "What are the expected outcomes of the project?" → no

                "What is the total budget requested for this project?" → no

                "What are the risks associated with the project?" → no

                "What monitoring and evaluation mechanisms will be used?" → no

                Expected output format
                Answer only yes, no or uncertain, without further explanation.
            """

            class ClassifyQuestion(BaseModel):
                """Classfication for yes/no questions"""

                type: str = Field(
                    description="The question is related to association identification or not, output 'yes', 'no' or 'uncertain'"
                )
        else:
            return "Provide a valid classification taks: 'open/close question', 'asso question'"


        # LLM with function call
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        structured_llm_classifier = llm.with_structured_output(ClassifyQuestion)

        # Prompt
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", sys_prompt),
                ("human", "Classify the question as close or open \n\n User question: {question}"),
            ]
        )

        question_classifier = grade_prompt | structured_llm_classifier

        return question_classifier
        
    def query_rewriter(question):

        "v3"
        system="""
            You are a question rewriter tasked with improving input questions to optimize them for vector store retrieval. 
            Your mission is to refine, rephrase, and enhance the provided questions to ensure they are:
            * Clear and easy to understand.
            * Concise and focused.
            * Optimized for effective retrieval by removing ambiguities, unnecessary words, and redundancies.
            * Written in an interrogative form while preserving the original intent.

            #### Input Fields to Rework:
            * Project Description: Reword questions that focus on the project’s overall scope and objectives.
            * Country and City: Refine questions to specifically inquire about the project’s location.
            * Target Beneficiaries: Enhance questions to clarify the population or group that benefits from the project.
            * Number of People Concerned: Rework questions to quantify how many people the project impacts.
            * Context, Environment, Project Rationale, and Challenges: Rephrase questions that ask for background information, challenges, and the reasoning behind the project.
            * Project Start Date / End Date: Rework questions regarding the project’s timeline.
            * Financial Information:
                * Project Budget: Reword questions about the overall project budget.
                * Total Project Cost: Rephrase inquiries about the total cost of the project.
                * Donation Request Amount: Refine questions asking about the amount of funding requested.
                * Provisional Project Budget: Rework questions about the detailed provisional budget for the project.
                * Current Year Budget: Enhance questions related to the budget specific to the current year.


            #### Response Format:
            For each input question, rephrase it in a clear, concise, and interrogative form, optimized for vector store retrieval. Return only the reworked question.
        """

        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the initial question: \n\n {question} \n Formulate an improved question.",
                ),
            ]
        )
        llm_rewriter = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
        question_rewriter = re_write_prompt | llm_rewriter | StrOutputParser()
        enhanced_query= question_rewriter.invoke({"question": question})    

        return enhanced_query
    
    

    question_classifier_openORclose=rag_chain_switcher(classification_task="open/close question")
    question_classifier_asso=rag_chain_switcher(classification_task="asso question")

    if "hybrid_pipeline" not in pipeline_args and "graph_pipeline" not in pipeline_args:
        yield "Veuillez choisir un PP"
        return 
    
    replies=[]
    for q in queries:        
        
        # déterminer le type de question
        openORclose_question= question_classifier_openORclose.invoke({"question": q})

        enhanced_query=query_rewriter(q)
        if openORclose_question.type=='close':
            
            asso_question= question_classifier_asso.invoke({"question": q})

            stream_resp=pipeline_args['hybrid_pipeline']["final_chain"].stream({"question": enhanced_query})    
            yield stream_resp
            
            yield {"sources": pipeline_args["hybrid_pipeline"]["sources"]}

            yield {'uid': 'uid', "question": q, 
                   "enhanced_question": enhanced_query, 
                   "question_type": openORclose_question.type,
                    "question_asso": asso_question.type   
                }

        elif openORclose_question.type=="open":
            yield 'Graphrag pipeline in progress'

            yield {
                    'uid': 'uid', "question": q, "enhanced_question": enhanced_query, 
                    "question_open_close": openORclose_question.type,
                    "question_asso_yes_no": asso_question.type   
                }   
                
