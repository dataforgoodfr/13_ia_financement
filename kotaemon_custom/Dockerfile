# Dockerfile
FROM ghcr.io/cinnamon/kotaemon:main-full
RUN pip install --no-cache-dir PyPDF2 docx pandas
COPY sos_chat_falcon.py /app/sos_chat_falcon.py
COPY sos_flowsettings.py /app/sos_flowsettings.py
COPY sos_pipeline.py /app/sos_pipeline.py
CMD ["python", "app.py"]
