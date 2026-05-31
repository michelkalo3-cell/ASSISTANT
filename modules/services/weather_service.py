"""
CHARAMOU AI - Service météo
Via OpenWeatherMap API (gratuit).
"""
import os
import requests
from typing import Dict, Any, Optional
from modules.nlp.response_generator import ResponseGenerator
from core.logger import setup_logger
from core.exceptions import WeatherServiceError

logger = setup_logger("WeatherService")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_CITY = "Paris"


class WeatherService:
    """
    Récupère la météo via OpenWeatherMap.
    Clé API : variable d'environnement OPENWEATHER_API_KEY.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "")
        if not self.api_key:
            logger.warning("OPENWEATHER_API_KEY non défini — météo désactivée.")
        else:
            logger.info("WeatherService initialisé.")

    def get_weather(self, city: str = DEFAULT_CITY) -> Dict[str, Any]:
        """Retourne les données météo pour une ville."""
        if not self.api_key:
            return {"error": "Clé API météo manquante."}

        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "lang": "fr"
        }
        try:
            response = requests.get(BASE_URL, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            return {
                "city":        data["name"],
                "country":     data["sys"]["country"],
                "description": data["weather"][0]["description"],
                "temp":        data["main"]["temp"],
                "feels_like":  data["main"]["feels_like"],
                "humidity":    data["main"]["humidity"],
                "wind_speed":  data["wind"]["speed"],
                "icon":        data["weather"][0]["icon"]
            }
        except requests.exceptions.ConnectionError:
            logger.error("Pas de connexion internet pour la météo.")
            return {"error": "Connexion impossible."}
        except Exception as e:
            logger.error(f"Erreur météo : {e}")
            return {"error": str(e)}

    def handle(self, entities: dict = None, context=None) -> str:
        """Handler pour le TaskRouter."""
        entities = entities or {}
        city = entities.get("city", DEFAULT_CITY)
        data = self.get_weather(city)

        if "error" in data:
            return f"Désolé, je ne peux pas récupérer la météo : {data['error']}"

        return ResponseGenerator.weather(
            city=data["city"],
            description=data["description"],
            temp=data["temp"],
            humidity=data["humidity"]
        )
