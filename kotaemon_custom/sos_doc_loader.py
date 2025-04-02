# # sos_doc_loader.py
# import gradio as gr
# from sos_flowsettings import KH_DOCUMENTSTORE

# def load_documents():
#     """
#     Récupère la liste des documents depuis le docstore et retourne une liste de dictionnaires
#     pour affichage dans l’UI.
#     """
#     try:
#         # Supposons que KH_DOCUMENTSTORE a une méthode get_all() ou une méthode similaire
#         # qui renvoie la liste complète des documents ingérés.
#         docs = KH_DOCUMENTSTORE.get_all()
#     except Exception as e:
#         return f"Erreur lors de la récupération des documents: {str(e)}"
    
#     # Transforme chaque document en dictionnaire pour l'affichage
#     data = []
#     for doc in docs:
#         # On suppose que chaque document possède une metadata contenant 'source'
#         source = doc.metadata.get("source", "N/A") if doc.metadata else "N/A"
#         # Optionnel : récupérer un aperçu du contenu (par exemple, les 100 premiers caractères)
#         preview = (doc.page_content[:100] + "...") if len(doc.page_content) > 100 else doc.page_content
#         # On peut utiliser l’ID s’il est stocké dans la metadata (sinon, générer un index)
#         doc_id = doc.metadata.get("doc_id", "N/A") if doc.metadata else "N/A"
#         data.append({
#             "doc_id": doc_id,
#             "source": source,
#             "preview": preview
#         })
#     return data

# def launch_doc_loader():
#     """
#     Crée une interface Gradio simple pour afficher les documents ingérés.
#     """
#     with gr.Blocks() as demo:
#         gr.Markdown("# Documents ingérés")
#         refresh_btn = gr.Button("Rafraîchir la liste")
#         doc_table = gr.DataFrame(headers=["doc_id", "source", "preview"])
#         refresh_btn.click(fn=load_documents, outputs=doc_table)
#     demo.launch()

# if __name__ == "__main__":
#     launch_doc_loader()
# sos_doc_loader.py

import gradio as gr
import json
import lancedb

# Chemin vers le docstore
DOCSTORE_PATH = "./ktem_app_data/user_data/docstore"
COLLECTION_NAME = "docstore"

# def load_documents():
#     """
#     Charge manuellement les documents depuis LanceDB (remplace l'appel KH_DOCUMENTSTORE.get_all())
#     """
#     try:
#         db = lancedb.connect(DOCSTORE_PATH)
#         if COLLECTION_NAME not in db.table_names():
#             return [["N/A", "Aucun document trouvé", ""]]

#         table = db.open_table(COLLECTION_NAME)
#         rows = table.to_list(limit=1000)  # limite à 1000 documents pour performance

#         data = []
#         for doc in rows:
#             doc_id = doc.get("id", "N/A")
#             text = doc.get("text", "")
#             preview = (text[:100] + "...") if len(text) > 100 else text
#             metadata = json.loads(doc.get("attributes", "{}"))
#             source = metadata.get("source", "inconnu")
#             data.append([doc_id, source, preview])

#         return data

#     except Exception as e:
#         return [["Erreur", f"{str(e)}", ""]]

from sos_flowsettings import KH_DOCUMENTSTORE

def load_documents():
    try:
        # Accès direct au LanceDB table
        table = KH_DOCUMENTSTORE.db_connection.open_table(KH_DOCUMENTSTORE.collection_name)
        rows = table.to_arrow().to_pylist()
    except Exception as e:
        return f"Erreur : {str(e)}"

    data = []
    for row in rows:
        metadata = json.loads(row.get("attributes", "{}"))
        doc_id = metadata.get("doc_id", row.get("id", "N/A"))
        source = metadata.get("source", "N/A")
        preview = (row["text"][:100] + "...") if row.get("text") and len(row["text"]) > 100 else row.get("text", "")
        data.append({
            "doc_id": doc_id,
            "source": source,
            "preview": preview
        })

    return data



def launch_doc_loader():
    """
    Crée une UI Gradio minimale pour tester l'affichage des documents
    """
    with gr.Blocks() as demo:
        gr.Markdown("Documents ingérés")
        refresh_btn = gr.Button("Rafraîchir la liste")
        doc_table = gr.DataFrame(headers=["doc_id", "source", "preview"], interactive=False)
        refresh_btn.click(fn=load_documents, outputs=doc_table)

    demo.launch(server_name="0.0.0.0", server_port=7860)

if __name__ == "__main__":
    launch_doc_loader()
