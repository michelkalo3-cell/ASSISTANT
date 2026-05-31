"""
CHARAMOU AI - Launcher
Vérifie les dépendances, charge la configuration, prépare l'environnement.
"""
import sys
import os
import json
import importlib
import subprocess
from pathlib import Path


BASE_DIR = Path(__file__).parent
REQUIRED_DIRS = [
    "logs", "data/cache", "data/temp",
    "data/voices", "data/models", "database"
]
REQUIRED_PACKAGES = [
    "speechrecognition", "pyttsx3", "pyaudio",
    "openai", "requests", "sqlite3",
    "schedule", "python-dotenv", "keyboard",
    "pyautogui", "psutil"
]


def check_python_version():
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ requis.")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}")


def create_directories():
    for d in REQUIRED_DIRS:
        path = BASE_DIR / d
        path.mkdir(parents=True, exist_ok=True)
    print("✅ Répertoires vérifiés.")


def check_env_file():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        example = BASE_DIR / ".env.example"
        if example.exists():
            import shutil
            shutil.copy(example, env_path)
            print("⚠️  Fichier .env créé depuis .env.example — configurez vos clés API.")
        else:
            print("⚠️  Aucun fichier .env trouvé.")
    else:
        print("✅ Fichier .env présent.")


def check_config():
    settings_path = BASE_DIR / "config" / "settings.json"
    if not settings_path.exists():
        print("❌ config/settings.json manquant.")
        sys.exit(1)
    with open(settings_path) as f:
        config = json.load(f)
    print(f"✅ Configuration chargée : assistant '{config.get('assistant_name', 'CHARAMOU')}'")
    return config


def load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
        print("✅ Variables d'environnement chargées.")
    except ImportError:
        print("⚠️  python-dotenv non installé — variables .env non chargées.")


def run():
    print("=" * 50)
    print("   CHARAMOU AI - Démarrage du launcher")
    print("=" * 50)
    check_python_version()
    create_directories()
    load_env()
    check_env_file()
    config = check_config()
    print("=" * 50)
    print("🚀 Lancement de CHARAMOU AI...")
    print("=" * 50)

    # Import différé pour éviter les erreurs avant vérification
    from core.engine import AssistantEngine
    engine = AssistantEngine()
    engine.start()


if __name__ == "__main__":
    run()
