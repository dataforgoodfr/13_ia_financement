Organisation Générale et Structure des Fichiers
Votre application est découpée en plusieurs modules :

sos_pipeline.py : Gestion de l’ingestion des documents, extraction de texte et questions.

sos_flowsettings.py : Configuration des stores et du LLM (Falcon vs. OpenAI).

sos_chat_falcon.py : Chargement et création du pipeline Falcon pour la génération de texte.

sos_doc_loader.py : Interface Gradio minimale pour visualiser les documents ingérés.

sos_ui_chat_context.py : Interface pour le chat contextuel et consultation d’un PDF.

sos_app.py : Interface principale unifiée qui combine les différents onglets (AAP, Chat, Ingestion).

