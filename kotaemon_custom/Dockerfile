FROM ghcr.io/cinnamon/kotaemon:main-full

RUN pip uninstall -y pydantic langchain langchain-core langchain-community accelerat llama-index || true
RUN pip uninstall -y pydantic-settings langchain-openai langchain-embeddings langchain-embeddings-openai langchain-embeddings-huggingface langchain-embeddings-huggingface-transformers langchain-embeddings-huggingface-transformers-accelerate langchain-embeddings-huggingface-transformers-torch || true
RUN pip install --upgrade pip
RUN pip install --no-cache-dir \
    "pydantic==2.6.4" \
    "pydantic-settings>=2.0.3" \
    "pydantic-core>=2.16.3" \
    "pydantic[email]>=2.6.4" \
    "langchain" \
    "langchain-core" \
    "langchain-cohere"\
    PyPDF2 \
    python-docx \
    pandas
RUN pip install accelerate>=0.26.0



COPY sos_app.py /app/sos_app.py
COPY sos_pipeline.py /app/sos_pipeline.py
COPY sos_flowsettings.py /app/sos_flowsettings.py
COPY sos_chat_falcon.py /app/sos_chat_falcon.py
COPY sos_doc_loader.py /app/sos_doc_loader.py

# Désactiver l'entrypoint par défaut de l'image de base si nécessaire
ENTRYPOINT []
    

CMD ["python", "sos_app.py"]

