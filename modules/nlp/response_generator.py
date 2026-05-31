"""
CHARAMOU AI - Générateur de réponses
Construit des réponses naturelles en français.
"""
import random
from datetime import datetime
from typing import Optional
from core.logger import setup_logger

logger = setup_logger("ResponseGenerator")


class ResponseGenerator:
    """
    Génère des réponses contextuelles et naturelles.
    Utilisé par les services pour formater leurs résultats.
    """

    # Formules de transition
    _CONFIRMATIONS = [
        "Très bien,", "D'accord,", "Bien sûr,", "Entendu,", "Parfait,"
    ]
    _ERRORS = [
        "Désolé, je n'ai pas pu effectuer cette action.",
        "Une erreur est survenue. Voulez-vous réessayer ?",
        "Je n'ai pas réussi à traiter cette demande.",
    ]
    _UNKNOWNS = [
        "Je ne suis pas sûr de comprendre. Pouvez-vous reformuler ?",
        "Hmm, je n'ai pas bien saisi. Pouvez-vous préciser ?",
        "Je n'ai pas compris. Pouvez-vous répéter autrement ?",
    ]

    @classmethod
    def confirmation(cls, action: str) -> str:
        prefix = random.choice(cls._CONFIRMATIONS)
        return f"{prefix} {action}."

    @classmethod
    def error(cls, detail: str = "") -> str:
        base = random.choice(cls._ERRORS)
        return f"{base} {detail}".strip()

    @classmethod
    def unknown(cls) -> str:
        return random.choice(cls._UNKNOWNS)

    @classmethod
    def weather(cls, city: str, description: str, temp: float, humidity: int) -> str:
        return (
            f"À {city}, il fait actuellement {description}. "
            f"La température est de {temp:.0f}°C avec {humidity}% d'humidité."
        )

    @classmethod
    def reminder_set(cls, title: str, time_str: str) -> str:
        return f"Rappel enregistré : « {title} » pour {time_str}."

    @classmethod
    def greeting(cls, name: str = "CHARAMOU", user: str = "") -> str:
        hour = datetime.now().hour
        if hour < 12:
            moment = "bonjour"
        elif hour < 18:
            moment = "bon après-midi"
        else:
            moment = "bonsoir"

        if user:
            return f"{moment.capitalize()}, {user} ! Je suis {name}. Comment puis-je vous aider ?"
        return f"{moment.capitalize()} ! Je suis {name}. Comment puis-je vous aider ?"

    @classmethod
    def list_items(cls, title: str, items: list) -> str:
        if not items:
            return f"Je n'ai trouvé aucun élément pour : {title}."
        lines = "\n".join(f"  • {item}" for item in items)
        return f"{title} :\n{lines}"

    @classmethod
    def time_response(cls) -> str:
        now = datetime.now()
        return f"Il est {now.strftime('%H heures %M')}."

    @classmethod
    def date_response(cls) -> str:
        now = datetime.now()
        days_fr = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
        months_fr = [
            "janvier","février","mars","avril","mai","juin",
            "juillet","août","septembre","octobre","novembre","décembre"
        ]
        day_name = days_fr[now.weekday()]
        month_name = months_fr[now.month - 1]
        return f"Nous sommes {day_name} {now.day} {month_name} {now.year}."
