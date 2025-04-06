import streamlit as st
import os
import tempfile
from read_answer_aap import Read_Questions_in_docx

st.set_page_config(page_title="Test code JF", layout="wide")
st.title("📄 Analyse de fichier AAP (.docx)")
uploaded_file = st.file_uploader("Chargez un fichier Word (.docx)", type=["docx"])

# Listes de mots clés
list_of_SizeWords_OK = [
    " MAX", " MIN", " CARACT", " CHARACT", " LIGNE", " LINE", " SIGN", " PAGE", 
    " PAS EXC", " NOT EXCEED", " MOTS", " WORDS"
]

list_of_SizeWords_KO = [
    " SIGNAT", " MAXIMI", " MONTH", " MOIS", " ANS", " ANNé", " YEAR", " DAY", " JOUR",
    " DURéE", " DURATION", " IMPACT", " AMOUNT", " MONTANT"
]

TagQStart = "<>"
TagQEnd = "</>"

if uploaded_file is not None:
    st.info("Fichier reçu. Lancement de l’analyse...")

    with tempfile.TemporaryDirectory(dir="temp") as tmpdirname:
        file_path = os.path.join(tmpdirname, uploaded_file.name)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        log_dir = os.path.join(tmpdirname, "logs")
        os.makedirs(log_dir, exist_ok=True)

        # Lancement du traitement
        with st.spinner("Extraction des questions en cours..."):
            extracted_questions = Read_Questions_in_docx(
                PathFolderSource=tmpdirname + "/",
                PathForOutputsAndLogs=log_dir,
                list_of_SizeWords_OK=list_of_SizeWords_OK,
                list_of_SizeWords_KO=list_of_SizeWords_KO,
                TagQStart=TagQStart,
                TagQEnd=TagQEnd
            )

        st.success("Extraction terminée")
        st.write(f"Nombre de questions détectées : {len(extracted_questions)}")

        for idx, q in enumerate(extracted_questions):
            st.markdown(f"### Question {idx+1}")
            st.json(q)
