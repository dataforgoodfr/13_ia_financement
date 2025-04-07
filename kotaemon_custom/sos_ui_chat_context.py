
"""
sos_ui_chat_context.py

Interface Gradio pour le chat contextuel avec affichage d'une page PDF.
"""

import gradio as gr
from sos_pipeline import answer_question_with_context
import fitz  # PyMuPDF
import os

# Chemin temporaire vers un PDF de démonstration (à rendre dynamique ultérieurement)
PDF_PATH = "/app/data/Sante_Sud/Projet04/SS_P04_PP01.pdf"

def extract_page_texts(pdf_path):
    """
    Extrait le texte de chaque page d'un PDF.
    """
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages

pdf_pages = extract_page_texts(PDF_PATH)

def get_pdf_page(page_number):
    """
    Retourne le texte de la page indiquée.
    """
    if 0 <= page_number < len(pdf_pages):
        return pdf_pages[page_number]
    else:
        return "Page introuvable."

def chat_with_context_ui():
    """
    Interface Gradio pour un chat avec contexte et affichage d'une page PDF.
    """
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Assistant Financement")
            question = gr.Textbox(placeholder="Pose ta question ici...", label="Question")
            send_btn = gr.Button("Envoyer")
        with gr.Column(scale=2):
            gr.Markdown("### Page du document consulté")
            page_slider = gr.Slider(minimum=0, maximum=len(pdf_pages)-1, step=1, label="Page", value=0)
            doc_preview = gr.Textbox(label="Texte de la page PDF", lines=30, interactive=False)
            page_slider.change(fn=get_pdf_page, inputs=page_slider, outputs=doc_preview)

    state = gr.State([])

    def custom_chat_interaction(message, history):
        history = history + [(message, "...")]
        answer = answer_question_with_context(message)
        history[-1] = (message, answer)
        return history, history, doc_preview

    send_btn.click(fn=custom_chat_interaction, inputs=[question, state], outputs=[chatbot, state, doc_preview])
