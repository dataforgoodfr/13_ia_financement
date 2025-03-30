import streamlit as st
from hybrid_retriever import process_new_pp, process_existing_pp, get_vectorstore_from_hash
from langchain_community.document_loaders import PyPDFLoader
import os
import pandas as pd

def load_doc(pdf_file_path):
    loader = PyPDFLoader(pdf_file_path)
    pages = loader.load()

    bruits = ["Planète Urgence | FOREST Programme"]
    for doc in pages:
        for bruit in bruits:
            if bruit in doc.page_content:
                doc.page_content = doc.page_content.replace(bruit, "")
    pages = [doc for doc in pages if len(doc.page_content) > 0]

    full_text = "".join([p.page_content for p in pages])
    return full_text

def load_pp_traces():
    st.markdown("### 📚 Projets déjà enregistrés")
    file_path = "pp_hashes.json"
    if os.path.exists(file_path):
        table = pd.read_json(file_path).T
        table = table.sort_values("Date de création", ascending=False)
        table['Date de création'] = pd.to_datetime(table['Date de création']).dt.floor('s')
        st.dataframe(table.reset_index(drop=True))
        return table
    else:
        st.info("Aucun projet enregistré pour l’instant.")
        return pd.DataFrame()

def run():
    st.title("📁 Présentation de Projets (PP)")

    df_existing_pp = load_pp_traces()

    # Charger un nouveau PP
    st.subheader("➕ Charger un nouveau document de projet")
    col1, col2, col3 = st.columns(3)
    with col1:
        btn_new_pp = st.button("📤 Charger PP")
    with col2:
        pp_name = st.text_input("Nom du PP", placeholder="Ex: Projet Mahakam")
    with col3:
        max_size = st.number_input("Taille max à indexer (caractères)", step=100, value=3000)

    input_file = st.file_uploader("📎 Téléversez un fichier PDF", type=["pdf"])

    st.markdown("<hr>", unsafe_allow_html=True)

    # Utiliser un PP existant
    st.subheader("♻️ Utiliser un projet existant")
    col4, col5 = st.columns(2)
    with col4:
        existing_pp_name = st.selectbox("📂 Choisir un PP existant",
                                        options=df_existing_pp["Nom du PP"].unique() if not df_existing_pp.empty else [])
    with col5:
        btn_existing_pp = st.button("✅ Utiliser ce PP")

    # Traitement d’un nouveau PP
    if btn_new_pp:
        if input_file is None or pp_name.strip() == "":
            st.error("Veuillez fournir un fichier PDF **et** un nom de projet.")
        else:
            with st.spinner("Chargement et traitement..."):
                temp_path = os.path.join("temp", input_file.name)
                os.makedirs("temp", exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(input_file.read())

                text = load_doc(temp_path)
                text_cut = text[: max(1, len(text) - int(max_size))]

                if not text_cut.strip():
                    st.error("Document trop court ou taille max trop élevée.")
                    return

                for message in process_new_pp(text_cut, pp_name):
                    st.markdown(message, unsafe_allow_html=True)

    # Utiliser un PP existant
    elif btn_existing_pp:
        if existing_pp_name.strip() == "":
            st.warning("⚠️ Veuillez sélectionner un projet.")
        else:
            hash_value = df_existing_pp[df_existing_pp["Nom du PP"] == existing_pp_name].index.values[0]

            for message in process_existing_pp(hash_value, existing_pp_name):
                st.markdown(message, unsafe_allow_html=True)

            vector_store = get_vectorstore_from_hash(hash_value)

            if vector_store:
                st.session_state["vector_store"] = vector_store
                st.session_state["current_pp_name"] = existing_pp_name
                st.success(f"✅ Le projet « {existing_pp_name} » est prêt à être utilisé.")
            else:
                st.error("Impossible de charger la base vectorielle pour ce PP.")
