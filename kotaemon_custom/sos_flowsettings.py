import os
from kotaemon.storages import LanceDBDocumentStore
from kotaemon.storages.vectorstores.chroma import ChromaVectorStore
from kotaemon.llms.chats.openai import ChatOpenAI
from sos_chat_falcon import ChatFalcon

LLM_MODE = os.environ.get("LLM_MODE", "falcon").lower()
print(f"[sos_flowsettings] LLM_MODE={LLM_MODE}")

# --- Patch : Ajout de la méthode similarity_search ---
class CustomChromaVectorStore(ChromaVectorStore):
    def similarity_search(self, query: str, k: int = 3):
        """Ajout de la méthode manquante pour la recherche de similarité"""
        results = self._client.query(query=query, top_k=k)
        docs = results["documents"]
        metadatas = results.get("metadatas", [{}]*len(docs))
        return [
            {
                "text": doc[0] if isinstance(doc, list) else doc,
                "metadata": meta
            }
            for doc, meta in zip(docs, metadatas)
        ]

KH_DOCUMENTSTORE = LanceDBDocumentStore(path="./ktem_app_data/user_data/docstore")
KH_VECTORSTORE = CustomChromaVectorStore(
    persist_directory="./ktem_app_data/user_data/chroma",
    collection_name="default"
)

if LLM_MODE == "falcon":
    print("[sos_flowsettings] Using Falcon local for chat.")
    KH_CHAT_LLM = ChatFalcon(
        model_name="tiiuae/falcon-7b-instruct",
        max_length=512
    )
else:
    print("[sos_flowsettings] Using OpenAI chat.")
    KH_CHAT_LLM = ChatOpenAI(
        model="gpt-3.5-turbo",
        api_key=os.environ.get("OPENAI_API_KEY")
    )
