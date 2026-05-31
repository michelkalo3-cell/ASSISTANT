"""
CHARAMOU AI - Agent de base
Tous les agents spécialisés héritent de cette classe.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from core.logger import setup_logger


class BaseAgent(ABC):
    """
    Agent autonome capable d'exécuter une séquence d'actions
    pour atteindre un objectif.

    Cycle : plan → execute → observe → adjust → result
    """

    name:        str = "base_agent"
    description: str = ""

    def __init__(self, engine=None):
        self.engine  = engine
        self.memory  = engine.memory  if engine else None
        self.security = engine.security if engine else None
        self._logger = setup_logger(f"Agent.{self.name}")
        self._steps: List[str] = []

    @abstractmethod
    def can_handle(self, task: str, entities: dict) -> bool:
        """Retourne True si l'agent peut traiter cette tâche."""
        pass

    @abstractmethod
    def execute(self, task: str, entities: dict, context: Any = None) -> str:
        """Exécute la tâche et retourne le résultat."""
        pass

    def plan(self, task: str) -> List[str]:
        """Génère un plan d'étapes pour accomplir la tâche."""
        return [f"Exécuter : {task}"]

    def _log_step(self, step: str) -> None:
        self._steps.append(step)
        self._logger.info(f"[{self.name}] Étape : {step}")

    def get_steps(self) -> List[str]:
        return list(self._steps)
