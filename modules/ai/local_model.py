"""
CHARAMOU AI - Client IA Local v2 (Ollama)
Fallback automatique entre modèles si le modèle demandé est absent.
Stratégies cloud/local/hybride.
"""
import json
import os
from typing import List, Dict, Optional
from core.logger import setup_logger
from core.exceptions import OllamaError, ModelNotAvailableError

logger = setup_logger("LocalModel_AI")

if "requests" not in globals():
    try:
        import requests
    except ImportError:
        class _MissingRequests:
            def get(self, *args, **kwargs):
                raise RuntimeError("requests non installé")

            def post(self, *args, **kwargs):
                raise RuntimeError("requests non installé")

        requests = _MissingRequests()

OLLAMA_BASE_URL = "http://localhost:11434"

SYSTEM_PROMPT = """Tu es CHARAMOU, un assistant personnel vocal intelligent.
Tu parles toujours en français, de façon naturelle et concise.
Réponds en 1-3 phrases maximum pour les réponses vocales."""

# Cascade de modèles par ordre de préférence (taille croissante)
FALLBACK_MODELS = [
    "phi3:mini",     # 3.8B — très rapide, bon pour commandes courtes
    "mistral",       # 7B  — excellent équilibre vitesse/qualité
    "llama3",        # 8B  — très bon en français
    "llama3:8b",
    "mixtral",       # 8x7B — puissant, nécessite RAM
    "llama3:70b",    # 70B — meilleure qualité, lent
]


class OllamaClient:
    """
    Client Ollama avec sélection automatique de modèle.
    Si le modèle demandé n'est pas installé → bascule vers le suivant disponible.
    """

    def __init__(self, model: str = "mistral", base_url: str = OLLAMA_BASE_URL):
        self.requested_model = model
        self.base_url        = base_url
        self._available: Optional[bool] = None
        self._active_model:  Optional[str] = None
        self._installed_models: List[str] = []
        logger.info(f"OllamaClient initialisé : modèle demandé='{model}'")

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            self._available = r.status_code == 200
            if self._available:
                self._installed_models = [m["name"].split(":")[0]
                                          for m in r.json().get("models", [])]
                self._active_model = self._select_model()
                logger.info(
                    f"Ollama : modèles installés={self._installed_models}, "
                    f"actif='{self._active_model}'"
                )
            return self._available
        except Exception:
            self._available = False
            return False

    def _select_model(self) -> Optional[str]:
        """
        Sélectionne le meilleur modèle disponible.
        Priorité : modèle demandé → cascade FALLBACK_MODELS.
        """
        installed = set(self._installed_models)

        # 1. Modèle demandé
        base = self.requested_model.split(":")[0]
        if base in installed:
            return self.requested_model

        # 2. Cascade de fallback
        for model in FALLBACK_MODELS:
            base_fb = model.split(":")[0]
            if base_fb in installed:
                logger.info(
                    f"Modèle '{self.requested_model}' absent → fallback '{model}'"
                )
                return model

        # 3. Premier modèle installé (dernier recours)
        if self._installed_models:
            fallback = self._installed_models[0]
            logger.warning(f"Aucun modèle recommandé installé → utilisation de '{fallback}'")
            return fallback

        logger.error("Aucun modèle Ollama installé.")
        return None

    def list_models(self) -> List[str]:
        if not self.is_available():
            return []
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            return []

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if not self.is_available():
            raise OllamaError("Ollama non disponible. Démarrez : ollama serve")

        model = self._active_model
        if not model:
            raise ModelNotAvailableError(
                "Aucun modèle disponible. Installez un modèle : ollama pull mistral"
            )

        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        payload = {
            "model":    model,
            "messages": full_messages,
            "stream":   False,
            "options":  {"temperature": 0.7, "num_predict": 300}
        }

        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=30)
            r.raise_for_status()
            text = r.json()["message"]["content"].strip()
            logger.info(f"Réponse Ollama ({model}) : {len(text)} chars")
            return text
        except Exception as e:
            # Tente le prochain modèle en cascade
            logger.warning(f"Erreur avec '{model}' : {e} — tentative fallback...")
            return self._try_next_model(messages, exclude=model)

    def _try_next_model(self, messages: List[Dict], exclude: str) -> str:
        """Essaie le prochain modèle dans la cascade."""
        installed = set(self._installed_models)
        for model in FALLBACK_MODELS:
            base = model.split(":")[0]
            if base in installed and model != exclude:
                logger.info(f"Tentative avec modèle de secours : '{model}'")
                try:
                    full = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
                    r = requests.post(
                        f"{self.base_url}/api/chat",
                        json={"model": model, "messages": full, "stream": False},
                        timeout=30
                    )
                    r.raise_for_status()
                    self._active_model = model
                    return r.json()["message"]["content"].strip()
                except Exception:
                    continue
        raise OllamaError("Tous les modèles ont échoué.")

    def ask(self, question: str) -> str:
        return self.chat([{"role": "user", "content": question}])

    @property
    def active_model(self) -> str:
        return self._active_model or "non sélectionné"


# ─────────────────────────────────────────────────────────────────────────────
# Client IA hybride Cloud + Local
# ─────────────────────────────────────────────────────────────────────────────
class HybridAIClient:
    """
    Bascule automatique OpenAI ↔ Ollama selon disponibilité et stratégie.
    """

    def __init__(self, config: dict = None):
        self.config       = config or {}
        self.strategy     = self.config.get("ai_strategy", "cloud_first")
        self.offline_mode = self.config.get("offline_mode", False)

        try:
            from modules.ai.openai_client import OpenAIClient
            self._cloud = OpenAIClient(config=config)
        except Exception:
            self._cloud = None

        self._local = OllamaClient(model=self.config.get("local_model", "mistral"))
        logger.info(f"HybridAIClient : stratégie='{self.strategy}'")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        if self.offline_mode or self.strategy == "local_only":
            return self._try_local(messages)
        if self.strategy == "local_first":
            try:
                return self._try_local(messages)
            except Exception:
                return self._try_cloud(messages)
        # cloud_first (défaut)
        try:
            return self._try_cloud(messages)
        except Exception:
            logger.warning("OpenAI indisponible → Ollama")
            return self._try_local(messages)

    def _try_cloud(self, messages: List[Dict]) -> str:
        if self._cloud and self._cloud.available:
            return self._cloud.chat(messages)
        raise OllamaError("Cloud indisponible.")

    def _try_local(self, messages: List[Dict]) -> str:
        if self._local.is_available():
            return self._local.chat(messages)
        raise OllamaError("Ollama indisponible.")

    def ask(self, question: str) -> str:
        return self.chat([{"role": "user", "content": question}])

    def current_backend(self) -> str:
        if self.offline_mode:
            return f"local ({self._local.active_model})"
        if self.strategy == "cloud_first" and self._cloud and self._cloud.available:
            return f"cloud ({self.config.get('ai_model', 'gpt-4o-mini')})"
        if self._local.is_available():
            return f"local ({self._local.active_model})"
        return "unavailable"

    def get_stats(self) -> Dict:
        return {
            "strategy":    self.strategy,
            "cloud_ok":    bool(self._cloud and self._cloud.available),
            "local_ok":    self._local.is_available(),
            "active":      self.current_backend(),
            "local_models": self._local.list_models(),
        }

    @property
    def available(self) -> bool:
        return bool(
            (self._cloud and self._cloud.available)
            or self._local.is_available()
        )
