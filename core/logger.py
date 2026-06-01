"""
CHARAMOU AI - Système de logging centralisé v2
Un fichier de log par domaine + rotation automatique.
"""
import logging
import logging.handlers
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
try:
    LOGS_DIR.mkdir(exist_ok=True)
except OSError:
    pass

_LOGGERS: dict = {}

_DOMAIN_FILES = {
    "voice":    "voice.log",
    "ai":       "ai.log",
    "system":   "system.log",
    "security": "security.log",
    "errors":   "errors.log",
    "activity": "activity.log",
}

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    if name in _LOGGERS:
        return _LOGGERS[name]

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)

    if logger.handlers:
        _LOGGERS[name] = logger
        return logger

    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    def make_handler(filename: str, level=logging.DEBUG):
        path = LOGS_DIR / filename
        try:
            with open(path, "a", encoding="utf-8"):
                pass
            h = logging.handlers.RotatingFileHandler(
                path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8"
            )
        except OSError:
            return None
        h.setLevel(level)
        h.setFormatter(fmt)
        return h

    # Console
    ch = logging.StreamHandler()
    ch.setLevel(numeric_level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Fichier activité global
    activity_handler = make_handler("activity.log", logging.INFO)
    if activity_handler:
        logger.addHandler(activity_handler)

    # Fichier erreurs global
    error_handler = make_handler("errors.log", logging.ERROR)
    if error_handler:
        logger.addHandler(error_handler)

    # Fichier domaine spécifique
    name_lower = name.lower()
    for domain, fname in _DOMAIN_FILES.items():
        if domain in name_lower:
            domain_handler = make_handler(fname, logging.DEBUG)
            if domain_handler:
                logger.addHandler(domain_handler)
            break

    _LOGGERS[name] = logger
    return logger

logger = setup_logger("CHARAMOU")
