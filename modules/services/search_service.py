"""
CHARAMOU AI - Service de recherche web
Via DuckDuckGo (sans clé API requise) + fallback navigateur.
"""
import re
import webbrowser
import urllib.parse
import requests
from typing import List, Dict
from core.logger import setup_logger

logger = setup_logger("SearchService")


class SearchService:
    """
    Effectue des recherches web.
    Méthode principale : DuckDuckGo Instant Answer API (gratuit, sans clé).
    Fallback : ouvre le navigateur.
    """

    DDG_API = "https://api.duckduckgo.com/"

    def __init__(self):
        logger.info("SearchService initialisé.")

    def search(self, query: str) -> List[Dict[str, str]]:
        """Retourne une liste de résultats {title, url, snippet}."""
        try:
            params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
            r = requests.get(self.DDG_API, params=params, timeout=5)
            r.raise_for_status()
            data = r.json()

            results = []

            # Abstract (réponse directe)
            if data.get("AbstractText"):
                results.append({
                    "title":   data.get("Heading", query),
                    "url":     data.get("AbstractURL", ""),
                    "snippet": data["AbstractText"][:300]
                })

            # Résultats liés
            for item in data.get("RelatedTopics", [])[:5]:
                if "Text" in item and "FirstURL" in item:
                    results.append({
                        "title":   item["Text"][:80],
                        "url":     item["FirstURL"],
                        "snippet": item["Text"]
                    })

            return results

        except Exception as e:
            logger.error(f"Erreur recherche : {e}")
            return []

    def open_in_browser(self, query: str) -> None:
        """Ouvre la recherche dans le navigateur par défaut."""
        import webbrowser
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)
        logger.info(f"Recherche ouverte dans le navigateur : '{query}'")

    def handle(self, entities: dict = None, context=None) -> str:
        """Handler pour le TaskRouter."""
        entities = entities or {}
        raw_text = entities.get("raw_text", "")

        # Nettoie la commande pour isoler la requête
        query = re.sub(
            r'\b(cherche|recherche|google|trouve|qu\'est-ce que|c\'est quoi)\b',
            '', raw_text, flags=re.IGNORECASE
        ).strip()

        if not query:
            return "Que souhaitez-vous rechercher ?"

        results = self.search(query)

        if results:
            first = results[0]
            response = f"Voici ce que j'ai trouvé pour « {query} » : {first['snippet'][:200]}"
            if first.get("url"):
                response += f"\n  Source : {first['url']}"
        else:
            self.open_in_browser(query)
            response = f"J'ai ouvert une recherche pour « {query} » dans votre navigateur."

        return response
