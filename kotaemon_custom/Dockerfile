FROM ghcr.io/cinnamon/kotaemon:main-full

# Désinstallation de paquets potentiellement incompatibles
RUN pip uninstall -y pydantic langchain langchain-core langchain-community accelerate llama-index || true
RUN pip uninstall -y pydantic-settings langchain-openai langchain-embeddings langchain-embeddings-openai langchain-embeddings-huggingface langchain-embeddings-huggingface-transformers langchain-embeddings-huggingface-transformers-accelerate langchain-embeddings-huggingface-transformers-torch || true

# Mise à jour de pip et installation des dépendances
RUN pip install --upgrade pip
RUN pip install --no-cache-dir \
    "pydantic==2.6.4" \
    "pydantic-settings>=2.0.3" \
    "pydantic-core>=2.16.3" \
    "pydantic[email]>=2.6.4" \
    "langchain" \
    "langchain-core" \
    "langchain-cohere" \
    PyPDF2 \
    python-docx \
    pandas
RUN pip install accelerate>=0.26.0

# Copie des scripts dans le conteneur
COPY sos_app.py /app/sos_app.py
COPY sos_pipeline.py /app/sos_pipeline.py
COPY sos_flowsettings.py /app/sos_flowsettings.py
COPY sos_chat_falcon.py /app/sos_chat_falcon.py
COPY sos_doc_loader.py /app/sos_doc_loader.py
COPY sos_ui_chat_context.py /app/sos_ui_chat_context.py

# Désactivation de l'entrypoint par défaut
ENTRYPOINT []

CMD ["python", "sos_app.py"]