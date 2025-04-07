
"""
sos_chat_falcon.py

Module pour initialiser et gérer le modèle Falcon local via HuggingFace Transformers.
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from kotaemon.base import LLMInterface
from huggingface_hub import login

# Vérification de la présence du token HuggingFace
token = os.environ.get("HUGGINGFACE_HUB_TOKEN")
if not token:
    raise EnvironmentError("HUGGINGFACE_HUB_TOKEN is missing from environment.")
# Optionnel : login(token=token)

class ChatFalcon:
    """
    Classe encapsulant le modèle Falcon pour la génération de texte.
    """
    def __init__(self,
                 model_name="tiiuae/falcon-7b-instruct",
                 max_length=512,
                 do_sample=True,
                 temperature=0.7,
                 **kwargs):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        print("[ChatFalcon] Tokenizer loaded.")
        print("[ChatFalcon] Loading Falcon model")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            revision="main",
            trust_remote_code=True,
            device_map="auto",
            torch_dtype=torch.float16
        )
        print("[ChatFalcon] Model loaded.")
        print("[ChatFalcon] Creating pipeline...")
        self.pipeline = pipeline(
            task="text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_length=max_length,
            max_new_tokens=150,
            do_sample=do_sample,
            temperature=temperature
        )
        print("[ChatFalcon] Pipeline ready. Falcon is ready to use.")

    def run(self, prompt: str, **kwargs) -> LLMInterface:
        """
        Génère une réponse en utilisant le pipeline Falcon.
        """
        response = self.pipeline(prompt)[0]["generated_text"]
        return LLMInterface(content=response)

    def invoke(self, prompt: str, *args, **kwargs) -> LLMInterface:
        return self.run(prompt, **kwargs)
