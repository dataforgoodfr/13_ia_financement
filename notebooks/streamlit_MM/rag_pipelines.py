from hybrid_retriever import process_new_doc_as_hybrid, process_existing_doc_as_hybrid
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



dotenv.load_dotenv(".env")


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



    
    messages= process_new_doc_as_hybrid(all_pages, doc_name, doc_category)
    
    for feedback in messages:
        if isinstance(feedback, str):
            yield feedback
        elif isinstance(feedback, dict):
            pipeline_args[f"hybrid_pipeline_{doc_category}"]=feedback["pipeline_args"]

            source_language=get_source_langage_wrap(pages)
            pipeline_args[f"{doc_category}_source_language"]=source_language


def process_existing_doc(hash: str, doc_name: str, doc_category: str):
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
    for feedback in process_existing_doc_as_hybrid(hash, doc_name, doc_category):
        if isinstance(feedback, str):
            yield feedback
        elif isinstance(feedback, dict):
            pipeline_args[f"hybrid_pipeline_{doc_category}"]=feedback["pipeline_args"]

            pages=feedback["pipeline_args"]["split_docs"]
            source_language=get_source_langage_wrap(pages)
            pipeline_args[f"{doc_category}_source_language"]=source_language




def get_source_langage():
    model_qa_name="gpt-4o-mini"
    llm = ChatOpenAI(model_name=model_qa_name, temperature=0,)


    sys_prompt="""
        You are an assistant tasked with the detection of the language of a given text

        Read the text carefully.            
                                                
        Your output should strictly be one of these labels;
        "french": the text is written in french
        "english": the text is written in english
        "other": other language than french or english

    """

    # Data model
    class DetectLanguage(BaseModel):
        """Language detection"""

        type: str = Field(
            description="The language of the text is 'french', 'english' or 'other'"
        )


    # LLM with function call
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm_classifier = llm.with_structured_output(DetectLanguage)

    # Prompt
    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", sys_prompt),
            ("human", "What is the language of the given text \n\n Text: {text}"),
        ]
    )

    language_classifier = grade_prompt | structured_llm_classifier

    return language_classifier


def get_source_langage_wrap(pages):
    text=""
    for p in pages[:2]:
        if isinstance(p, Document):
            text+=p.page_content+"\nn"
        elif 'page_content' in p:
            text+=p["page_content"]+"\nn"            

    source_language=get_source_langage().invoke({"text": text})
    return source_language.type



