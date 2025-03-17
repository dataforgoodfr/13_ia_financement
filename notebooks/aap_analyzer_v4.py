import requests
import json
from pathlib import Path
import os
from typing import Dict, List, Any, Set, Tuple
from docx import Document
import PyPDF2
import pandas as pd
from collections import Counter, defaultdict
import openpyxl
import logging
from difflib import SequenceMatcher
import numpy as np
from datetime import datetime
import time
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

OLLAMA_HOST = "http://localhost:11434/api/generate"

class AAPAnalyzer:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.setup_logging()
        self.theme_patterns = {
            "introduction": ["introduction", "contexte", "présentation", "préambule", "avant-propos"],
            "objectifs": ["objectif", "but", "finalité", "mission", "ambition", "vision"],
            "methodologie": ["méthode", "méthodologie", "approche", "démarche", "processus", "protocole"],
            "budget": ["budget", "financement", "coût", "investissement", "dépense", "ressource financière"],
            "evaluation": ["évaluation", "suivi", "indicateur", "mesure", "performance", "critère"],
            "partenariats": ["partenaire", "collaboration", "coopération", "alliance", "réseau", "acteur"],
            "resultats": ["résultat", "impact", "effet", "retombée", "bénéfice", "conséquence"],
            "planning": ["planning", "calendrier", "échéancier", "temporalité", "délai", "durée"],
            "innovation": ["innovation", "nouveauté", "créativité", "originalité", "invention"],
            "durabilite": ["durabilité", "environnement", "écologie", "développement durable"],
            "social": ["social", "sociétal", "inclusion", "accessibilité", "solidarité"],
            "technique": ["technique", "technologie", "outil", "équipement", "infrastructure"],
            "gouvernance": ["gouvernance", "pilotage", "gestion", "organisation", "coordination"],
            "communication": ["communication", "diffusion", "valorisation", "promotion"]
        }
        
        self.reference_sections = {
            "resume": ["résumé", "synthèse", "abstract"],
            "introduction": ["introduction", "contexte", "présentation"],
            "objectifs": ["objectifs", "buts", "finalités"],
            "description_projet": ["description", "présentation détaillée", "contenu"],
            "methodologie": ["méthodologie", "méthode", "approche"],
            "moyens": ["moyens", "ressources", "équipements"],
            "budget": ["budget", "financement", "coûts"],
            "planning": ["planning", "calendrier", "échéancier"],
            "equipe": ["équipe", "personnel", "ressources humaines"],
            "partenaires": ["partenaires", "partenariats", "collaborations"],
            "innovation": ["innovation", "originalité", "nouveauté"],
            "impact": ["impact", "retombées", "effets"],
            "evaluation": ["évaluation", "suivi", "indicateurs"],
            "perennisation": ["pérennisation", "durabilité", "suite"],
            "communication": ["communication", "diffusion", "valorisation"],
            "annexes": ["annexes", "pièces jointes", "documents complémentaires"]
        }

        self.section_requirements = {
            "resume": ["synthèse claire", "objectifs principaux", "résultats attendus"],
            "introduction": ["contexte", "problématique", "enjeux"],
            "objectifs": ["objectifs généraux", "objectifs spécifiques", "résultats attendus"],
            "description_projet": ["description détaillée", "public cible", "territoire"],
            "methodologie": ["approche", "étapes", "outils"],
            "moyens": ["moyens humains", "moyens matériels", "moyens financiers"],
            "budget": ["plan de financement", "coûts détaillés", "sources de financement"],
            "planning": ["calendrier détaillé", "jalons", "livrables"],
            "equipe": ["compétences", "rôles", "responsabilités"],
            "partenaires": ["rôles des partenaires", "engagements", "contributions"],
            "innovation": ["caractère innovant", "plus-value", "originalité"],
            "impact": ["impact social", "impact environnemental", "impact économique"],
            "evaluation": ["indicateurs", "méthodes d'évaluation", "outils de suivi"],
            "perennisation": ["stratégie long terme", "modèle économique", "perspectives"],
            "communication": ["plan de communication", "outils", "cibles"],
            "annexes": ["documents administratifs", "lettres de soutien", "études"]
        }

    def setup_logging(self):
        """Configuration des logs avec gestion de l'encodage"""
        if sys.platform == 'win32':
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('aap_analyzer.log', encoding='utf-8'),
                    logging.StreamHandler(sys.stdout)
                ]
            )
        else:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler('aap_analyzer.log'),
                    logging.StreamHandler()
                ]
            )
        self.logger = logging.getLogger(__name__)

    def ask_mixtral(self, prompt: str) -> str:
        """Envoie une requête à Mixtral pour analyse et compréhension du texte"""
        try:
            response = requests.post(
                OLLAMA_HOST,
                json={
                    "model": "mixtral",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3
                },
                timeout=180
            )
            
            if response.status_code == 200:
                return response.json().get("response", "Erreur: pas de réponse")
            else:
                self.logger.error(f"Erreur Mixtral - Status code: {response.status_code}")
                return "Erreur: réponse invalide"
        except Exception as e:
            self.logger.error(f"Erreur connexion Mixtral: {str(e)}")
            return "Erreur: problème de connexion"

    def extract_text_by_sections(self, file_path: str) -> Dict[str, Any]:
        """Extrait le texte et la structure d'un document"""
        try:
            file_path_lower = file_path.lower()
            if file_path_lower.endswith('.docx'):
                return self._extract_from_docx(file_path)
            elif file_path_lower.endswith('.pdf'):
                return self._extract_from_pdf(file_path)
            elif file_path_lower.endswith(('.xlsx', '.xls')):
                return self._extract_from_excel(file_path)
            else:
                self.logger.warning(f"Format non supporté: {file_path}")
                return {}
        except Exception as e:
            self.logger.error(f"Erreur extraction {file_path}: {str(e)}")
            return {}

    def _extract_from_docx(self, file_path: str) -> Dict[str, Any]:
        """Extraction améliorée des documents Word avec structure"""
        sections = {}
        try:
            doc = Document(file_path)
            current_section = "Introduction"
            sections[current_section] = []
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                
                if para.style and "Heading" in para.style.name:
                    current_section = text
                    sections[current_section] = []
                else:
                    sections[current_section].append(text)
            
            return {sec: " ".join(content) for sec, content in sections.items() if content}
            
        except Exception as e:
            self.logger.error(f"Erreur Word {file_path}: {str(e)}")
            return {}

    def analyze_themes(self, text: str) -> Dict[str, float]:
        """Analyse les thèmes présents dans un texte"""
        themes_scores = {}
        text_lower = text.lower()
        
        for theme, patterns in self.theme_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in text_lower:
                    score += text_lower.count(pattern)
            if score > 0:
                themes_scores[theme] = score
                
        # Normalisation des scores
        if themes_scores:
            max_score = max(themes_scores.values())
            themes_scores = {k: v/max_score for k, v in themes_scores.items()}
            
        return themes_scores

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes"""
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except:
            return 0.0

    def analyze_aap_files(self) -> Dict[str, Any]:
        """Analyse complète des fichiers AAP"""
        # Vérifier la connexion à Mixtral
        try:
            response = requests.get("http://localhost:11434/api/version")
            if response.status_code != 200:
                self.logger.error("Mixtral n'est pas accessible")
                return {}
        except:
            self.logger.error("Impossible de se connecter à Mixtral")
            return {}

        # Recherche de tous les AAPs dans le dossier data
        aap_files = []
        for path in Path(self.data_dir).rglob("*"):
            if path.is_file() and "AAP" in path.name.upper() and path.suffix.lower() in ['.docx', '.pdf', '.xlsx', '.xls']:
                aap_files.append(path)

        if not aap_files:
            self.logger.error(f"Aucun fichier AAP trouvé dans {self.data_dir}")
            return {}

        self.logger.info(f"Analyse de {len(aap_files)} fichiers AAP")

        # Analyse des documents
        analyses = {}
        processing_times = {}
        similarities = defaultdict(dict)
        total_start_time = time.time()

        # Analyse de chaque AAP
        for aap_path in aap_files:
            self.logger.info(f"Analyse de {aap_path.name}")
            start_time = time.time()

            try:
                # Extraction et analyse des sections
                aap_sections = self.extract_text_by_sections(str(aap_path))
                if not aap_sections:
                    continue

                # Analyse des thèmes par section
                section_themes = {}
                section_similarities = {}
                
                for section, content in aap_sections.items():
                    # Analyse thématique
                    section_themes[section] = self.analyze_themes(content)

                # Construction du prompt pour l'analyse détaillée
                prompt = f"""
                Analyse détaillée du document {aap_path.name}.
                
                Sections trouvées : {list(aap_sections.keys())}
                
                Pour chaque thématique, évalue :
                1. La couverture du contenu (✅ complète, ⚠️ partielle, ❌ absente)
                2. La pertinence du contenu
                3. Les éléments manquants ou à améliorer
                
                Thématiques à analyser :
                {list(self.theme_patterns.keys())}
                
                Format de réponse souhaité :
                - ✅ [Thème] : Bien couvert, avec [détails]
                - ⚠️ [Thème] : Partiellement couvert, manque [éléments]
                - ❌ [Thème] : Absent, devrait inclure [suggestions]
                """

                # Analyse avec Mixtral
                analysis_result = self.ask_mixtral(prompt)

                # Calcul du temps et enregistrement des résultats
                processing_time = time.time() - start_time
                
                analyses[aap_path.name] = {
                    "file_path": str(aap_path),
                    "sections": aap_sections,
                    "themes": section_themes,
                    "analysis": analysis_result,
                    "processing_time": processing_time
                }
                
                processing_times[aap_path.name] = processing_time

            except Exception as e:
                self.logger.error(f"Erreur analyse {aap_path.name}: {str(e)}")
                continue

        total_time = time.time() - total_start_time

        # Génération du rapport
        report = self.generate_report(analyses, processing_times, total_time)

        return {
            "analyses": analyses,
            "processing_times": processing_times,
            "total_time": total_time,
            "report": report
        }

    def analyze_common_themes(self, analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """Analyse les thèmes communs et uniques entre les AAP"""
        # Initialisation des dictionnaires pour stocker les thèmes par document
        themes_by_doc = {}
        all_themes = set()
        
        # Collecte des thèmes pour chaque document
        for doc_name, doc_data in analyses.items():
            doc_themes = set()
            for section_themes in doc_data["themes"].values():
                doc_themes.update(section_themes.keys())
            themes_by_doc[doc_name] = doc_themes
            all_themes.update(doc_themes)
        
        # Identification des thèmes communs à tous les documents
        common_themes = set.intersection(*themes_by_doc.values()) if themes_by_doc else set()
        
        # Identification des thèmes uniques par document
        unique_themes = {}
        for doc_name, themes in themes_by_doc.items():
            other_docs_themes = set.union(*[t for n, t in themes_by_doc.items() if n != doc_name]) if len(themes_by_doc) > 1 else set()
            unique_themes[doc_name] = themes - other_docs_themes
        
        return {
            "common_themes": list(common_themes),
            "unique_themes": {k: list(v) for k, v in unique_themes.items()},
            "all_themes": list(all_themes)
        }

    def analyze_section_completeness(self, section_content: str, section_name: str) -> Dict[str, Any]:
        """Analyse la complétude d'une section par rapport aux exigences"""
        requirements = self.section_requirements.get(section_name, [])
        completeness = {}
        
        for req in requirements:
            # Calcul du score de présence pour chaque exigence
            score = sum(1 for word in req.split() if word.lower() in section_content.lower())
            completeness[req] = {
                "present": score > 0,
                "score": score / len(req.split())  # Score normalisé
            }
            
        return {
            "requirements_met": sum(1 for req in completeness.values() if req["present"]),
            "total_requirements": len(requirements),
            "details": completeness,
            "completion_rate": sum(req["score"] for req in completeness.values()) / len(requirements) if requirements else 0
        }

    def analyze_aap_statistics(self, analyses: Dict[str, Dict]) -> Dict[str, Any]:
        """Génère des statistiques détaillées pour chaque AAP"""
        stats = {}
        
        for doc_name, doc_data in analyses.items():
            doc_stats = {
                "section_coverage": {},
                "theme_coverage": {},
                "global_stats": {
                    "total_sections": len(doc_data["sections"]),
                    "total_themes": len(doc_data["themes"]),
                    "average_completion": 0
                }
            }
            
            # Analyse de la couverture des sections
            total_completion = 0
            for section_name, content in doc_data["sections"].items():
                completeness = self.analyze_section_completeness(content, section_name)
                doc_stats["section_coverage"][section_name] = completeness
                total_completion += completeness["completion_rate"]
            
            # Calcul des moyennes
            doc_stats["global_stats"]["average_completion"] = (
                total_completion / len(doc_data["sections"]) if doc_data["sections"] else 0
            )
            
            # Analyse des thèmes
            for section, themes in doc_data["themes"].items():
                for theme, score in themes.items():
                    if theme not in doc_stats["theme_coverage"]:
                        doc_stats["theme_coverage"][theme] = {
                            "total_score": 0,
                            "occurrences": 0
                        }
                    doc_stats["theme_coverage"][theme]["total_score"] += score
                    doc_stats["theme_coverage"][theme]["occurrences"] += 1
            
            # Calcul des scores moyens des thèmes
            for theme_stats in doc_stats["theme_coverage"].values():
                theme_stats["average_score"] = (
                    theme_stats["total_score"] / theme_stats["occurrences"]
                    if theme_stats["occurrences"] > 0 else 0
                )
            
            stats[doc_name] = doc_stats
        
        return stats

    def generate_report(self, analyses: Dict[str, Dict], processing_times: Dict[str, float], total_time: float) -> str:
        """Génération d'un rapport détaillé"""
        report = []
        report.append("📊 ANALYSE DES AAP")
        report.append(f"Date de l'analyse : {datetime.now().isoformat()}")
        report.append(f"Nombre de documents analysés : {len(analyses)}")
        
        # Analyse comparative des thèmes
        theme_comparison = self.analyze_common_themes(analyses)
        
        # Statistiques détaillées
        stats = self.analyze_aap_statistics(analyses)
        
        report.append("\n📈 STATISTIQUES GLOBALES")
        for doc_name, doc_stats in stats.items():
            report.append(f"\n=== {doc_name} ===")
            report.append(f"Taux de complétion moyen : {doc_stats['global_stats']['average_completion']*100:.1f}%")
            report.append(f"Nombre de sections : {doc_stats['global_stats']['total_sections']}")
            
            report.append("\nCouverture des sections :")
            for section, coverage in doc_stats["section_coverage"].items():
                completion = coverage["completion_rate"] * 100
                requirements_met = coverage["requirements_met"]
                total_req = coverage["total_requirements"]
                
                if completion >= 75:
                    status = "✅"
                elif completion >= 40:
                    status = "⚠️"
                else:
                    status = "❌"
                
                report.append(f"{status} {section}: {completion:.1f}% ({requirements_met}/{total_req} critères)")
                
                # Détails des exigences non satisfaites
                missing_reqs = [
                    req for req, details in coverage["details"].items()
                    if not details["present"]
                ]
                if missing_reqs:
                    report.append("   Éléments manquants :")
                    for req in missing_reqs:
                        report.append(f"   - {req}")
            
            report.append("\nCouverture thématique :")
            for theme, coverage in doc_stats["theme_coverage"].items():
                score = coverage["average_score"] * 100
                if score >= 75:
                    status = "✅"
                elif score >= 40:
                    status = "⚠️"
                else:
                    status = "❌"
                report.append(f"{status} {theme}: {score:.1f}%")
        
        report.append("\n🔄 ANALYSE COMPARATIVE DES THÈMES")
        report.append("\n📌 Thèmes communs à tous les AAP :")
        if theme_comparison["common_themes"]:
            for theme in theme_comparison["common_themes"]:
                report.append(f"• {theme}")
        else:
            report.append("Aucun thème commun trouvé")
            
        report.append("\n🎯 Thèmes uniques par AAP :")
        for doc_name, unique in theme_comparison["unique_themes"].items():
            report.append(f"\n{doc_name}:")
            if unique:
                for theme in unique:
                    report.append(f"• {theme}")
            else:
                report.append("Aucun thème unique")
        
        # Temps de traitement
        report.append("\n⏱️ TEMPS DE TRAITEMENT")
        report.append(f"Temps total : {total_time:.2f} secondes")
        report.append("\nTemps par document :")
        for doc, time_spent in processing_times.items():
            report.append(f"• {doc}: {time_spent:.2f} secondes")
        
        return "\n".join(report)

def check_mixtral():
    """Vérifie si Mixtral est accessible"""
    try:
        response = requests.get("http://localhost:11434/api/version")
        return response.status_code == 200
    except:
        return False

def main():
    print("🔄 Vérification de Mixtral...")
    if not check_mixtral():
        print("❌ Erreur: Mixtral n'est pas accessible. Assurez-vous qu'il est lancé sur le port 11434")
        return

    print("🔍 Initialisation de l'analyse...")
    analyzer = AAPAnalyzer("data")
    
    try:
        results = analyzer.analyze_aap_files()
        
        if results:
            print("\n=== Rapport d'Analyse ===")
            print(results["report"])
            
            # Sauvegarde des résultats
            with open("analyse_aap_complete.json", "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print("\n💾 Résultats détaillés sauvegardés dans analyse_aap_complete.json")
        else:
            print("\n❌ Aucun résultat d'analyse disponible")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {str(e)}")

if __name__ == "__main__":
    main() 