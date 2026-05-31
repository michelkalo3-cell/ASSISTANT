"""
CHARAMOU AI - Bus d'événements
Communication asynchrone entre tous les modules.
"""
import threading
from typing import Callable, Dict, List, Any
from core.logger import setup_logger

logger = setup_logger("EventBus")


class EventBus:
    """
    Bus d'événements centralisé.
    Permet à chaque module de publier et écouter des événements
    sans couplage direct.

    Événements standards :
      - user_spoke          : l'utilisateur a parlé
      - command_detected    : une commande a été identifiée
      - response_ready      : réponse prête à être synthétisée
      - task_completed      : une tâche s'est terminée
      - error_occurred      : une erreur s'est produite
      - battery_low         : batterie faible
      - internet_disconnected : connexion perdue
      - wake_word_detected  : mot de réveil détecté
      - assistant_sleeping  : passage en veille
      - assistant_awake     : réveil de l'assistant
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        logger.info("EventBus initialisé.")

    def subscribe(self, event: str, callback: Callable) -> None:
        """Abonne un callback à un événement."""
        with self._lock:
            if event not in self._subscribers:
                self._subscribers[event] = []
            if callback not in self._subscribers[event]:
                self._subscribers[event].append(callback)
                logger.debug(f"Abonnement : '{event}' → {callback.__qualname__}")

    def unsubscribe(self, event: str, callback: Callable) -> None:
        """Désabonne un callback d'un événement."""
        with self._lock:
            if event in self._subscribers:
                self._subscribers[event] = [
                    cb for cb in self._subscribers[event] if cb != callback
                ]

    def publish(self, event: str, data: Any = None) -> None:
        """
        Publie un événement vers tous les abonnés.
        Chaque callback est exécuté dans un thread séparé.
        """
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))

        if not callbacks:
            logger.debug(f"Événement '{event}' publié sans abonnés.")
            return

        logger.debug(f"Événement '{event}' → {len(callbacks)} abonné(s).")
        for callback in callbacks:
            thread = threading.Thread(
                target=self._safe_call,
                args=(callback, event, data),
                daemon=True
            )
            thread.start()

    def publish_sync(self, event: str, data: Any = None) -> None:
        """Publie un événement de façon synchrone (bloquant)."""
        with self._lock:
            callbacks = list(self._subscribers.get(event, []))
        for callback in callbacks:
            self._safe_call(callback, event, data)

    def _safe_call(self, callback: Callable, event: str, data: Any) -> None:
        try:
            callback(data)
        except Exception as e:
            logger.error(f"Erreur dans le callback '{callback.__qualname__}' pour '{event}': {e}")

    def list_events(self) -> Dict[str, int]:
        """Retourne la liste des événements et leur nombre d'abonnés."""
        with self._lock:
            return {event: len(cbs) for event, cbs in self._subscribers.items()}


# Instance globale partagée
bus = EventBus()
