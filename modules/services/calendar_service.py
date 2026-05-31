"""
CHARAMOU AI - Service de calendrier
Intégration Google Calendar (OAuth2) + calendrier local SQLite.
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from core.logger import setup_logger

logger = setup_logger("CalendarService")


class CalendarService:
    """
    Gère le calendrier de l'utilisateur.
    Supports : Google Calendar (si credentials.json), calendrier local.
    """

    def __init__(self):
        self._google_service = None
        self._try_init_google()
        logger.info("CalendarService initialisé.")

    def _try_init_google(self) -> None:
        """Tente d'initialiser Google Calendar API."""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            from pathlib import Path

            SCOPES     = ["https://www.googleapis.com/auth/calendar.readonly"]
            CREDS_PATH = Path(__file__).parent.parent.parent / "config" / "credentials.json"
            TOKEN_PATH = Path(__file__).parent.parent.parent / "data" / "token.pickle"

            if not CREDS_PATH.exists():
                logger.debug("credentials.json absent — Google Calendar désactivé.")
                return

            creds = None
            if TOKEN_PATH.exists():
                with open(TOKEN_PATH, "rb") as f:
                    creds = pickle.load(f)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
                    creds = flow.run_local_server(port=0)
                with open(TOKEN_PATH, "wb") as f:
                    pickle.dump(creds, f)

            self._google_service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar connecté.")

        except Exception as e:
            logger.debug(f"Google Calendar non disponible : {e}")

    def get_today_events(self) -> List[Dict[str, Any]]:
        """Retourne les événements d'aujourd'hui."""
        if self._google_service:
            return self._get_google_events(days=0)
        return self._get_local_events()

    def get_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """Retourne les événements des N prochains jours."""
        if self._google_service:
            return self._get_google_events(days=days)
        return []

    def _get_google_events(self, days: int = 0) -> List[Dict[str, Any]]:
        try:
            now   = datetime.utcnow()
            start = now.isoformat() + "Z"
            end   = (now + timedelta(days=max(days, 1))).isoformat() + "Z"

            result = self._google_service.events().list(
                calendarId="primary",
                timeMin=start, timeMax=end,
                maxResults=10, singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = []
            for item in result.get("items", []):
                start_raw = item["start"].get("dateTime", item["start"].get("date", ""))
                events.append({
                    "title":   item.get("summary", "Sans titre"),
                    "start":   start_raw,
                    "location": item.get("location", ""),
                })
            return events
        except Exception as e:
            logger.error(f"Erreur Google Calendar : {e}")
            return []

    def _get_local_events(self) -> List[Dict[str, Any]]:
        """Événements locaux depuis la mémoire SQLite."""
        return []  # À enrichir avec MemoryManager

    def handle(self, entities: dict = None, context=None) -> str:
        """Handler pour le TaskRouter."""
        events = self.get_today_events()
        if not events:
            return "Vous n'avez aucun événement prévu aujourd'hui."

        lines = []
        for e in events:
            start = e.get("start", "")
            if "T" in start:
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    start = dt.strftime("%H:%M")
                except Exception:
                    pass
            lines.append(f"{start} — {e['title']}")

        result = "Vos événements du jour :\n" + "\n".join(f"  • {l}" for l in lines)
        return result
