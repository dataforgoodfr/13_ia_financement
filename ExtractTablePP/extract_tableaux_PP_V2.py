

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@ "SCAN PARAGRAPHS & TABLES TOP DOWN" FUNCTION @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
def iter_block_items(parent):
    """
    Yield each paragraph and table child within *parent*, in document
    order. Each returned value is an instance of either Table or
    Paragraph. *parent* would most commonly be a reference to a main
    Document object, but also works for a _Cell object, which itself can
    contain paragraphs and tables.
    """
    import docx
    from docx.document import Document
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph

    if isinstance(parent, Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("something's not right")

    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@ "END OF SCAN PARAGRAPHS & TABLES TOP DOWN" FUNCTION @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


#@@@@@@@@@@@@@@@@@@@@@@@@@@@@ "ANSWER QUESTION FROM TEXT WITH IA" FUNCTION @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def IA_answer_question_on_text(text_to_read : list, question: str,size_answer="")-> str: 
    """
        #### Function definition:
        Read the text with IA and return an answer to the question asked

        #### Inputs :
        **text_to_read**: a list of text containing text and also text extracted from tables identified with tag <table> and </table>
        **question**: a text of a question to be asked to the IA about the list of text text_to_read
        **size_answer**: The size required for the answer - default = "" (no size required)

        #### Outputs:
        A generator function containing return information in str format.
    """

    import streamlit as st
    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    import pandas as pd
    from pathlib import Path
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from langchain_core.output_parsers import StrOutputParser

    from langchain_community.document_loaders import PyPDFLoader
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    import os
    import pandas as pd
    import json

    # pour télécharger l'AAP en docx
    from docx import Document
    from docx.shared import Pt

    if text_to_read!=[] and question!="":
        # 1 ######### answer the question about the text to read
        system="""
            You have to answer the {question} asked by the user based on the {text_to_read} provided.
            {text_to_read} is a list of texts containing either normal text or text extracted from tables.
            The text extracted from tables is identified by the tag <table> indicating the beginning of the table and the tag </table> indicating the end of the table
            answer the {question} based on the {text_to_read}
            #### Response Format:
            it must be clear, easy to understand and the language must be the same as the input
        """

        answer_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the list of texts: \n\n {text_to_read} \nhere is the question: \n\n {question} \nanswer the {question} based on the {text_to_read}.",
                ),
            ]
        )
        llm_answerer = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
        answerer_resp = answer_prompt | llm_answerer | StrOutputParser()
        resp = answerer_resp.invoke({"question": question, "text_to_read": text_to_read})
    else:
        resp="No text to read or no question asked"
    
        
    # 2 ######### adjust the text to read to the size of the answer if size_answer is not empty
    if size_answer!="" and resp!="No text to read or no question asked":
        system="""
            summarize the text {resp} into a text of {size_answer}, keeping the main ideas
            #### Response Format:
            it must be clear, easy to understand and the language must be the same as the input
        """

        adjust_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the initial text: \n\n {resp} \n summarize it in a text of {size_answer}.",
                ),
            ]
        )
        llm_adjuster = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
        adjustor_resp = adjust_prompt | llm_adjuster | StrOutputParser()
        adjusted_resp = adjustor_resp.invoke({"resp": resp, "size_answer": size_answer})
    else:
        adjusted_resp=resp
    # 3 ######### return the answer
    return adjusted_resp
    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ "ANSWER QUESTION FROM TEXT WITH IA" FUNCTION @


