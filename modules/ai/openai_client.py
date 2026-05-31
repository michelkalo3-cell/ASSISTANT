"""
CHARAMOU AI - Client OpenAI
Gère les appels à l'API OpenAI (GPT-4o-mini par défaut).
"""
import os
from typing import List, Dict, Optional
from core.logger import setup_logger
from core.exceptions import AIError, APIKeyMissingError

logger = setup_logger("OpenAIClient")

SYSTEM_PROMPT = """Tu es CHARAMOU, un assistant personnel vocal intelligent, développé pour Windows.
Tu parles toujours en français, de manière naturelle, concise et utile.
Tu es capable de gérer des tâches quotidiennes, d'automatiser des applications et de répondre à des questions.
Sois chaleureux, efficace et précis. Tes réponses vocales doivent être courtes (1-3 phrases max).
"""


class OpenAIClient:
    """
    Encapsule les appels à l'API OpenAI.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.model = self.config.get("ai_model", "gpt-4o-mini")
        self.max_tokens = 300
        self._client = self._init_client()

    def _init_client(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY non défini — client IA désactivé.")
            return None
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            logger.info(f"OpenAI client initialisé (modèle : {self.model}).")
            return client
        except ImportError:
            logger.warning("openai non installé.")
            return None
        except Exception as e:
            logger.error(f"Erreur init OpenAI : {e}")
            return None

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Envoie une conversation à OpenAI et retourne la réponse.
        messages = [{"role": "user"/"assistant", "content": "..."}]
        """
        if not self._client:
            return self._offline_response(messages)

        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )
            text = response.choices[0].message.content.strip()
            logger.info(f"Réponse OpenAI reçue ({len(text)} chars).")
            return text
        except Exception as e:
            logger.error(f"Erreur API OpenAI : {e}")
            return "Désolé, je ne peux pas me connecter à l'IA pour le moment."

    def ask(self, question: str) -> str:
        """Raccourci pour une question simple."""
        return self.chat([{"role": "user", "content": question}])

    def _offline_response(self, messages: List[dict]) -> str:
        """Réponse de secours sans API."""
        last = messages[-1].get("content", "") if messages else ""
        logger.debug("Mode offline — réponse par défaut.")
        return "Je fonctionne actuellement sans connexion IA. Veuillez configurer votre clé OpenAI."

    @property
    def available(self) -> bool:
        return self._client is not None
