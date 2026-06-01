"""
CHARAMOU AI - Contrôleur système
Volume, luminosité, captures d'écran, ouverture d'applications, arrêt.
"""
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from core.logger import setup_logger
from core.exceptions import AutomationError, ApplicationNotFoundError

logger = setup_logger("SystemController")

SCREENSHOTS_DIR = Path.home() / "Pictures" / "CHARAMOU_Screenshots"

# Table des applications Windows
APP_MAP = {
    "word":        "WINWORD.EXE",
    "excel":       "EXCEL.EXE",
    "powerpoint":  "POWERPNT.EXE",
    "outlook":     "OUTLOOK.EXE",
    "notepad":     "notepad.exe",
    "calculatrice":"calc.exe",
    "explorer":    "explorer.exe",
    "chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":     r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":        "msedge.exe",
    "teams":       "Teams.exe",
    "discord":     "Discord.exe",
    "vlc":         r"C:\Program Files\VideoLAN\VLC\vlc.exe",
}


class SystemController:
    """Contrôle les éléments système de Windows."""

    def __init__(self, security=None):
        self.security = security
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("SystemController initialisé.")

    # ────────────────────────────────────────────────────────────────────────
    # Ouverture d'applications
    # ────────────────────────────────────────────────────────────────────────

    def handle_open(self, entities: dict = None, context=None) -> str:
        entities = entities or {}
        app_name = entities.get("app") or self._extract_app(entities.get("raw_text", ""))

        if not app_name:
            return "Quelle application souhaitez-vous ouvrir ?"

        return self.open_application(app_name)

    def handle_status(self, entities: dict = None, context=None) -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            parts = [
                f"CPU : {cpu:.0f}%",
                f"RAM : {ram.percent:.0f}%",
                f"Disque : {disk.percent:.0f}%",
            ]
            battery = psutil.sensors_battery()
            if battery:
                state = "en charge" if battery.power_plugged else "sur batterie"
                parts.append(f"Batterie : {battery.percent:.0f}% ({state})")
            return "État système : " + " | ".join(parts)
        except ImportError:
            return "psutil n'est pas installé. Exécutez : pip install psutil"
        except Exception as e:
            logger.error(f"Erreur état système : {e}")
            return "Impossible de lire l'état du système."

    def open_application(self, app_name: str) -> str:
        app_lower = app_name.lower().strip()
        executable = APP_MAP.get(app_lower, app_lower)

        try:
            if self.security:
                self.security.validate_app(app_lower)
            if platform.system() == "Windows":
                os.startfile(executable)
            else:
                subprocess.Popen(["xdg-open", executable])
            logger.info(f"Application lancée : {executable}")
            return f"J'ouvre {app_name}."
        except FileNotFoundError:
            logger.warning(f"Application introuvable : {executable}")
            return f"Je n'ai pas trouvé l'application « {app_name} »."
        except Exception as e:
            logger.error(f"Erreur lancement {app_name} : {e}")
            return f"Impossible d'ouvrir {app_name}."

    # ────────────────────────────────────────────────────────────────────────
    # Volume
    # ────────────────────────────────────────────────────────────────────────

    def handle_volume(self, entities: dict = None, context=None) -> str:
        if self.security:
            self.security.require("system_volume")

        entities = entities or {}
        raw = entities.get("raw_text", "").lower()

        if "silence" in raw or "muet" in raw:
            self._set_mute(True)
            return "Mise en silence."
        elif "monte" in raw or "augmente" in raw:
            self._adjust_volume(+10)
            return "Volume augmenté."
        elif "baisse" in raw or "diminue" in raw:
            self._adjust_volume(-10)
            return "Volume diminué."
        else:
            numbers = entities.get("numbers", [])
            if numbers:
                level = min(100, max(0, numbers[0]))
                self._set_volume(level)
                return f"Volume réglé à {level}%."
        return "Commande volume non reconnue."

    def _set_mute(self, mute: bool) -> None:
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1 if mute else 0, None)
        except Exception:
            logger.debug("pycaw non disponible pour le volume.")

    def _adjust_volume(self, delta: int) -> None:
        try:
            if platform.system() == "Windows":
                import pyautogui
                key = "volumeup" if delta > 0 else "volumedown"
                for _ in range(abs(delta) // 2):
                    pyautogui.press(key)
        except Exception as e:
            logger.debug(f"Ajustement volume : {e}")

    def _set_volume(self, level: int) -> None:
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["nircmd.exe", "setsysvolume", str(int(level * 655.35))],
                    capture_output=True
                )
        except Exception as e:
            logger.debug(f"Set volume : {e}")

    # ────────────────────────────────────────────────────────────────────────
    # Capture d'écran
    # ────────────────────────────────────────────────────────────────────────

    def handle_screenshot(self, entities: dict = None, context=None) -> str:
        if self.security:
            self.security.require("screenshot")
        return self.take_screenshot()

    def take_screenshot(self) -> str:
        try:
            import pyautogui
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = SCREENSHOTS_DIR / filename
            screenshot = pyautogui.screenshot()
            screenshot.save(str(path))
            logger.info(f"Capture d'écran : {path}")
            return f"Capture d'écran enregistrée : {filename}"
        except Exception as e:
            logger.error(f"Erreur screenshot : {e}")
            return "Impossible de prendre une capture d'écran."

    # ────────────────────────────────────────────────────────────────────────
    # Arrêt système
    # ────────────────────────────────────────────────────────────────────────

    def handle_shutdown(self, entities: dict = None, context=None) -> str:
        if self.security:
            self.security.require("shutdown")
        if platform.system() == "Windows":
            os.system("shutdown /s /t 60")
            return "L'ordinateur s'éteindra dans 60 secondes. Tapez 'shutdown /a' pour annuler."
        return "Arrêt non disponible sur ce système."

    # ────────────────────────────────────────────────────────────────────────
    # Utilitaires
    # ────────────────────────────────────────────────────────────────────────

    def _extract_app(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for app_name in APP_MAP:
            if app_name in text_lower:
                return app_name
        return None