#@@@@@@@@@@@@@@@@@@@@@@@@@@@ "READ PP IN DOCX" FUNCTION @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
def Read_PP_in_docx (PathFolderSource, PathForOutputsAndLogs):
    """
    Function to read the Paragraphs and tables inside files with .docx extension contained in a folder
    It is written to a list where text of paragraphs and content of tables transformed into csv are listed in the order of the document


    Args:
        PathFolderSource: Path to the folder containing the files to be read
        PathForOutputsAndLogs: Path to the folder containing the log file
            
    Returns:
        The function returns a list of strings and csv text - Strings = text of paragraphs - csv text = content of tables  
        It also logs errors in a file named "logs-IA_for_Asso.txt" in the folder "PathForOutputsAndLogs"
    """


    #Create a list of path to all the files (no hidden files) contained in the folder “PathFolderSource” 
    import glob
    FilesWithPath = []
    for file in glob.glob(PathFolderSource +'*.*'):
        FilesWithPath.append(file)
    import pandas as pd

    ListePP =[] # List containing the text and the tables of the document docx named PP
    # read content of the files, only if they are .docx (extension to other file types possible with the match - case)
    for file in FilesWithPath:
        TheExtension = file [-4:] 
        match TheExtension:
            case 'docx':
                try:
                    #with open(PathForOutputsAndLogs + r'/' + "LePP.txt", 'w') as output:
                    f = open(file, 'rb')
                    document = Document(f)
                    NameOfDocument = file.split('/')[-1] # Name of the file without the path will be used in the Key of the dictionnary

                    for block_item in iter_block_items(document): # scan of document top down (paragraphs @ tables)
                        #============== 1 - TREATMENT OF "FULL TEXT" PARAGRAPHS (NOT TABLES)================================================    
                        if isinstance(block_item, Paragraph): # treatment of a "full text" paragraph (not table) 
                            if block_item.text.strip() !='':
                                ListePP.append(block_item.text) # Add the text of a full text paragraph

                        #============== 2 - TREATMENT OF TABLES WITH CELLS================================================    
                        elif isinstance(block_item, Table): # treatment of a table with cells
                            #Put a tag "start of table" in the list : <table> + OLD '\n<table>\n'
                            ListePP.append('<table>') # Add the text of a full text paragraph

                            # Create a DataFrame structure with empty strings, sized by the number of rows and columns in the table
                            Listdf = [['' for _ in range(len(block_item.columns))] for _ in range(len(block_item.rows))]
                            # Iterate through each row in the current table
                            for i, row in enumerate(block_item.rows):
                                # Iterate through each cell in the current row
                                for j, cell in enumerate(row.cells):
                                # If the cell has text, store it in the corresponding DataFrame position
                                    if cell.text:
                                        Listdf[i][j] = cell.text

                            # convert listdf (list of table content) -> Dataframe -> csv and append to ListPP (list of PP content)
                            ListePP.append(pd.DataFrame(data=Listdf).to_csv())
                        
                            #Put a tag "end of table" in the list : </table> + OLD '\n</table>\n'
                            ListePP.append('</table>') # Add the text of a full text paragraph
                        
                        else:
                            MessageError = str(datetime.now()) + ' Error encountered when browsing the blocks of Word docx in file ' + file
                            logging.error(MessageError)
                            print(MessageError)
                    print (ListePP)
                    
                except IOError:
                        MessageError = str(datetime.now()) + ' Error encountered when reading Word docx file ' + file
                        logging.error(MessageError)
                        print(MessageError)
                finally:        
                    f.close()
            
                        #============== 3 - READ THE TEXT WITH IA ================================================    
                
            
            case _:
                print('Fichier non pris en charge')
    print('End of the Read PP program')
    return ListePP
#@@@@@@@@@@@@@@@@@@@@@@@ END OF "READ PP IN DOCX" FUNCTION @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@


#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ MAIN PROGRAM @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# Settings for the path files
Path_where_we_put_Outputs = r'/Users/jfm/Library/CloudStorage/OneDrive-Personnel/Python yc Dev D4G/3 - Dev IA Asso/Pour les logs/' 
Folder_where_the_files_are = r'/Users/jfm/Library/CloudStorage/OneDrive-Personnel/Python yc Dev D4G/3 - Dev IA Asso/LesFilesA Lire/'

from docx import Document # import de python-docx
#import docx
#from docx.document import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
import re

#activate logging of errors in a txt file
from datetime import datetime
import logging
logging.basicConfig(filename=Path_where_we_put_Outputs + r'/logs-IA_for_Asso.txt')

text_to_read = Read_PP_in_docx (Folder_where_the_files_are, Path_where_we_put_Outputs )
the_answer = IA_answer_question_on_text(text_to_read, " What is the final expected number of teachers trained ?") 
print(the_answer)
the_answer = IA_answer_question_on_text(text_to_read, " What is the number of students involved in campaign in 2023 ?") 
print(the_answer)
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ END OF MAIN PROGRAM @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
