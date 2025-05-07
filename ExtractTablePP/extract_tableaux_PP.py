

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
            case _:
                print('Fichier non pris en charge')
    print('End of the Read PP program')
    return 
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

Read_PP_in_docx (Folder_where_the_files_are, Path_where_we_put_Outputs )

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@ END OF MAIN PROGRAM @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
