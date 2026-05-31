"""
CHARAMOU AI - Gestionnaire de contexte conversationnel
Conserve le fil de la conversation et les entités extraites.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from core.logger import setup_logger

logger = setup_logger("ContextManager")


@dataclass
class Turn:
    """Un tour de conversation (entrée utilisateur + réponse)."""
    role: str           # "user" ou "assistant"
    content: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class ContextManager:
    """
    Maintient le contexte de la conversation en cours.
    Conserve un historique glissant et des entités persistantes.
    """

    def __init__(self, max_history: int = 20):
        self.max_history = max_history
        self._history: deque = deque(maxlen=max_history)
        self._entities: Dict[str, Any] = {}   # Entités persistantes de session
        self._current_intent: Optional[str] = None
        logger.info(f"ContextManager initialisé (max {max_history} tours).")

    # ─── Historique ──────────────────────────────────────────────────────────

    def add_user_turn(self, text: str, intent: str = None, entities: dict = None) -> None:
        turn = Turn(role="user", content=text,
                    intent=intent, entities=entities or {})
        self._history.append(turn)
        self._current_intent = intent
        if entities:
            self._entities.update(entities)
        logger.debug(f"Tour utilisateur : '{text[:60]}' | intent={intent}")

    def add_assistant_turn(self, text: str) -> None:
        turn = Turn(role="assistant", content=text)
        self._history.append(turn)
        logger.debug(f"Tour assistant : '{text[:60]}'")

    def get_history(self) -> List[Turn]:
        return list(self._history)

    def get_openai_messages(self) -> List[dict]:
        """Formate l'historique pour l'API OpenAI."""
        return [
            {"role": t.role, "content": t.content}
            for t in self._history
        ]

    # ─── Entités ─────────────────────────────────────────────────────────────

    def set_entity(self, key: str, value: Any) -> None:
        self._entities[key] = value

    def get_entity(self, key: str, default=None) -> Any:
        return self._entities.get(key, default)

    def get_entities(self) -> Dict[str, Any]:
        return dict(self._entities)

    # ─── Contexte ────────────────────────────────────────────────────────────

    @property
    def current_intent(self) -> Optional[str]:
        return self._current_intent

    def last_user_message(self) -> Optional[str]:
        for turn in reversed(list(self._history)):
            if turn.role == "user":
                return turn.content
        return None

    def last_assistant_message(self) -> Optional[str]:
        for turn in reversed(list(self._history)):
            if turn.role == "assistant":
                return turn.content
        return None

    def is_follow_up(self) -> bool:
        """Détecte si la question actuelle est une suite d'une précédente."""
        return len(self._history) > 2

    def clear(self) -> None:
        self._history.clear()
        self._entities.clear()
        self._current_intent = None
        logger.info("Contexte réinitialisé.")

    def summary(self) -> dict:
        return {
            "turns": len(self._history),
            "intent": self._current_intent,
            "entities": list(self._entities.keys())
        }
