import requests
import json
from pathlib import Path
import os
from typing import Dict, List, Any
from docx import Document
import fitz  # PyMuPDF
import logging
from datetime import datetime
import time
import sys
import re

# Constants
OLLAMA_HOST = "http://localhost:11434/api/generate"
MAX_RETRIES = 2
REQUEST_TIMEOUT = 300
CHUNK_SIZE = 300
PAUSE_BETWEEN_CHUNKS = 2

class AAPAnalyzer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.logger = self.setup_logging()
        self.output_dir = "resultats"
        os.makedirs(self.output_dir, exist_ok=True)

    def setup_logging(self) -> logging.Logger:
        """Configure et retourne le logger"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"aap_analyzer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        logger = logging.getLogger('AAPAnalyzer')
        logger.setLevel(logging.INFO)
        logger.handlers = []
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        console_handler = logging.StreamHandler(sys.stdout)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    def ask_mixtral(self, prompt: str, retry_count: int = 0) -> str:
        """Version simplifiée qui retourne directement le texte d'analyse"""
        if retry_count >= MAX_RETRIES:
            return "Analyse non disponible (nombre maximum de tentatives atteint)"

        try:
            self.logger.info(f"Tentative {retry_count + 1}/{MAX_RETRIES}")
            
            analysis_prompt = f"""Analyse ce texte et fournis une synthèse claire avec les points suivants :

            BESOINS PRINCIPAUX :
            - Liste des besoins identifiés

            ATTENTES EXPRIMÉES :
            - Liste des attentes principales

            QUESTIONS IMPORTANTES :
            - Liste des questions clés

            AXES MAJEURS :
            - Points principaux du document

            CONTEXTE :
            - Éléments de contexte importants

            Texte à analyser : {prompt}"""

            response = requests.post(
                OLLAMA_HOST,
                json={
                    "model": "mixtral",
                    "prompt": analysis_prompt,
                    "stream": False,
                    "temperature": 0.1,
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                response_json = response.json()
                return response_json.get("response", "")
            
            time.sleep(PAUSE_BETWEEN_CHUNKS)
            return self.ask_mixtral(prompt, retry_count + 1)
            
        except Exception as e:
            self.logger.error(f"Erreur: {str(e)}")
            time.sleep(PAUSE_BETWEEN_CHUNKS)
            return self.ask_mixtral(prompt, retry_count + 1)

    def extract_text(self, file_path: str) -> str:
        """Extraction de texte des documents"""
        try:
            if file_path.lower().endswith('.docx'):
                doc = Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            elif file_path.lower().endswith('.pdf'):
                text = []
                with fitz.open(file_path) as doc:
                    for page in doc:
                        text.append(page.get_text())
                return "\n".join(text)
            else:
                self.logger.warning(f"Format non supporté: {file_path}")
                return ""
        except Exception as e:
            self.logger.error(f"Erreur extraction texte: {str(e)}")
            return ""

    def split_text(self, text: str, max_size: int = CHUNK_SIZE) -> List[str]:
        """Découpage du texte en sections"""
        if not text:
            return []
        
        # Découpage en paragraphes puis en chunks de taille raisonnable
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            if current_size + para_size > max_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    def extract_context_around_keywords(self, text: str) -> Dict[str, List[str]]:
        """Extrait les phrases contenant les mots-clés et leur contexte"""
        keywords = {
            'besoins': ['besoin', 'nécessite', 'requiert', 'demande'],
            'attentes': ['attente', 'attend', 'souhaite', 'désire', 'exige'],
            'questions': ['question', '?', 'comment', 'pourquoi', 'quand', 'où', 'qui', 'quel']
        }
        
        # Découper le texte en phrases
        sentences = re.split(r'(?<=[.!?])\s+', text)
        context = {k: [] for k in keywords.keys()}
        
        for i, sentence in enumerate(sentences):
            for category, words in keywords.items():
                if any(word.lower() in sentence.lower() for word in words):
                    # Récupérer la phrase précédente si elle existe
                    previous = sentences[i-1] if i > 0 else ""
                    # Récupérer la phrase suivante si elle existe
                    next_sentence = sentences[i+1] if i < len(sentences)-1 else ""
                    
                    context_entry = {
                        'phrase': sentence.strip(),
                        'contexte_avant': previous.strip(),
                        'contexte_apres': next_sentence.strip()
                    }
                    context[category].append(context_entry)
        
        return context
    def detect_theme(self, text: str) -> str:
        """Détecte le thème principal du document"""
        try:
            theme_prompt = f"""Analyse ce texte et identifie son thème principal en une phrase courte.
            Ne garde que l'essentiel, maximum 10 mots.
            
            Texte à analyser : {text[:1000]}"""  # On utilise le début du document

            response = requests.post(
                OLLAMA_HOST,
                json={
                    "model": "mixtral",
                    "prompt": theme_prompt,
                    "stream": False,
                    "temperature": 0.1,
                },
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                theme = response.json().get("response", "").strip()
                return theme
            
            return "Thème non détecté"
            
        except Exception as e:
            self.logger.error(f"Erreur détection thème: {str(e)}")
            return "Erreur détection thème"
    def analyze_document(self, file_path: Path) -> str:
        """Analyse d'un document avec sortie texte et contexte"""
        try:
            self.logger.info(f"\n=== Analyse de {file_path.name} ===")
            
            # Extraction du texte
            text = self.extract_text(str(file_path))
            if not text:
                return "Document vide ou non extractible"

            # Détection du thème
            theme = self.detect_theme(text)
            self.logger.info(f"THÈME DÉTECTÉ : {theme}")

            # Extraction du contexte autour des mots-clés
            context_data = self.extract_context_around_keywords(text)

            # Découpage en sections
            chunks = self.split_text(text)
            self.logger.info(f"Document découpé en {len(chunks)} sections")
            
            analyses = []
            
            for i, chunk in enumerate(chunks, 1):
                self.logger.info(f"Analyse section {i}/{len(chunks)}")
                analysis = self.ask_mixtral(chunk)
                if analysis:
                    analyses.append(analysis)
                    # Log les 3 premières analyses
                    if i <= 3:
                        self.logger.info(f"\nANALYSE SECTION {i}:\n{'-' * 20}\n{analysis}\n")
                time.sleep(PAUSE_BETWEEN_CHUNKS)

            # Compilation de l'analyse complète avec le contexte
            full_analysis = f"""
{"=" * 50}
ANALYSE DE : {file_path.name}
{"=" * 50}

THÈME PRINCIPAL : {theme}
{"-" * 50}

"""
            # Ajouter les analyses par section
            for i, analysis in enumerate(analyses, 1):
                full_analysis += f"\nSECTION {i} :\n{'-' * 20}\n{analysis}\n\n"

            # Ajouter les extraits avec contexte
            full_analysis += f"\n{'=' * 50}\nEXTRAITS AVEC CONTEXTE\n{'=' * 50}\n\n"
            
            for category, entries in context_data.items():
                if entries:
                    full_analysis += f"\n{category.upper()} IDENTIFIÉS :\n{'-' * 20}\n"
                    for entry in entries:
                        full_analysis += f"\nContexte avant : {entry['contexte_avant']}\n"
                        full_analysis += f"PHRASE : {entry['phrase']}\n"
                        full_analysis += f"Contexte après : {entry['contexte_apres']}\n"
                        full_analysis += f"{'-' * 40}\n"

            # Sauvegarde dans un fichier texte
            output_file = os.path.join(self.output_dir, f"analyse_{file_path.stem}.txt")
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_analysis)

            return full_analysis

        except Exception as e:
            self.logger.error(f"Erreur analyse document: {str(e)}")
            return f"Erreur lors de l'analyse: {str(e)}"

def main():
    try:
        print("\n🔍 Initialisation de l'analyse des AAP...")
        
        # Vérification et création des répertoires
        data_dir = Path("../data").resolve()
        if not data_dir.exists():
            print(f"❌ Répertoire data non trouvé: {data_dir}")
            return
            
        analyzer = AAPAnalyzer(str(data_dir))
        
        # Test de connexion Mixtral
        print("🔄 Test de connexion à Mixtral...")
        test_response = analyzer.ask_mixtral("Test de connexion")
        if not test_response:
            print("❌ Impossible de se connecter à Mixtral")
            return
        print("✅ Connexion à Mixtral établie")
        
        # Recherche des fichiers AAP
        print("\n🔍 Recherche des fichiers AAP...")
        aap_files = list(data_dir.rglob("*.[pd][do][fc]*"))
        aap_files = [f for f in aap_files if f.suffix.lower() in ('.pdf', '.docx')]
        
        if not aap_files:
            print("❌ Aucun fichier AAP trouvé")
            return
            
        print(f"📁 {len(aap_files)} fichiers AAP trouvés")
        
        # Analyse des documents
        for i, file_path in enumerate(aap_files, 1):
            print(f"\n📄 [{i}/{len(aap_files)}] Analyse de {file_path.name}")
            analysis = analyzer.analyze_document(file_path)
            
            # Affichage d'un résumé
            print("\n📝 Résumé de l'analyse :")
            print("-" * 50)
            theme_match = re.search(r"THÈME PRINCIPAL : (.+?)\n", analysis)
            if theme_match:
                print(f"🏷️ Thème : {theme_match.group(1)}")
            print("-" * 50)
            # Affiche les 500 premiers caractères avec "..." si le texte est plus long
            print(analysis[:500] + "..." if len(analysis) > 500 else analysis)
            print("-" * 50)
            print(f"💾 Analyse complète sauvegardée dans resultats/analyse_{file_path.stem}.txt")
            
        print("\n✅ Analyse terminée !")
        print(f"📊 {len(aap_files)} documents analysés")
        print("💾 Les résultats complets sont disponibles dans le dossier 'resultats'")
            
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")

if __name__ == "__main__":
    main()