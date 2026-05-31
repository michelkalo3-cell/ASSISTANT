"""
CHARAMOU AI - SecurityManager v2
PermissionManager + CommandValidator + ApiKeyVault + AuditLogger
"""
import os
import re
import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Any, List, Optional
from core.logger import setup_logger
from core.exceptions import PermissionDeniedError, CommandBlockedError, SecurityError

logger = setup_logger("SecurityManager")
PERMISSIONS_PATH = Path(__file__).parent.parent / "config" / "permissions.json"
AUDIT_LOG_PATH   = Path(__file__).parent.parent / "logs" / "security.log"

# ─────────────────────────────────────────────────────────────────────────────
# AuditLogger
# ─────────────────────────────────────────────────────────────────────────────
class AuditLogger:
    """Enregistre toutes les actions sensibles dans security.log."""

    def __init__(self):
        self._log = logging.getLogger("AuditLogger")
        self._log.setLevel(logging.DEBUG)
        if not self._log.handlers:
            h = logging.handlers.RotatingFileHandler(
                AUDIT_LOG_PATH, maxBytes=2*1024*1024, backupCount=5, encoding="utf-8"
            ) if hasattr(logging, 'handlers') else logging.FileHandler(AUDIT_LOG_PATH)
            import logging.handlers as lh
            h = lh.RotatingFileHandler(AUDIT_LOG_PATH, maxBytes=2*1024*1024, backupCount=5, encoding="utf-8")
            h.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            self._log.addHandler(h)

    def log(self, action: str, status: str, detail: str = "") -> None:
        self._log.info(f"[{status.upper()}] action='{action}' detail='{detail}'")


# ─────────────────────────────────────────────────────────────────────────────
# CommandValidator
# ─────────────────────────────────────────────────────────────────────────────
class CommandValidator:
    """
    Valide les commandes avant exécution.
    Bloque les patterns dangereux (injection, escalade de privilèges…).
    """

    # Patterns shell dangereux
    BLOCKED_PATTERNS: List[re.Pattern] = [
        re.compile(r'\b(rm\s+-rf|del\s+/[sf]|format\s+[a-z]:)', re.IGNORECASE),
        re.compile(r'(&&|\|\||;)\s*(rm|del|format|shutdown|reboot)', re.IGNORECASE),
        re.compile(r'(__import__|exec\(|eval\(|os\.system)', re.IGNORECASE),
        re.compile(r'(drop\s+table|delete\s+from|truncate)', re.IGNORECASE),
        re.compile(r'(net\s+user|net\s+localgroup|reg\s+add)', re.IGNORECASE),
    ]

    # Applications autorisées à être lancées
    ALLOWED_APPS = {
        "word", "excel", "powerpoint", "outlook", "notepad", "calc",
        "calculator", "calculatrice", "explorer", "chrome", "firefox",
        "edge", "teams", "zoom", "discord", "spotify", "vlc", "code",
        "notepad++", "paint", "wordpad"
    }

    def validate_text(self, text: str) -> bool:
        """Retourne True si le texte est sûr."""
        for pattern in self.BLOCKED_PATTERNS:
            if pattern.search(text):
                raise CommandBlockedError(f"Commande bloquée : pattern dangereux détecté.")
        return True

    def validate_app_name(self, app_name: str) -> bool:
        """Vérifie si l'application est dans la liste blanche."""
        if app_name.lower().strip() not in self.ALLOWED_APPS:
            raise CommandBlockedError(
                f"Application '{app_name}' non autorisée. "
                f"Liste blanche : {sorted(self.ALLOWED_APPS)}"
            )
        return True

    def validate_file_path(self, path: str) -> bool:
        """Refuse les chemins système dangereux."""
        dangerous_prefixes = [
            "C:\\Windows\\System32", "C:\\Windows\\System",
            "/etc/", "/bin/", "/sbin/", "/usr/bin/",
            "C:\\Program Files\\Common"
        ]
        for prefix in dangerous_prefixes:
            if path.lower().startswith(prefix.lower()):
                raise CommandBlockedError(f"Accès refusé : chemin système protégé.")
        return True


# ─────────────────────────────────────────────────────────────────────────────
# ApiKeyVault
# ─────────────────────────────────────────────────────────────────────────────
class ApiKeyVault:
    """
    Gestion sécurisée des clés API.
    Lit depuis les variables d'environnement (jamais en dur dans le code).
    """

    _KEYS = {
        "openai":       "OPENAI_API_KEY",
        "openweather":  "OPENWEATHER_API_KEY",
        "news":         "NEWS_API_KEY",
        "porcupine":    "PORCUPINE_ACCESS_KEY",
        "google":       "GOOGLE_API_KEY",
    }

    def get(self, service: str) -> Optional[str]:
        env_var = self._KEYS.get(service.lower())
        if not env_var:
            return None
        key = os.getenv(env_var, "").strip()
        return key or None

    def is_available(self, service: str) -> bool:
        return self.get(service) is not None

    def mask(self, key: str) -> str:
        """Masque une clé pour les logs (ex: sk-...xyz)."""
        if not key or len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

    def available_services(self) -> list:
        return [svc for svc in self._KEYS if self.is_available(svc)]


# ─────────────────────────────────────────────────────────────────────────────
# SecurityManager principal
# ─────────────────────────────────────────────────────────────────────────────
class SecurityManager:
    """
    Point d'entrée unique pour toute la sécurité.
    Intègre : permissions, validation, vault, audit.
    """

    def __init__(self):
        self._permissions: dict = {}
        self._confirmation_required: list = []
        self.validator = CommandValidator()
        self.vault     = ApiKeyVault()
        self.audit     = AuditLogger()
        self._load()
        logger.info("SecurityManager v2 initialisé.")
        logger.info(f"Services API disponibles : {self.vault.available_services()}")

    def _load(self) -> None:
        try:
            with open(PERMISSIONS_PATH, encoding="utf-8") as f:
                data = json.load(f)
            self._permissions          = {k: v for k, v in data.items() if k != "require_confirmation_for"}
            self._confirmation_required = data.get("require_confirmation_for", [])
        except FileNotFoundError:
            logger.warning("permissions.json introuvable — mode restrictif par défaut.")
        except Exception as e:
            logger.error(f"Erreur chargement permissions : {e}")

    # ── Permissions ──────────────────────────────────────────────────────────

    def is_allowed(self, action: str) -> bool:
        key = f"allow_{action}"
        allowed = self._permissions.get(key, False)
        if not allowed:
            self.audit.log(action, "DENIED")
        return allowed

    def require(self, action: str) -> None:
        if not self.is_allowed(action):
            self.audit.log(action, "BLOCKED", "permission manquante")
            raise PermissionDeniedError(action)
        self.audit.log(action, "ALLOWED")

    def needs_confirmation(self, action: str) -> bool:
        return action in self._confirmation_required

    # ── Validation ───────────────────────────────────────────────────────────

    def validate_command(self, text: str) -> bool:
        try:
            result = self.validator.validate_text(text)
            self.audit.log("validate_command", "PASSED", text[:50])
            return result
        except CommandBlockedError as e:
            self.audit.log("validate_command", "BLOCKED", str(e))
            raise

    def validate_app(self, app_name: str) -> bool:
        return self.validator.validate_app_name(app_name)

    # ── Décorateur ───────────────────────────────────────────────────────────

    def guard(self, action: str):
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                self.require(action)
                return func(*args, **kwargs)
            wrapper.__name__ = func.__name__
            return wrapper
        return decorator

    def reload(self) -> None:
        self._load()
        logger.info("Permissions rechargées.")
