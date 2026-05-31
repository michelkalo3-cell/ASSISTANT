"""
CHARAMOU AI - Gestionnaire de plugins
Charge dynamiquement les plugins depuis modules/plugins/.
"""
import importlib
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from core.logger import setup_logger

logger = setup_logger("PluginManager")
PLUGINS_DIR = Path(__file__).parent.parent / "modules" / "plugins"


class BasePlugin:
    """
    Classe de base que tout plugin doit hériter.
    """
    name: str = "unnamed_plugin"
    version: str = "0.1.0"
    description: str = ""

    def __init__(self, engine=None):
        self.engine = engine

    def setup(self) -> bool:
        """Initialisation du plugin. Retourne True si succès."""
        return True

    def teardown(self) -> None:
        """Nettoyage à la fermeture."""
        pass

    def register_routes(self, router) -> None:
        """Enregistre les routes du plugin dans le TaskRouter."""
        pass

    def on_event(self, event: str, data: Any) -> None:
        """Appelé lors d'événements du bus."""
        pass


class PluginManager:
    """
    Découvre, charge et gère les plugins.
    Un plugin = un dossier dans modules/plugins/ contenant plugin.py avec une classe Plugin.
    """

    def __init__(self, engine=None):
        self.engine = engine
        self._plugins: Dict[str, BasePlugin] = {}
        logger.info("PluginManager initialisé.")

    def discover(self) -> list:
        """Retourne la liste des plugins disponibles."""
        available = []
        if not PLUGINS_DIR.exists():
            return available
        for item in PLUGINS_DIR.iterdir():
            if item.is_dir() and (item / "plugin.py").exists():
                available.append(item.name)
        logger.info(f"Plugins découverts : {available}")
        return available

    def load(self, plugin_name: str) -> bool:
        """Charge un plugin par son nom."""
        plugin_path = PLUGINS_DIR / plugin_name / "plugin.py"
        if not plugin_path.exists():
            logger.error(f"Plugin '{plugin_name}' introuvable.")
            return False

        try:
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}", plugin_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, "Plugin"):
                logger.error(f"Plugin '{plugin_name}' : classe 'Plugin' manquante.")
                return False

            plugin_instance: BasePlugin = module.Plugin(engine=self.engine)
            if plugin_instance.setup():
                self._plugins[plugin_name] = plugin_instance
                logger.info(f"Plugin chargé : '{plugin_name}' v{plugin_instance.version}")
                return True
            else:
                logger.warning(f"Plugin '{plugin_name}' : setup() a échoué.")
                return False

        except Exception as e:
            logger.error(f"Erreur chargement plugin '{plugin_name}': {e}")
            return False

    def load_all(self) -> None:
        """Charge tous les plugins disponibles."""
        for name in self.discover():
            self.load(name)

    def unload(self, plugin_name: str) -> bool:
        if plugin_name in self._plugins:
            self._plugins[plugin_name].teardown()
            del self._plugins[plugin_name]
            logger.info(f"Plugin '{plugin_name}' déchargé.")
            return True
        return False

    def get(self, plugin_name: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_name)

    def broadcast_event(self, event: str, data: Any = None) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.on_event(event, data)
            except Exception as e:
                logger.error(f"Erreur dans plugin '{plugin.name}' event '{event}': {e}")

    def loaded_plugins(self) -> list:
        return list(self._plugins.keys())
