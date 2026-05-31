"""
CHARAMOU AI - Contrôleur navigateur
Ouvre des sites, effectue des recherches, gère les onglets.
"""
import re
import webbrowser
import urllib.parse
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("BrowserController")

# Raccourcis de sites populaires
SITE_MAP = {
    "youtube":   "https://www.youtube.com",
    "google":    "https://www.google.com",
    "github":    "https://www.github.com",
    "gmail":     "https://mail.google.com",
    "facebook":  "https://www.facebook.com",
    "twitter":   "https://www.twitter.com",
    "linkedin":  "https://www.linkedin.com",
    "wikipedia": "https://fr.wikipedia.org",
    "amazon":    "https://www.amazon.fr",
    "netflix":   "https://www.netflix.com",
    "chatgpt":   "https://chat.openai.com",
    "météo":     "https://weather.com/fr-FR",
}


class BrowserController:
    """
    Contrôle le navigateur par défaut du système.
    """

    def __init__(self, security=None):
        self.security = security
        logger.info("BrowserController initialisé.")

    def handle(self, entities: dict = None, context=None) -> str:
        """Handler pour le TaskRouter."""
        if self.security:
            self.security.require("browser_control")

        entities = entities or {}
        raw_text = entities.get("raw_text", "")
        return self.process_command(raw_text)

    def process_command(self, text: str) -> str:
        text_lower = text.lower()

        # Ouverture d'un site nommé
        for site, url in SITE_MAP.items():
            if site in text_lower:
                self.open_url(url)
                return f"J'ouvre {site}."

        # URL directe
        url_match = re.search(r'https?://\S+', text)
        if url_match:
            self.open_url(url_match.group(0))
            return f"J'ouvre la page."

        # Recherche
        query = self._extract_search_query(text)
        if query:
            self.search_google(query)
            return f"Je recherche « {query} » dans votre navigateur."

        # Par défaut : ouvrir le navigateur
        webbrowser.open("https://www.google.com")
        return "J'ouvre votre navigateur."

    def open_url(self, url: str) -> None:
        webbrowser.open(url)
        logger.info(f"URL ouverte : {url}")

    def search_google(self, query: str) -> None:
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)
        logger.info(f"Recherche Google : '{query}'")

    def search_youtube(self, query: str) -> None:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)
        logger.info(f"Recherche YouTube : '{query}'")

    def _extract_search_query(self, text: str) -> Optional[str]:
        patterns = [
            r'(?:cherche|recherche|google|trouve)\s+(.+?)(?:\s+sur\s+\w+)?$',
            r'ouvre\s+(.+)',
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None
