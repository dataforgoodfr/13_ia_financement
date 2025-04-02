import gradio as gr
import json
import lancedb

# Chemin vers le docstore
DOCSTORE_PATH = "./ktem_app_data/user_data/docstore"
COLLECTION_NAME = "docstore"

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
