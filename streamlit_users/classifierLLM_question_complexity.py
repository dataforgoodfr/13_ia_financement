from hybrid_retriever import process_new_doc_as_hybrid, process_existing_doc_as_hybrid, update_hybrid_pipeline_args
from graphrag_retriever import create_graphdb as process_new_doc_as_graph
from graphrag_retriever import load_existing_graphdb as process_existing_doc_as_graph
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
from PathRAG import QueryParam
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
from langchain_openai import OpenAI
import json


dotenv.load_dotenv(".env")

def classifierLLM_question_complexity(the_question:str): 
    """
        #### Function definition:
        Evaluate the complexity of a question

        #### Inputs :
        **the_question**: the question to be evaluated

        #### Outputs:
        The level of complexity identified for the question = one of the 3 keywords: "simple | moderately_complex | very_complex",

    """

    # Prompt
    prompt = f"""
    You are a cognitive analysis expert, specialized in evaluating the complexity of questions.

    Goal: Classify {the_question} into one of the following three exclusive categories. A question can belong to only one category:
    - simple → factual, direct answer, requires only quick lookup or common knowledge; estimated answering time < 15 seconds.
    - moderately_complex → requires structured reasoning or combining several simple elements; estimated answering time between 15 seconds and 2 minutes.
    - very_complex → requires extended reasoning, specialized expertise, or analysis of multiple factors; estimated answering time > 2 minutes.

    Strict rules:
    1. No interpretation beyond the given text: judge complexity only from the wording of the provided question.
    2. No rephrasing: copy the question exactly as it is.
    3. Justification required (1–3 sentences) explaining the choice.
    4. No ambiguity: if a question is borderline between two categories, choose the more complex category.

    Required output format :
       a string which must be either "simple" or "moderately_complex" or "very_complex"
    """



    if the_question.strip() != '':
        system=prompt

        adjust_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the question of which you must evaluate the complexity: \n\n {the_question} \n indicate with which of the 3 categories : simple | moderately_complex | very_complex it should be associated.",
                ),
            ]
        )
        llm_evaluator = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
        evaluator_quest = adjust_prompt | llm_evaluator | StrOutputParser()
        complexity_of_quest = evaluator_quest.invoke({"the_question": the_question})
    else:
        complexity_of_quest = ""

    return complexity_of_quest

# question =  "What is the capital of France?" classifiée comme "simple"
# question =  "Explain the process of photosynthesis." classifiée comme "moderately_complex"
# question =  "How would you design a scalable distributed database system?" classifiée comme "very_complex"
question =  "How would you design a scalable distributed database system?"
complexity = classifierLLM_question_complexity(question)
print(f"The complexity of the question '{question}' is classified as: {complexity}")