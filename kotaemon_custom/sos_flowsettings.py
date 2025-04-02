import os
from kotaemon.storages import LanceDBDocumentStore
from kotaemon.storages.vectorstores.chroma import ChromaVectorStore
from kotaemon.llms.chats.openai import ChatOpenAI
from sos_chat_falcon import ChatFalcon

LLM_MODE = os.environ.get("LLM_MODE", "falcon").lower()
print(f"[sos_flowsettings] LLM_MODE={LLM_MODE}")

KH_DOCUMENTSTORE = LanceDBDocumentStore(path="./ktem_app_data/user_data/docstore")
KH_VECTORSTORE = ChromaVectorStore(
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
