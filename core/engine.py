"""
CHARAMOU AI - Moteur principal v2
Architecture complète : agents, RAG, IA hybride, health monitoring.
"""
import json
import threading
import time
from pathlib import Path
from typing import Optional

from core.logger import setup_logger
from core.event_bus import EventBus
from core.assistant_state import AssistantState, AssistantStatus
from core.context_manager import ContextManager
from core.memory_manager import MemoryManager
from core.task_router import TaskRouter
from core.action_registry import ActionRegistry
from core.scheduler import Scheduler
from core.security_manager import SecurityManager
from core.plugin_manager import PluginManager
from core.health_monitor import HealthMonitor, RecoveryManager
from core.exceptions import EngineError, ConfigurationError

logger = setup_logger("Engine")
BASE_DIR = Path(__file__).parent.parent


class AssistantEngine:
    """
    Moteur central CHARAMOU AI v2.

    Nouveautés v2 :
    - ActionRegistry (remplace if/elif)
    - HealthMonitor + RecoveryManager
    - Agents spécialisés (Web, Word, System)
    - IA hybride (OpenAI + Ollama)
    - RAG (KnowledgeManager)
    - Mémoire sémantique TF-IDF
    """

    def __init__(self):
        self.config = self._load_config()
        self.name:  str = self.config.get("assistant_name", "CHARAMOU")

        # ── Noyau ────────────────────────────────────────────────────────────
        self.bus      = EventBus()
        self.state    = AssistantState()
        self.context  = ContextManager(max_history=self.config.get("max_conversation_history", 20))
        self.memory   = MemoryManager()
        self.router   = TaskRouter()
        self.scheduler = Scheduler()
        self.security  = SecurityManager()
        self.registry = ActionRegistry(security=self.security)
        self.plugins   = PluginManager(engine=self)

        # ── Surveillance ─────────────────────────────────────────────────────
        self.health   = HealthMonitor(event_bus=self.bus)
        self.recovery = RecoveryManager()

        # ── Modules ──────────────────────────────────────────────────────────
        self.recognizer  = None
        self.synthesizer = None
        self.nlp         = None
        self.ai_client   = None
        self.knowledge   = None

        # ── Agents ───────────────────────────────────────────────────────────
        self._agents = []

        self._voice_enabled: bool = self.config.get("voice_enabled", True)
        self._running = False

        logger.info(f"AssistantEngine v2 '{self.name}' créé.")

    def _start_api(self) -> None:
        """Lance l'API REST/WS si activée."""
        if self.config.get("api_enabled", True):
            try:
                from interfaces.api.server import start_api
                start_api(self, port=self.config.get("api_port", 8000))
                logger.info(f"✅ API REST/WebSocket sur le port {self.config.get('api_port', 8000)}")
            except Exception as e:
                logger.warning(f"⚠️  API : {e}")

    # ────────────────────────────────────────────────────────────────────────
    # Démarrage
    # ────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        logger.info("=" * 55)
        logger.info(f"   {self.name} AI v2 - Démarrage")
        logger.info("=" * 55)

        self._init_modules()
        self._init_agents()
        self._register_routes()
        self._subscribe_events()
        self._register_health_checks()
        self._start_api()

        self.scheduler.start()
        self.health.start()
        self.plugins.load_all()

        # Rappels pendants
        self._check_pending_reminders()

        self._running = True
        self.state.set_status(AssistantStatus.SLEEPING)

        backend = self.ai_client.current_backend() if self.ai_client else "non disponible"
        mem_summary = self.memory.get_memory_summary()

        self.speak(
            f"Bonjour ! Je suis {self.name}. "
            f"Je fonctionne en mode {backend}. "
            f"Comment puis-je vous aider ?"
        )
        logger.info(mem_summary)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interruption clavier.")
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        logger.info("Arrêt en cours...")
        self._running = False
        self.scheduler.stop()
        self.health.stop()
        self.memory.close()
        self.state.set_status(AssistantStatus.SHUTDOWN)
        self.bus.publish("assistant_shutdown")
        logger.info(f"Session terminée. {self.state.summary()}")

    # ────────────────────────────────────────────────────────────────────────
    # Initialisation
    # ────────────────────────────────────────────────────────────────────────

    def _init_modules(self) -> None:
        logger.info("Initialisation des modules...")

        # Synthèse vocale
        try:
            from modules.voice.synthesis import Synthesizer
            self.synthesizer = Synthesizer(config=self.config)
            logger.info("✅ Synthèse vocale")
        except Exception as e:
            logger.warning(f"⚠️  Synthèse : {e}")

        # Reconnaissance vocale
        try:
            from modules.voice.recognition import SpeechRecognizer
            self.recognizer = SpeechRecognizer(config=self.config)
            logger.info("✅ Reconnaissance vocale")
        except Exception as e:
            logger.warning(f"⚠️  Reconnaissance : {e}")
            self._voice_enabled = False

        # NLP
        try:
            from modules.nlp.intent_classifier import IntentClassifier
            self.nlp = IntentClassifier()
            logger.info("✅ NLP v2")
        except Exception as e:
            logger.warning(f"⚠️  NLP : {e}")

        # IA hybride (OpenAI + Ollama)
        try:
            from modules.ai.local_model import HybridAIClient
            self.ai_client = HybridAIClient(config=self.config)
            logger.info(f"✅ IA hybride (backend: {self.ai_client.current_backend()})")
        except Exception as e:
            logger.warning(f"⚠️  IA : {e}")

        # Knowledge Manager (RAG)
        try:
            from modules.services.knowledge_manager import KnowledgeManager
            self.knowledge = KnowledgeManager(
                memory=self.memory,
                ai_client=self.ai_client
            )
            logger.info("✅ KnowledgeManager (RAG)")
        except Exception as e:
            logger.warning(f"⚠️  Knowledge : {e}")

    def _init_agents(self) -> None:
        """Initialise les agents spécialisés."""
        try:
            from core.agents.web_agent    import WebAgent
            from core.agents.word_agent   import WordAgent
            from core.agents.system_agent import SystemAgent

            self._agents = [
                WebAgent(engine=self),
                WordAgent(engine=self),
                SystemAgent(engine=self),
            ]
            logger.info(f"✅ Agents : {[a.name for a in self._agents]}")
        except Exception as e:
            logger.warning(f"⚠️  Agents : {e}")

    def _register_routes(self) -> None:
        """Enregistre toutes les routes avec ActionRegistry."""
        from modules.services.weather_service     import WeatherService
        from modules.services.calendar_service    import CalendarService
        from modules.services.reminder_service    import ReminderService
        from modules.services.search_service      import SearchService
        from modules.services.translation_service import TranslationService
        from modules.services.news_service        import NewsService
        from modules.automation.system_controller import SystemController
        from modules.automation.word_controller   import WordController
        from modules.automation.browser_controller import BrowserController

        weather     = WeatherService()
        calendar    = CalendarService()
        reminder    = ReminderService(scheduler=self.scheduler, memory=self.memory)
        search      = SearchService()
        translation = TranslationService()
        news        = NewsService()
        system      = SystemController(security=self.security)
        word        = WordController(security=self.security)
        browser     = BrowserController(security=self.security)

        # ActionRegistry (nouveau système)
        self.registry.register("GET_WEATHER",      weather.handle,     "Météo en temps réel",    "services",   ["météo","temps","température"])
        self.registry.register("SET_REMINDER",      reminder.handle,    "Créer un rappel",         "services",   ["rappel","rappelle","alarme"])
        self.registry.register("GET_CALENDAR",      calendar.handle,    "Calendrier",              "services",   ["calendrier","agenda","événements"])
        self.registry.register("SEARCH_WEB",        search.handle,      "Recherche web",           "services",   ["cherche","recherche","google"])
        self.registry.register("TRANSLATE",         translation.handle, "Traduction",              "services",   ["traduis","traduction"])
        self.registry.register("GET_NEWS",          news.handle,        "Actualités",              "services",   ["actualités","news","infos"])
        self.registry.register("OPEN_APPLICATION",  system.handle_open, "Ouvrir une application",  "automation", ["ouvre","lance"],    requires=["browser_control"])
        self.registry.register("SYSTEM_VOLUME",     system.handle_volume,"Volume système",          "automation", ["volume","son"])
        self.registry.register("TAKE_SCREENSHOT",   system.handle_screenshot,"Capture d'écran",    "automation", ["capture","screenshot"])
        self.registry.register("GET_SYSTEM_STATUS", system.handle_status,    "État du système",    "system",     ["système","cpu","ram","batterie"])
        self.registry.register("SYSTEM_SHUTDOWN",   system.handle_shutdown,"Arrêt PC",              "automation", ["éteins","arrête l'ordinateur"], requires=["shutdown"])
        self.registry.register("WRITE_DOCUMENT",    word.handle,        "Créer un document Word",  "automation", ["écris","rédige","document"])
        self.registry.register("OPEN_BROWSER",      browser.handle,     "Navigateur web",          "automation", ["navigateur","site"])

        if self.knowledge:
            self.registry.register("SEARCH_KNOWLEDGE", self.knowledge.handle, "Base de connaissances", "knowledge", ["sais-tu","qu'est-ce que","explique"])

        # Synchronisation avec l'ancien TaskRouter (compatibilité)
        for action in self.registry.list_all():
            self.router.register(
                action["name"],
                lambda entities=None, context=None, n=action["name"]:
                    self.registry.execute(n, entities, context)
            )

        # Fallback IA
        self.router.set_fallback(self._ai_fallback)
        logger.info(f"Actions enregistrées : {len(self.registry)} routes")

    def _subscribe_events(self) -> None:
        self.bus.subscribe("user_spoke",       self._on_user_spoke)
        self.bus.subscribe("response_ready",   self._on_response_ready)
        self.bus.subscribe("error_occurred",   self._on_error)
        self.bus.subscribe("battery_low",      self._on_battery_low)
        self.bus.subscribe("wake_word_detected",self._on_wake_word)
        self.bus.subscribe("module_down",      self.recovery.on_module_down)

    def _register_health_checks(self) -> None:
        """Enregistre les vérifications de santé."""
        if self.recognizer:
            self.health.register("voice", lambda: None)  # check basique
        if self.ai_client:
            self.health.register("ai", lambda: None)

    # ────────────────────────────────────────────────────────────────────────
    # Boucle principale
    # ────────────────────────────────────────────────────────────────────────

    def _main_loop(self) -> None:
        logger.info("Boucle principale démarrée.")
        while self._running:
            if self._voice_enabled and self.recognizer:
                self._voice_cycle()
            else:
                self._cli_cycle()

    def _voice_cycle(self) -> None:
        self.state.set_status(AssistantStatus.LISTENING)
        try:
            text = self.recognizer.listen()
        except Exception as e:
            logger.warning(f"Voix indisponible, bascule en CLI : {e}")
            self._voice_enabled = False
            self.speak("Le microphone n'est pas disponible. Je passe en mode clavier.")
            return
        if text:
            self.bus.publish("user_spoke", text)
            self.process_input(text)

    def _cli_cycle(self) -> None:
        self.state.set_status(AssistantStatus.LISTENING)
        try:
            text = input(f"\n[{self.name}] → ").strip()
            if text:
                if text.lower() in ("quitter", "quit", "exit", "au revoir"):
                    self._running = False
                    return
                self.process_input(text)
        except EOFError:
            self._running = False

    # ────────────────────────────────────────────────────────────────────────
    # Traitement
    # ────────────────────────────────────────────────────────────────────────

    def process_input(self, text: str) -> Optional[str]:
        """
        Pipeline complet v2 :
        texte → security check → NLP → agent routing → action → réponse → TTS
        """
        if not text.strip():
            return None

        # Validation sécurité
        try:
            self.security.validate_command(text)
        except Exception as e:
            self.speak("Cette commande a été bloquée pour des raisons de sécurité.")
            return "Commande bloquée."

        self.state.set_status(AssistantStatus.PROCESSING)
        self.memory.save_turn("user", text)
        self.memory.set_working("last_input", text)

        # NLP
        intent, entities = "CONVERSATION", {}
        if self.nlp:
            try:
                intent, entities = self.nlp.classify(text)
            except Exception as e:
                logger.warning(f"NLP : {e}")

        self.context.add_user_turn(text, intent, entities)
        self.state.record_command(text, intent)

        # Routing via agents si applicable
        response = self._route_to_agent(text, intent, entities)
        if response is None:
            # Routing via ActionRegistry / TaskRouter
            try:
                self.state.set_status(AssistantStatus.EXECUTING)
                result   = self.router.route(intent, entities, context=self.context)
                response = result if isinstance(result, str) else str(result or "")
            except Exception as e:
                logger.error(f"Routing : {e}")
                response = "Désolé, une erreur est survenue."
                self.state.record_error()

        # Enrichissement mémoire
        if intent not in ("CONVERSATION",) and response:
            self.memory.remember("recent_actions", intent, {"text": text[:60], "resp": response[:60]})

        # Réponse
        if response:
            self.context.add_assistant_turn(response)
            self.memory.save_turn("assistant", response, intent)
            self.bus.publish("response_ready", response)
            self.speak(response)

        return response

    def _route_to_agent(self, text: str, intent: str, entities: dict) -> Optional[str]:
        """Délègue à un agent spécialisé si approprié."""
        # Agents prioritaires pour certains intents
        agent_intents = {
            "SEARCH_WEB":    "web_agent",
            "WRITE_DOCUMENT": "word_agent",
        }
        target_name = agent_intents.get(intent)
        for agent in self._agents:
            if target_name and agent.name == target_name:
                try:
                    return agent.execute(text, entities, context=self.context)
                except Exception as e:
                    logger.warning(f"Agent '{agent.name}' : {e}")
        return None  # Pas d'agent → routing normal

    # ────────────────────────────────────────────────────────────────────────
    # Synthèse vocale
    # ────────────────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        if not text:
            return
        print(f"\n🤖 {self.name} : {text}")
        if self.synthesizer and not self.state.is_muted:
            self.state.set_status(AssistantStatus.SPEAKING)
            try:
                self.synthesizer.speak(text)
            except Exception as e:
                logger.warning(f"TTS : {e}")
        self.state.set_status(AssistantStatus.LISTENING)

    # ────────────────────────────────────────────────────────────────────────
    # Handlers événements
    # ────────────────────────────────────────────────────────────────────────

    def _on_user_spoke(self, data):  logger.debug(f"user_spoke : {data}")
    def _on_response_ready(self, data): logger.debug(f"response_ready : {str(data)[:60]}")
    def _on_error(self, data):       logger.error(f"error_occurred : {data}")
    def _on_battery_low(self, data): self.speak(f"Attention, batterie à {data.get('percent', '?')}%.")
    def _on_wake_word(self, data):   self.speak("Oui, je vous écoute.")

    # ────────────────────────────────────────────────────────────────────────
    # Fallback IA
    # ────────────────────────────────────────────────────────────────────────

    def _ai_fallback(self, intent: str, entities: dict, context) -> str:
        if self.ai_client and self.ai_client.available:
            try:
                messages = context.get_openai_messages() if context else []
                return self.ai_client.chat(messages)
            except Exception as e:
                logger.error(f"IA fallback : {e}")
        return "Je ne suis pas sûr de comprendre. Pouvez-vous reformuler ?"

    # ────────────────────────────────────────────────────────────────────────
    # Rappels pendants
    # ────────────────────────────────────────────────────────────────────────

    def _check_pending_reminders(self) -> None:
        try:
            pending = self.memory.get_pending_reminders()
            if pending:
                titles = ", ".join(r["title"] for r in pending[:3])
                self.speak(f"Vous avez {len(pending)} rappel(s) en attente : {titles}.")
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────────────
    # Config
    # ────────────────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        path = BASE_DIR / "config" / "settings.json"
        if not path.exists():
            raise ConfigurationError(f"settings.json introuvable : {path}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def get_status(self) -> dict:
        """Retourne l'état complet du système."""
        return {
            "state":   self.state.summary(),
            "health":  self.health.get_report(),
            "memory":  self.memory.get_memory_summary(),
            "actions": len(self.registry),
            "agents":  [a.name for a in self._agents],
            "ai":      self.ai_client.current_backend() if self.ai_client else "unavailable"
        }
