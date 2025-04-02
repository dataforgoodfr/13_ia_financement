# import gradio as gr
# import subprocess
# from sos_doc_loader import load_documents  # ton module pour récupérer la liste des docs

# def run_ingestion():
#     try:
#         result = subprocess.run(["python", "sos_pipeline.py"], capture_output=True, text=True, check=True)
#         return result.stdout
#     except subprocess.CalledProcessError as e:
#         return f"Erreur lors de l'ingestion:\n{e.stderr}"

# with gr.Blocks() as demo:
#     gr.Markdown("# Interface Kotaemon Personnalisée")
#     with gr.Tabs():
#         with gr.Tab("Chat"):
#             gr.Markdown("Interface de chat ici …")
#             # Intègre tes composants de chat ici
#             chat_input = gr.Textbox(label="Votre question")
#             chat_output = gr.Textbox(label="Réponse")
#             gr.Button("Envoyer")  # Placeholder
#         with gr.Tab("Documents"):
#             gr.Markdown("Liste des documents ingérés")
#             refresh_btn = gr.Button("Rafraîchir la liste")
#             doc_table = gr.DataFrame(headers=["doc_id", "source", "preview"])
#             refresh_btn.click(fn=load_documents, outputs=doc_table)
#         with gr.Tab("Ingestion"):
#             gr.Markdown("Lancez l’ingestion des documents")
#             ingest_btn = gr.Button("Lancer l'ingestion")
#             ingest_output = gr.Textbox(label="Logs d'ingestion", lines=10)
#             ingest_btn.click(fn=run_ingestion, outputs=ingest_output)
    
# demo.launch()

import gradio as gr
import subprocess
from sos_doc_loader import load_documents  # ton module pour récupérer la liste des docs

def run_ingestion():
    try:
        result = subprocess.run(["python", "sos_pipeline.py"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Erreur lors de l'ingestion:\n{e.stderr}"

def query_llm(message):
    from sos_flowsettings import KH_CHAT_LLM
    response = KH_CHAT_LLM.invoke(message)
    return response.content

with gr.Blocks() as demo:
    gr.Markdown("# Interface Kotaemon Personnalisée")
    with gr.Tabs():
        with gr.Tab("Chat"):
            gr.Markdown("Interface de chat ici …")
            chat_input = gr.Textbox(label="Votre question")
            chat_output = gr.Textbox(label="Réponse")
            gr.Button("Envoyer")  # Placeholder

        with gr.Tab("Documents"):
            gr.Markdown("Liste des documents ingérés")
            refresh_btn = gr.Button("Rafraîchir la liste")
            doc_table = gr.DataFrame(headers=["doc_id", "source", "preview"])
            refresh_btn.click(fn=load_documents, outputs=doc_table)

        with gr.Tab("Ingestion"):
            gr.Markdown("Lancez l’ingestion des documents")
            ingest_btn = gr.Button("Lancer l'ingestion")
            ingest_output = gr.Textbox(label="Logs d'ingestion", lines=10)
            ingest_btn.click(fn=run_ingestion, outputs=ingest_output)

        with gr.Tab("LLM Test"):
            gr.Markdown("Testez votre LLM (Falcon ou OpenAI)")
            user_input = gr.Textbox(label="Votre message", placeholder="Posez une question au modèle…")
            llm_output = gr.Textbox(label="Réponse", lines=10, interactive=False)
            send_btn = gr.Button("Envoyer")
            send_btn.click(fn=query_llm, inputs=user_input, outputs=llm_output)

demo.launch()