def QA_pipeline(queries: list, return_sources=True):

    """
        ### Function definition:\n
        Build rag pipeline and submit queries\n

        ### Inputs:
        **queries**: a list of user queries, where each element is either the raw query in str format, or a dict containing the raw query and other features
        **return_sources**: a boolean flag to get back used sources

        ### Outputs:
        A generator function that contains return information for three cases, in three distinct formats:\n
        1. A str that informs that a PP document should be loaded first
        2. A sub-generator function that streams the response of the llm \n
        3. A dict that transmits the source documents produced by the rag pipeline
    """    


    if "hybrid_pipeline_pp" not in pipeline_args and "graph_pipeline" not in pipeline_args:
        yield "Veuillez choisir un PP"
        return     
    elif 'hybrid_pipeline_asso' not in pipeline_args:
        yield "Veuillez choisir une fiche asso"
        return         
    
    def rag_chain_switcher(classification_task):
        model_qa_name="gpt-4o-mini"
        llm = ChatOpenAI(model_name=model_qa_name, temperature=0,)

        if classification_task=="open/close question":
            sys_prompt_v1=sys_prompt_v2="""
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
            "v1"
            sys_prompt_v1="""
                You are an AI model specializing in text classification. Your task is to determine whether a given question belongs to the category of "association identification."

                A question belongs to "association identification" if it seeks information about the legal identity, structure, history, personnel, governance, financials, or network of an organization. This includes details about:

                The organization's name, legal status, registration, and address

                The organization's experience, mission, and primary focus

                The number of employees, volunteers, and organizational structure

                Financial information such as budget or income

                The organization's partnerships and networks

                The key contacts and representatives of the organization

                A question does not belong to "association identification" if it asks about:

                A specific project the organization is seeking funding for

                The objectives, impact, or beneficiaries of a project

                Details of a proposed intervention, methodology, or implementation plan

                Output Format:
                Respond only with "yes" if the question falls into this category.
                Respond only with "no" if the question does not belong to this category.
                Respond only with "uncertain" if the question the question is ambigious and may fall in both categories.

                Example Inputs and Expected Outputs:

                Input: "What is the legal status of your organization?"
                Output: "Association Identification"

                Input: "Describe the main goals and impact of your project."
                Output: "Not Association Identification"

                Input: "How many full-time employees does your organization have?"
                Output: "Association Identification"

                Input: "What is the main challenge your project aims to solve?"
                Output: "Not Association Identification"
            """
            
            "v2"
            sys_prompt_v2="""
                You are a classification model designed to analyze whether a question concerns the identification of an organization (also called 'lead organisation' or 'association') in a funding application form. 
                A question belongs in the “yes” category if it seeks general information about the organization, such as its name, history, mission, partners or human and financial resources. 
                A question falls into the “no” category if it concerns other aspects of the project or funding application that are not directly related to the organization's identity.
                If the question is ambiguous and could reasonably fall into both categories, it should be classified as “uncertain”.

                Instructions
                If the question asks for information about the organization (name, history, mission, capabilities, members, partners, etc.), it should be classified as “uncertain”.

                If the question does not concern the organization itself, but rather the project to fund, the project context or detailed implementaion aspects, it is classified as “no”.

                If the question is ambiguous and may concern both the identity of the organization and another area, it is classified as “uncertain”.

                Commented examples
                Category "yes" (question relating to the organization's identity)
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
                ("system", sys_prompt_v1),
                ("human", "Classify the following question  \n\n User question: {question}"),
            ]
        )

        question_classifier = grade_prompt | structured_llm_classifier

        return question_classifier
        
    def query_rewriter(question, language):

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
            Important: keep the source language of the query
        """

        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the initial question: \n\n {question} \n Formulate an improved question and keep its the source language which is {language}.",
                ),
            ]
        )
        llm_rewriter = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
        question_rewriter = re_write_prompt | llm_rewriter | StrOutputParser()
        enhanced_query= question_rewriter.invoke({"question": question, "language": language})    

        return enhanced_query
   
    def query_translator(question, language):

            "v3"
            system="""
                You are an assistant specialized in text translation. 
                Translate the input text accurately, preserving its full meaning and nuances.
            """

            translator_prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system),
                    (
                        "human",
                        "Here is the initial text: \n\n {question} \n Perform a translation in {language}.",
                    ),
                ]
            )
            llm_translator = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
            question_translator = translator_prompt | llm_translator | StrOutputParser()
            translated_query= question_translator.invoke({"question": question, "language": language})    

            return translated_query
        
    # instancier les classifiers de question open/close et asso
    question_classifier_openORclose=rag_chain_switcher(classification_task="open/close question")
    question_classifier_asso=rag_chain_switcher(classification_task="asso question")


    
    # normaliser le format des questions selon formulaire app ou requête utilisateur directe    
    queries_norm=[]
    # question directe
    if "uid" not in queries[0]:
        for q in queries:
            queries_norm.append({"uid": "xxx", "question": q["question"]})
    else:
        queries_norm=queries


    for q in queries_norm:

        query=q["question"]
        
        # déterminer les types de la question
        #1. question ouverte/fermée
        openORclose_question= question_classifier_openORclose.invoke({"question": query})
        #2. question sur pp/asso
        asso_question= question_classifier_asso.invoke({"question": query})
        
        
        if asso_question.type == 'no':
            doc_category="pp" 
        elif asso_question.type== "yes":
            doc_category="asso"
        elif asso_question.type=="uncertain":
            yield "Impossible de détetminer le type de question asso/pp"            
            return

        #======forcer vers le rag hybride en cas de question asso
        # si la question porte sur l'asso, forcer le type de rag à hybride
        if asso_question.type=="yes":
            openORclose_question.type="close"

        #==========================================================




        #============= déterminer la langue de la question et traduire si nécessaire
        #if asso_question.type=="yes":
        #1.=====langue de la question
        query_source_language=get_source_langage().invoke({"text": query})


        #2.======= traduire la question
        reverse_translation=False
        doc_source_language=pipeline_args[f"{doc_category}_source_language"]
        if doc_source_language!=query_source_language.type:
            query=query_translator(query, doc_source_language)
            reverse_translation=True

        #3.======= améliorer la formulation de la question
        enhanced_query=query_rewriter(query, doc_source_language)

        #===========================================================================


        #normaliser question type à retourner
        question_asso_or_pp= "asso" if asso_question.type =="yes" else "pp"

        # orienter vers la meilleure chaine rag
        if openORclose_question.type=='close':

            stream_resp=pipeline_args[f'hybrid_pipeline_{doc_category}']["final_chain"].stream({
                "question": enhanced_query, "query_language": query_source_language.type
            })    
            #yield stream_resp
            yield {'question': q["question"], "response_stream": stream_resp}
            
            if return_sources: #modif mme
                hybrid_pipeline_data = pipeline_args.get(f"hybrid_pipeline_{doc_category}", {})
                sources = hybrid_pipeline_data.get("sources", [])
                yield {"sources": sources}#

            yield {'uid': q["uid"], "question": q["question"], 
                   "enhanced_question": enhanced_query, 
                   "question_close_or_open": openORclose_question.type,
                    "question_asso_or_pp": question_asso_or_pp,
                    "source_doc_language": pipeline_args[f"{doc_category}_source_language"],
                    "translation_requiered": reverse_translation
                }

        elif openORclose_question.type=="open":
            yield 'Graphrag pipeline in progress'

            yield {
                    'uid': q['uid'], "question": q["question"], "enhanced_question": enhanced_query, 
                    "question_close_or_open": openORclose_question.type,
                    "question_asso_or_pp": question_asso_or_pp,
                    "source_doc_language": pipeline_args[f"{doc_category}_source_language"],
                    "translation_requiered": reverse_translation
                }   
                