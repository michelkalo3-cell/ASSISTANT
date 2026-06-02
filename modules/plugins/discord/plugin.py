"""
CHARAMOU AI - Plugin Discord
Envoi de messages et notifications sur Discord via Webhook ou Bot.
"""
import os
import requests
from core.plugin_manager import BasePlugin
from core.logger import setup_logger

logger = setup_logger("DiscordPlugin")

class Plugin(BasePlugin):
    name = "discord"
    description = "Envoie des notifications sur Discord."

    def setup(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not self.webhook_url:
            logger.warning("DISCORD_WEBHOOK_URL manquant dans le .env")
            return False
        return True

    def register_routes(self, router):
        router.register("SEND_DISCORD", self.handle_send)

    def handle_send(self, entities, context):
        msg = entities.get("raw_text", "Notification de CHARAMOU AI")
        try:
            r = requests.post(self.webhook_url, json={"content": msg})
            if r.status_code == 204:
                return "Message envoyé sur Discord."
            return f"Erreur Discord (code {r.status_code})"
        except Exception as e:
            return f"Erreur d'envoi Discord : {e}"
