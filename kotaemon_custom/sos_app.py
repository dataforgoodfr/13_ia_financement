import gradio as gr
import subprocess
from sos_doc_loader import load_documents
from sos_pipeline import answer_question_with_context, assistant_aap_ui

def run_ingestion():
    try:
        result = subprocess.run(["python", "sos_pipeline.py"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Erreur lors de l'ingestion:\n{e.stderr}"

with gr.Blocks() as demo:
    gr.Markdown("# GroupeSOS - IA Financement")

    with gr.Tabs():
        # Onglet Chat
        with gr.Tab("Chat"):
            gr.Markdown("### Posez une question")
            user_input = gr.Textbox(label="Votre question", placeholder="Ex: Quels sont les critères de financement ?")
            llm_output = gr.Textbox(label="Réponse", lines=10, interactive=False)
            send_btn = gr.Button("Envoyer")
            send_btn.click(fn=answer_question_with_context, inputs=user_input, outputs=llm_output)

        # Onglet Documents
        with gr.Tab("Documents"):
            gr.Markdown("### Liste des documents ingérés")
            refresh_btn = gr.Button("Rafraîchir la liste")
            doc_table = gr.DataFrame(headers=["doc_id", "source", "preview"], interactive=False)
            refresh_btn.click(fn=load_documents, outputs=doc_table)

        # Onglet Ingestion
        with gr.Tab("Ingestion"):
            gr.Markdown("### Lancez l’ingestion des documents")
            ingest_btn = gr.Button("Lancer l'ingestion")
            ingest_output = gr.Textbox(label="Logs d'ingestion", lines=10)
            ingest_btn.click(fn=run_ingestion, outputs=ingest_output)

        # Onglet Assistant AAP (rendu par assistant_aap_ui)
        with gr.Tab("Assistant AAP"):
            assistant_aap_ui().render()

demo.launch()

