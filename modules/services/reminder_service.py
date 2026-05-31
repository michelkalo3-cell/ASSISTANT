"""
CHARAMOU AI - Service de rappels
Crée et gère les rappels avec le Scheduler et la MemoryManager.
"""
import re
from datetime import datetime, timedelta
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("ReminderService")


class ReminderService:
    """
    Crée des rappels à partir de commandes en langage naturel.
    Exemples :
      "rappelle-moi de prendre mes médicaments à 8h"
      "rappel réunion demain à 14h30"
    """

    def __init__(self, scheduler=None, memory=None):
        self.scheduler = scheduler
        self.memory    = memory
        logger.info("ReminderService initialisé.")

    def handle(self, entities: dict = None, context=None) -> str:
        entities = entities or {}
        raw_text = entities.get("raw_text", "")
        time_str = entities.get("time")
        date_str = entities.get("date")

        # Extraction du titre du rappel
        title = self._extract_title(raw_text)
        due_time = self._parse_datetime(date_str, time_str)

        if not due_time:
            return "Je n'ai pas compris l'heure du rappel. Précisez l'heure, par exemple : « rappelle-moi à 15h30 »."

        # Sauvegarde en mémoire
        if self.memory:
            reminder_id = self.memory.add_reminder(title, due_time)
            logger.info(f"Rappel #{reminder_id} créé : '{title}' à {due_time}")

        # Planification dans le scheduler
        if self.scheduler:
            delay = (due_time - datetime.now()).total_seconds()
            if delay > 0:
                self.scheduler.add_in(
                    name=f"reminder_{title[:20]}",
                    callback=self._fire_reminder,
                    seconds=delay,
                    title=title
                )

        time_formatted = due_time.strftime("%H h %M le %d/%m")
        return f"Rappel enregistré : « {title} » pour {time_formatted}."

    def _extract_title(self, text: str) -> str:
        """Extrait le sujet du rappel depuis le texte brut."""
        text = re.sub(
            r'\b(rappelle.?moi|rappel|alarme|souviens.?moi)\b',
            '', text, flags=re.IGNORECASE
        ).strip()
        # Retire les indications temporelles
        text = re.sub(r'\b(à|demain|aujourd\'hui|lundi|mardi|mercredi|jeudi|vendredi)\b',
                      '', text, flags=re.IGNORECASE)
        text = re.sub(r'\b\d{1,2}[h:]\d{0,2}\b', '', text).strip(' ,.')
        return text or "Rappel sans titre"

    def _parse_datetime(self, date_str: Optional[str], time_str: Optional[str]) -> Optional[datetime]:
        """Convertit date et heure en objet datetime."""
        now = datetime.now()

        # Base date
        base_date = now.date()
        if date_str:
            date_lower = date_str.lower()
            if "demain" in date_lower:
                base_date = (now + timedelta(days=1)).date()
            elif "lundi" in date_lower:
                base_date = self._next_weekday(now, 0)
            elif "mardi" in date_lower:
                base_date = self._next_weekday(now, 1)
            elif "mercredi" in date_lower:
                base_date = self._next_weekday(now, 2)
            elif "jeudi" in date_lower:
                base_date = self._next_weekday(now, 3)
            elif "vendredi" in date_lower:
                base_date = self._next_weekday(now, 4)

        # Heure
        if time_str:
            match = re.match(r'(\d{1,2}):(\d{2})', time_str)
            if match:
                hour, minute = int(match.group(1)), int(match.group(2))
                dt = datetime.combine(base_date, datetime.min.time()).replace(
                    hour=hour, minute=minute, second=0
                )
                if dt < now:
                    dt += timedelta(days=1)
                return dt

        return None

    def _next_weekday(self, now: datetime, weekday: int):
        days_ahead = weekday - now.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (now + timedelta(days=days_ahead)).date()

    def _fire_reminder(self, title: str) -> None:
        """Déclenchement du rappel (notification)."""
        logger.info(f"🔔 Rappel déclenché : {title}")
        try:
            import platform
            if platform.system() == "Windows":
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast("CHARAMOU - Rappel", title, duration=10)
            else:
                print(f"\n🔔 RAPPEL : {title}")
        except Exception:
            print(f"\n🔔 RAPPEL : {title}")
