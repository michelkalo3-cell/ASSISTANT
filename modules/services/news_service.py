"""
CHARAMOU AI - Service actualités
Via NewsAPI (clé gratuite) + RSS fallback.
"""
import os
from typing import List, Dict
from core.logger import setup_logger

logger = setup_logger("NewsService")

if "requests" not in globals():
    try:
        import requests
    except ImportError:
        class _MissingRequests:
            def get(self, *args, **kwargs):
                raise RuntimeError("requests non installé")

        requests = _MissingRequests()


class NewsService:

    def __init__(self):
        self.api_key = os.getenv("NEWS_API_KEY", "")
        logger.info("NewsService initialisé.")

    def get_headlines(self, country: str = "fr", category: str = "general", limit: int = 5) -> List[Dict]:
        if self.api_key:
            return self._newsapi(country, category, limit)
        return self._rss_fallback(limit)

    def _newsapi(self, country: str, category: str, limit: int) -> List[Dict]:
        try:
            url    = "https://newsapi.org/v2/top-headlines"
            params = {"country": country, "category": category,
                      "pageSize": limit, "apiKey": self.api_key}
            r    = requests.get(url, params=params, timeout=5)
            data = r.json()
            return [
                {"title": a["title"], "source": a["source"]["name"],
                 "url": a["url"], "description": a.get("description", "")}
                for a in data.get("articles", [])[:limit]
            ]
        except Exception as e:
            logger.error(f"NewsAPI : {e}")
            return []

    def _rss_fallback(self, limit: int) -> List[Dict]:
        """Lit le RSS Le Monde sans clé API."""
        try:
            import xml.etree.ElementTree as ET
            r = requests.get("https://www.lemonde.fr/rss/une.xml", timeout=5)
            root = ET.fromstring(r.content)
            articles = []
            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title", "")
                link  = item.findtext("link", "")
                desc  = item.findtext("description", "")
                if title:
                    articles.append({"title": title, "source": "Le Monde",
                                     "url": link, "description": desc[:100]})
            return articles
        except Exception as e:
            logger.warning(f"RSS fallback : {e}")
            return []

    def handle(self, entities: dict = None, context=None) -> str:
        articles = self.get_headlines()
        if not articles:
            return "Impossible de récupérer les actualités pour le moment."
        lines = [f"• {a['title']} ({a['source']})" for a in articles]
        return "Actualités du jour :\n" + "\n".join(lines)
