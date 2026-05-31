"""
CHARAMOU AI - Agent Système
Contrôle Windows : apps, volume, processus, notifications.
"""
import os
import platform
from core.agents.base_agent import BaseAgent
from typing import Any


class SystemAgent(BaseAgent):
    """
    Agent spécialisé dans le contrôle du système Windows.
    """

    name        = "system_agent"
    description = "Contrôle le système : apps, volume, processus."

    KEYWORDS = ["ouvre", "lance", "ferme", "volume", "son", "capture", "screenshot",
                "processus", "cpu", "mémoire", "batterie", "réseau", "wifi"]

    def can_handle(self, task: str, entities: dict) -> bool:
        return any(kw in task.lower() for kw in self.KEYWORDS)

    def execute(self, task: str, entities: dict, context: Any = None) -> str:
        task_lower = task.lower()

        if any(k in task_lower for k in ["cpu", "ram", "mémoire", "batterie", "état", "stats"]):
            return self._get_system_stats()
        elif "capture" in task_lower or "screenshot" in task_lower:
            return self._screenshot()
        elif any(k in task_lower for k in ["volume", "son", "silence", "muet"]):
            return self._handle_volume(task_lower)
        elif any(k in task_lower for k in ["ouvre", "lance"]):
            app = entities.get("app", "")
            return self._open_app(app, task)
        return "Commande système non reconnue."

    def _get_system_stats(self) -> str:
        try:
            import psutil
            cpu  = psutil.cpu_percent(interval=1)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            stats = [f"CPU : {cpu}%",
                     f"RAM : {ram.percent}% ({ram.used // 1e9:.1f} Go / {ram.total // 1e9:.1f} Go)",
                     f"Disque : {disk.percent}%"]
            bat = psutil.sensors_battery()
            if bat:
                stats.append(f"Batterie : {bat.percent:.0f}% ({'charge' if bat.power_plugged else 'décharge'})")
            return "État système : " + " | ".join(stats)
        except ImportError:
            return "psutil non installé."

    def _screenshot(self) -> str:
        try:
            import pyautogui
            from pathlib import Path
            from datetime import datetime
            d = Path.home() / "Pictures" / "CHARAMOU_Screenshots"
            d.mkdir(parents=True, exist_ok=True)
            f = d / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            pyautogui.screenshot().save(str(f))
            return f"Capture d'écran : {f.name}"
        except Exception as e:
            return f"Capture impossible : {e}"

    def _handle_volume(self, text: str) -> str:
        if "silence" in text or "muet" in text:
            return "Mise en silence. (Nécessite pywin32 sur Windows)"
        elif "monte" in text:
            try:
                import pyautogui
                [pyautogui.press("volumeup") for _ in range(5)]
                return "Volume augmenté."
            except Exception:
                return "Volume : pyautogui non disponible."
        elif "baisse" in text:
            try:
                import pyautogui
                [pyautogui.press("volumedown") for _ in range(5)]
                return "Volume diminué."
            except Exception:
                return "Volume : pyautogui non disponible."
        return "Précisez : monte, baisse ou silence."

    def _open_app(self, app_name: str, full_text: str) -> str:
        APP_MAP = {
            "word": "WINWORD.EXE", "excel": "EXCEL.EXE", "notepad": "notepad.exe",
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "calculatrice": "calc.exe", "explorer": "explorer.exe",
        }
        # Cherche dans le texte complet si app_name vide
        if not app_name:
            for key in APP_MAP:
                if key in full_text.lower():
                    app_name = key
                    break
        exe = APP_MAP.get(app_name.lower(), app_name)
        try:
            os.startfile(exe)
            return f"J'ouvre {app_name}."
        except Exception:
            return f"Impossible d'ouvrir '{app_name}'."
