"""
CHARAMOU AI - Agent Web
Recherche, extraction de contenu, navigation automatisée.
"""
from core.agents.base_agent import BaseAgent
from typing import Any, Dict, List, Optional


class WebAgent(BaseAgent):
    """
    Agent spécialisé dans la navigation et la recherche web.
    Capacités : recherche DuckDuckGo, extraction de contenu, résumé de page.
    """

    name        = "web_agent"
    description = "Recherche et extrait des informations sur le web."

    KEYWORDS = ["cherche", "recherche", "trouve", "google", "web", "site", "actualité", "news"]

    def can_handle(self, task: str, entities: dict) -> bool:
        task_lower = task.lower()
        return any(kw in task_lower for kw in self.KEYWORDS)

    def execute(self, task: str, entities: dict, context: Any = None) -> str:
        self._log_step(f"Analyse de la tâche : '{task}'")
        query = entities.get("raw_text", task)

        # Étape 1 : recherche
        self._log_step(f"Recherche : '{query}'")
        results = self._search(query)

        if not results:
            self._log_step("Aucun résultat — ouverture navigateur")
            self._open_browser(query)
            return f"J'ai ouvert une recherche pour « {query} » dans votre navigateur."

        # Étape 2 : résumé du premier résultat
        best = results[0]
        self._log_step(f"Résultat sélectionné : {best.get('title', '')[:40]}")

        response = f"Voici ce que j'ai trouvé pour « {query} » :\n{best['snippet'][:250]}"
        if best.get("url"):
            response += f"\nSource : {best['url']}"

        # Mémorisation si engine disponible
        if self.memory:
            self.memory.remember("web_searches", query[:50], best['snippet'][:100])

        return response

    def _search(self, query: str) -> List[Dict]:
        try:
            import requests
            params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1"}
            r = requests.get("https://api.duckduckgo.com/", params=params, timeout=5)
            data = r.json()
            results = []
            if data.get("AbstractText"):
                results.append({"title": data.get("Heading", ""), "snippet": data["AbstractText"], "url": data.get("AbstractURL", "")})
            for item in data.get("RelatedTopics", [])[:3]:
                if "Text" in item:
                    results.append({"title": item["Text"][:60], "snippet": item["Text"], "url": item.get("FirstURL", "")})
            return results
        except Exception as e:
            self._logger.warning(f"Recherche échouée : {e}")
            return []

    def _open_browser(self, query: str) -> None:
        import webbrowser, urllib.parse
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
