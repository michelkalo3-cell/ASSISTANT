"""
CHARAMOU AI - Routeur de tâches
Dirige chaque intention vers le module approprié.
"""
import json
from pathlib import Path
from typing import Callable, Dict, Any, Optional
from core.logger import setup_logger
from core.exceptions import CommandParseError

logger = setup_logger("TaskRouter")


class TaskRouter:
    """
    Reçoit une intention + entités et appelle le bon handler.

    Flux :
      Texte utilisateur
        ↓ NLP
      Intent + Entities
        ↓ TaskRouter
      Module (automation / service / ai / system)
        ↓
      Résultat → réponse
    """

    def __init__(self):
        self._routes: Dict[str, Callable] = {}
        self._fallback: Optional[Callable] = None
        logger.info("TaskRouter initialisé.")

    def register(self, intent: str, handler: Callable) -> None:
        """Enregistre un handler pour une intention donnée."""
        self._routes[intent] = handler
        logger.debug(f"Route enregistrée : '{intent}' → {handler.__qualname__}")

    def set_fallback(self, handler: Callable) -> None:
        """Handler appelé si aucune route ne correspond."""
        self._fallback = handler

    def route(self, intent: str, entities: Dict[str, Any], context: Any = None) -> Any:
        """
        Route une intention vers son handler.
        Retourne le résultat du handler.
        """
        handler = self._routes.get(intent)

        if handler:
            logger.info(f"Routing : '{intent}' → {handler.__qualname__}")
            try:
                return handler(entities=entities, context=context)
            except Exception as e:
                logger.error(f"Erreur dans le handler '{intent}': {e}")
                raise CommandParseError(f"Erreur lors du traitement de '{intent}': {e}")
        elif self._fallback:
            logger.info(f"Intent '{intent}' non mappé → fallback IA.")
            return self._fallback(intent=intent, entities=entities, context=context)
        else:
            logger.warning(f"Intent '{intent}' non géré et pas de fallback.")
            return None

    def available_intents(self) -> list:
        return list(self._routes.keys())
