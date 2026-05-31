"""
CHARAMOU AI - Gestionnaire de conversation
Maintient le fil de la conversation avec l'IA.
"""
from typing import List, Dict, Optional
from modules.ai.openai_client import OpenAIClient
from core.context_manager import ContextManager
from core.logger import setup_logger

logger = setup_logger("ConversationManager")


class ConversationManager:
    """
    Orchestre la conversation entre l'utilisateur et l'IA.
    Construit l'historique et gère les appels au modèle.
    """

    def __init__(self, ai_client: OpenAIClient, context: ContextManager):
        self.ai_client = ai_client
        self.context   = context
        logger.info("ConversationManager initialisé.")

    def respond(self, user_text: str) -> str:
        """
        Prend l'entrée utilisateur, envoie à l'IA avec contexte, retourne la réponse.
        """
        self.context.add_user_turn(user_text)
        messages = self.context.get_openai_messages()

        response = self.ai_client.chat(messages)

        self.context.add_assistant_turn(response)
        logger.info(f"Réponse conversation : '{response[:80]}'")
        return response

    def reset(self) -> None:
        self.context.clear()
        logger.info("Conversation réinitialisée.")

    def get_summary(self) -> dict:
        return self.context.summary()
