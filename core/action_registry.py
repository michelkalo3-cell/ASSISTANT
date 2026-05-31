"""
CHARAMOU AI - ActionRegistry
Remplace les chaînes if/elif par un registre d'actions propre et extensible.
"""
import inspect
from typing import Callable, Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from core.logger import setup_logger
from core.exceptions import CommandParseError

logger = setup_logger("ActionRegistry")


@dataclass
class Action:
    name:        str
    handler:     Callable
    description: str        = ""
    category:    str        = "general"
    keywords:    List[str]  = field(default_factory=list)
    requires:    List[str]  = field(default_factory=list)   # permissions requises
    enabled:     bool       = True


class ActionRegistry:
    """
    Registre central de toutes les actions disponibles.

    Au lieu de :
        if intent == "GET_WEATHER": ...
        elif intent == "OPEN_APP": ...

    On utilise :
        registry.execute("GET_WEATHER", entities=...)

    Avantages :
    - Introspection complète (liste des actions disponibles)
    - Activation/désactivation à chaud
    - Catégorisation
    - Validation des permissions intégrée
    """

    def __init__(self, security=None):
        self._actions: Dict[str, Action] = {}
        self.security = security
        logger.info("ActionRegistry initialisé.")

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = "",
        category: str = "general",
        keywords: List[str] = None,
        requires: List[str] = None
    ) -> None:
        action = Action(
            name=name,
            handler=handler,
            description=description or (handler.__doc__ or "").strip().split("\n")[0],
            category=category,
            keywords=keywords or [],
            requires=requires or []
        )
        self._actions[name] = action
        logger.debug(f"Action enregistrée : [{category}] '{name}'")

    def execute(self, name: str, entities: dict = None, context: Any = None) -> Any:
        """Exécute une action par son nom."""
        action = self._actions.get(name)

        if not action:
            raise CommandParseError(f"Action '{name}' non trouvée dans le registre.")

        if not action.enabled:
            return f"L'action '{name}' est temporairement désactivée."

        # Vérification des permissions
        if self.security and action.requires:
            for perm in action.requires:
                self.security.require(perm)

        logger.info(f"Exécution : '{name}' ({action.category})")
        return action.handler(entities=entities or {}, context=context)

    def disable(self, name: str) -> None:
        if name in self._actions:
            self._actions[name].enabled = False
            logger.info(f"Action désactivée : '{name}'")

    def enable(self, name: str) -> None:
        if name in self._actions:
            self._actions[name].enabled = True
            logger.info(f"Action réactivée : '{name}'")

    def get_by_category(self, category: str) -> List[Action]:
        return [a for a in self._actions.values() if a.category == category]

    def search_by_keyword(self, text: str) -> Optional[str]:
        """Trouve l'action la plus probable à partir d'un texte."""
        text_lower = text.lower()
        best_name  = None
        best_score = 0
        for name, action in self._actions.items():
            if not action.enabled:
                continue
            score = sum(1 for kw in action.keywords if kw.lower() in text_lower)
            if score > best_score:
                best_score = score
                best_name  = name
        return best_name

    def list_all(self) -> List[Dict]:
        return [
            {
                "name":     a.name,
                "category": a.category,
                "desc":     a.description,
                "enabled":  a.enabled
            }
            for a in self._actions.values()
        ]

    def __len__(self) -> int:
        return len(self._actions)
