
"""
sos_app.py

Interface principale de l'application, fusionnant :
- AAP Assistance (extraction des questions)
- Chat Assistance (interaction LLM basé sur le PP ou fallback vers la DB)
- Ingestion (chargement et gestion des documents)

L'affichage du document PP se fait page par page (au format A4) avec images, tableaux, etc.
Pour les PP au format DOC/DOCX, le document est converti en PDF via LibreOffice.
"""

import gradio as gr
import subprocess
import re
import base64
import fitz  # PyMuPDF
import os
from docx import Document

from sos_doc_loader import load_documents
from sos_pipeline import (
    extract_questions_from_aap,
    reset_data,
    answer_question_with_context  # fallback vers la DB
)
from sos_flowsettings import KH_CHAT_LLM

##############################################
# FONCTIONS UTILITAIRES
##############################################

def run_ingestion():
    """
    Lance le script d'ingestion via subprocess.
    """
    try:
        result = subprocess.run(["python", "sos_pipeline.py"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Erreur lors de l'ingestion:\n{e.stderr}"

def extract_pages_from_pdf(pdf_path):
    """
    Extrait le texte de chaque page d'un PDF et renvoie une liste.
    """
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages

def extract_text_from_docx(docx_path):
    """
    Retourne l'intégralité du texte d'un fichier DOCX.
    """
    doc_file = Document(docx_path)
    paragraphs = [para.text for para in doc_file.paragraphs]
    return "\n".join(paragraphs)

def convert_doc_to_pdf(file_path):
    """
    Convertit un fichier DOC ou DOCX en PDF via LibreOffice en mode headless.
    Retourne le chemin vers le fichier PDF généré.
    """
    output_dir = os.path.dirname(file_path)
    cmd = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, file_path]
    subprocess.run(cmd, check=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    pdf_file = os.path.join(output_dir, base_name + ".pdf")
    return pdf_file

def get_pp_page_count(pp_file):
    """
    Retourne le nombre de pages du document PP.
    Pour DOC/DOCX, le document est converti en PDF.
    """
    if pp_file is None:
        return 0
    file_path = pp_file.name
    ext = file_path.lower().split('.')[-1]
    if ext in ["doc", "docx"]:
        try:
            file_path = convert_doc_to_pdf(file_path)
        except Exception:
            return 0
    try:
        doc = fitz.open(file_path)
        count = doc.page_count
        doc.close()
        return count
    except Exception:
        return 0

def update_slider(pp_file):
    """
    Met à jour le slider de page en fonction du nombre de pages du PP.
    Si le document contient 1 page ou moins, le slider est désactivé en utilisant 'interactive=False'.
    """
    count = get_pp_page_count(pp_file)
    if count <= 1:
        return gr.update(maximum=1, value=0, interactive=False)
    else:
        return gr.update(maximum=count - 1, value=0, interactive=True)

def render_pp_page(page_number, pp_file):
    """
    Rend la page spécifiée du PP (PDF ou DOC/DOCX converti en PDF) en image PNG et renvoie un HTML.
    """
    if pp_file is None:
        return "Aucun document PP chargé."
    file_path = pp_file.name
    ext = file_path.lower().split('.')[-1]
    if ext in ["doc", "docx"]:
        try:
            file_path = convert_doc_to_pdf(file_path)
        except Exception as e:
            return f"Erreur de conversion DOC->PDF : {str(e)}"
    try:
        doc = fitz.open(file_path)
        if page_number < 0 or page_number >= doc.page_count:
            return "Page introuvable."
        page = doc.load_page(page_number)
        pix = page.get_pixmap(dpi=150)  # Rendu à 150 dpi pour un format A4
        img_data = pix.tobytes("png")
        encoded_img = base64.b64encode(img_data).decode('utf-8')
        html = f"<img src='data:image/png;base64,{encoded_img}' style='max-width:100%; height:auto;'/>"
        doc.close()
        return html
    except Exception as e:
        return f"Erreur lors du rendu de la page: {str(e)}"
def extract_relevant_snippet(text, question, max_chars=2000):
    """
    Extrait un snippet pertinent du texte en sélectionnant les phrases
    contenant au moins un mot-clé issu de la question.
    Si aucune phrase ne correspond, tronque simplement le texte.
    """
    # Découper le texte en phrases
    sentences = re.split(r'(?<=[.!?])\s+', text)
    # Liste de mots à ignorer (stop words simples)
    stop_words = set(["le", "la", "les", "de", "des", "un", "une", "et", "est", "à", "du", "en", "pour", "que", "qui", "ce", "dans", "ne", "pas"])
    # Extraire les mots de la question (sans ponctuation) et filtrer les mots courts et les stop words
    keywords = [word.lower() for word in re.findall(r'\w+', question) if len(word) > 3 and word.lower() not in stop_words]
    # Filtrer les phrases qui contiennent au moins un mot-clé
    relevant_sentences = [s for s in sentences if any(kw in s.lower() for kw in keywords)]
    if relevant_sentences:
        snippet = " ".join(relevant_sentences)
    else:
        snippet = text
    # Tronquer si le snippet est trop long
    if len(snippet) > max_chars:
        snippet = snippet[:max_chars] + "\n... (extrait tronqué)"
    return snippet


def answer_question_from_pp(question: str, pp_file) -> str:
    """
    Génère une réponse basée uniquement sur le contenu du PP (PDF ou DOC/DOCX).
    Pour éviter que le modèle ne renvoie l'intégralité du document, nous extrayons
    un extrait pertinent du texte en utilisant des expressions régulières pour sélectionner
    les phrases contenant les mots-clés de la question.
    Le prompt est formulé pour inciter le modèle à fournir une réponse synthétique.
    Retourne une chaîne vide en cas d'échec pour permettre le fallback.
    """
    if pp_file is None:
        return ""
    file_path = pp_file.name
    ext = file_path.lower().split('.')[-1]
    if ext == "pdf":
        pages = extract_pages_from_pdf(file_path)
        pp_text = "\n".join(pages)
    elif ext in ["doc", "docx"]:
        try:
            pdf_file = convert_doc_to_pdf(file_path)
            pages = extract_pages_from_pdf(pdf_file)
            pp_text = "\n".join(pages)
        except Exception as e:
            return ""
    else:
        return ""
    if not pp_text.strip():
        return ""
    # Extraire un snippet pertinent du document en utilisant les mots-clés de la question
    snippet = extract_relevant_snippet(pp_text, question, max_chars=2000)
    prompt = (
        "Tu es un assistant expert. En te basant sur l'extrait pertinent ci-dessous, "
        "fournis une réponse synthétique, concise et précise à la question posée. "
        "Ne reproduis pas l'extrait complet, mais utilise uniquement les informations essentielles.\n\n"
        "Extrait pertinent :\n" +
        snippet + "\n\n" +
        "Question : " + question + "\n\n" +
        "Réponse :"
    )
    response = KH_CHAT_LLM.invoke(prompt)
    return response.content


def answer_question_pp_or_db(question: str, pp_file) -> str:
    """
    Tente de générer une réponse via le PP.
    Si la réponse obtenue est trop courte ou vide, effectue un fallback vers la base via answer_question_with_context.
    """
    answer_pp = answer_question_from_pp(question, pp_file)
    if len(answer_pp.strip()) < 20:
        fallback_answer = answer_question_with_context(question)
        if "Aucun contexte trouvé" in fallback_answer:
            return f"(Pas trouvé dans PP ni DB)\n\n{answer_pp.strip()}"
        else:
            return f"(Réponse depuis la DB)\n\n{fallback_answer}"
    else:
        return f"(Réponse depuis le PP)\n\n{answer_pp}"

def generer_reponses_multiples(questions_text, pp_file):
    """
    Pour chaque question extraite, génère une réponse en utilisant le PP chargé.
    Affiche la question en gras suivie de la réponse générée.
    """
    if not questions_text.strip():
        return "Aucune question à traiter."
    lines = questions_text.splitlines()
    output = []
    for q in lines:
        q_str = q.strip()
        if not q_str:
            continue
        answer = answer_question_pp_or_db(q_str, pp_file)
        output.append(f"**Question :** {q_str}\n\n**Réponse :** {answer}\n\n---\n")
    return "\n".join(output)

##############################################
# UI PRINCIPALE
##############################################
def main_ui():
    with gr.Blocks() as demo:
        gr.Markdown("# GroupeSOS - IA Financement")
        with gr.Tabs():
            # Onglet Accueil : Fusion AAP Assistance et Chat Assistance
            with gr.Tab("Accueil"):
                with gr.Row():
                    # Colonne de gauche : AAP Assistance
                    with gr.Column(scale=1):
                        gr.Markdown("## AAP Assistance")
                        aap_file = gr.File(label="AAP (docx/pdf)", file_types=['.docx', '.pdf'])
                        questions_output = gr.Textbox(
                            label="Questions extraites",
                            lines=10,
                            placeholder="Les questions de l'AAP apparaîtront ici..."
                        )
                        def on_aap_uploaded(file):
                            return extract_questions_from_aap(file)
                        aap_file.change(fn=on_aap_uploaded, inputs=aap_file, outputs=questions_output)
                        
                        pp_file = gr.File(label="Projet (doc/docx/pdf)", file_types=['.doc', '.docx', '.pdf'])
                        pp_file_state = gr.State(None)
                        pp_feedback = gr.Textbox(label="Statut du PP", lines=1, interactive=False)
                        def on_pp_uploaded(file):
                            if file is None:
                                return None, "Aucun document PP fourni."
                            return file, f"Document PP chargé : {file.name}"
                        pp_file.upload(fn=on_pp_uploaded, inputs=pp_file, outputs=[pp_file_state, pp_feedback])
                        
                        reponses_markdown = gr.Markdown(value="*(Les réponses apparaîtront ici...)*")
                        generer_btn = gr.Button("Générer les réponses (toutes les questions)")
                        generer_btn.click(fn=generer_reponses_multiples,
                                          inputs=[questions_output, pp_file_state],
                                          outputs=reponses_markdown)
                    
                    # Colonne de droite : Chat Assistance et affichage paginé du PP
                    with gr.Column(scale=1):
                        gr.Markdown("## Chat Assistance (PP + Fallback DB)")
                        
                        # Crée le slider pour choisir la page du PP et le composant HTML pour l'affichage
                        pp_page_slider = gr.Slider(minimum=0, maximum=1, value=0, step=1, label="Page du PP")
                        pp_viewer = gr.HTML(label="Aperçu du document PP (page)")
                        pp_page_slider.change(fn=render_pp_page,
                                              inputs=[pp_page_slider, pp_file_state],
                                              outputs=pp_viewer)
                        
                        chatbot = gr.Chatbot(label="Assistant Financement")
                        user_input = gr.Textbox(label="Question", placeholder="Posez votre question ici...")
                        send_btn = gr.Button("Envoyer")
                        conversation_state = gr.State([])
                        def custom_chat_interaction(message, history, pp_file):
                            new_history = history + [(message, "...")]
                            answer = answer_question_pp_or_db(message, pp_file)
                            new_history[-1] = (message, answer)
                            return new_history, new_history
                        send_btn.click(fn=custom_chat_interaction,
                                       inputs=[user_input, conversation_state, pp_file_state],
                                       outputs=[chatbot, conversation_state])
            # Onglet Ingestion : Gestion des documents
            with gr.Tab("Ingestion"):
                gr.Markdown("## Ingestion de documents")
                ingest_btn = gr.Button("Lancer l'ingestion")
                ingest_output = gr.Textbox(label="Logs d'ingestion", lines=8)
                ingest_btn.click(fn=run_ingestion, outputs=ingest_output)
                
                gr.Markdown("### Liste des documents en base")
                refresh_btn = gr.Button("Rafraîchir la liste")
                doc_table = gr.DataFrame(headers=["doc_id", "source", "preview"], interactive=False)
                refresh_btn.click(fn=load_documents, outputs=doc_table)
                
                reset_btn = gr.Button("Réinitialiser la base")
                reset_output = gr.Textbox(label="Logs de reset", lines=2)
                reset_btn.click(fn=reset_data, outputs=reset_output)
        
        # En dehors des onglets, on met à jour le slider en fonction de pp_file_state
        pp_file_state.change(fn=update_slider, inputs=pp_file_state, outputs=pp_page_slider)
        
    return demo

if __name__ == "__main__":
    main_ui().launch(server_name="0.0.0.0", server_port=7860)

