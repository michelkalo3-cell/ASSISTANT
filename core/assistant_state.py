"""
CHARAMOU AI - Gestion de l'état de l'assistant
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("AssistantState")


class AssistantStatus(Enum):
    SLEEPING    = auto()   # En veille, attend le wake word
    LISTENING   = auto()   # Écoute active
    PROCESSING  = auto()   # Traitement de la commande
    SPEAKING    = auto()   # En train de parler
    EXECUTING   = auto()   # Exécution d'une tâche
    ERROR       = auto()   # État d'erreur
    SHUTDOWN    = auto()   # Arrêt


@dataclass
class AssistantState:
    status: AssistantStatus = AssistantStatus.SLEEPING
    last_command: Optional[str] = None
    last_response: Optional[str] = None
    current_intent: Optional[str] = None
    is_muted: bool = False
    conversation_active: bool = False
    last_activity: datetime = field(default_factory=datetime.now)
    session_start: datetime = field(default_factory=datetime.now)
    command_count: int = 0
    error_count: int = 0
    user_name: Optional[str] = None

    def set_status(self, new_status: AssistantStatus) -> None:
        old = self.status
        self.status = new_status
        self.last_activity = datetime.now()
        logger.debug(f"État : {old.name} → {new_status.name}")

    def record_command(self, command: str, intent: str) -> None:
        self.last_command = command
        self.current_intent = intent
        self.command_count += 1

    def record_error(self) -> None:
        self.error_count += 1

    def is_available(self) -> bool:
        return self.status in (AssistantStatus.SLEEPING, AssistantStatus.LISTENING)

    def session_duration(self) -> float:
        return (datetime.now() - self.session_start).total_seconds()

    def summary(self) -> dict:
        return {
            "status": self.status.name,
            "commands_handled": self.command_count,
            "errors": self.error_count,
            "session_seconds": round(self.session_duration()),
            "muted": self.is_muted
        }
