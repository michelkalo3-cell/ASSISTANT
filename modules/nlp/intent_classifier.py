"""
CHARAMOU AI - Classificateur NLP v2
Détection d'intentions + extraction d'entités + résolution pronominale.
"""
import json
import re
from pathlib import Path
from typing import Tuple, Dict, Any, List
from core.logger import setup_logger

logger = setup_logger("IntentClassifier")
COMMANDS_PATH = Path(__file__).parent.parent.parent / "config" / "commands.json"


class IntentClassifier:
    """
    Classificateur basé sur des règles pondérées.
    Gère la résolution de contexte (pronoms, anaphore).
    """

    def __init__(self):
        self._commands       = self._load_commands()
        self._entity_extractor = EntityExtractor()
        self._last_intent    = None
        self._last_entities  = {}
        logger.info(f"IntentClassifier v2 : {len(self._commands)} intentions.")

    def _load_commands(self) -> dict:
        try:
            with open(COMMANDS_PATH, encoding="utf-8") as f:
                return json.load(f).get("commands", {})
        except Exception as e:
            logger.warning(f"commands.json non chargé : {e}")
            return {}

    def classify(self, text: str) -> Tuple[str, Dict[str, Any]]:
        text_lower = text.lower().strip()

        # Résolution pronominale
        text_resolved = self._resolve_pronouns(text_lower)

        # Détection d'intention
        best_intent, best_score = "CONVERSATION", 0
        for intent, data in self._commands.items():
            score = self._score(text_resolved, data.get("keywords", []))
            if score > best_score:
                best_score  = score
                best_intent = intent

        entities = self._entity_extractor.extract(text, best_intent)

        # Mémorisation du contexte pour la résolution future
        self._last_intent   = best_intent
        self._last_entities = entities

        logger.debug(f"Intent: {best_intent} (score={best_score})")
        return best_intent, entities

    def _resolve_pronouns(self, text: str) -> str:
        """
        Résout les pronoms et références anaphoriques.
        Ex: "enregistre-la" → "enregistre le document"
        """
        replacements = {
            r'\b(la|le|les|l\'|l)\b\s*(enregistr|sauvegardr|fermer|ouvrrir)':
                lambda m: f"le document {m.group(2)}",
            r'\benregistre-la\b': "enregistre le document",
            r'\bferme-le\b':      "ferme le fichier",
            r'\bouvre-le\b':      "ouvre le fichier",
        }
        for pattern, replacement in replacements.items():
            if callable(replacement):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            else:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def _score(self, text: str, keywords: list) -> int:
        score = 0
        for kw in keywords:
            kw_lower = kw.lower()
            if re.search(r'\b' + re.escape(kw_lower) + r'\b', text):
                score += 2
            elif kw_lower in text:
                score += 1
        return score


class EntityExtractor:
    _TIME_PATTERN  = re.compile(r'\b(\d{1,2})[h:\s](\d{0,2})\s*(am|pm)?\b', re.IGNORECASE)
    _DATE_PATTERN  = re.compile(
        r'\b(aujourd\'hui|demain|après-demain|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche'
        r'|\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?)\b', re.IGNORECASE)
    _NUMBER_PATTERN = re.compile(r'\b(\d+)\b')
    _CITY_PATTERN   = re.compile(
        r'\b(paris|lyon|marseille|bordeaux|nice|toulouse|lille|nantes|'
        r'montpellier|strasbourg|rennes|grenoble|london|new\s?york|berlin|madrid)\b', re.IGNORECASE)
    _APP_PATTERN    = re.compile(
        r'\b(word|excel|powerpoint|chrome|firefox|edge|notepad|calculatrice|'
        r'explorer|outlook|teams|zoom|discord|spotify|vlc|paint|code)\b', re.IGNORECASE)
    _URL_PATTERN    = re.compile(r'https?://\S+')
    _LANG_PATTERN   = re.compile(
        r'\b(en\s+anglais|en\s+français|en\s+espagnol|en\s+arabe|en\s+allemand|en\s+italien)\b',
        re.IGNORECASE)
    _DURATION_PATTERN = re.compile(
        r'\b(\d+)\s*(minute|min|heure|h|seconde|sec|jour|semaine)\b', re.IGNORECASE)

    def extract(self, text: str, intent: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {"raw_text": text}

        t = self._TIME_PATTERN.search(text)
        if t:
            entities["time"] = f"{t.group(1)}:{(t.group(2) or '00').zfill(2)}"

        d = self._DATE_PATTERN.search(text)
        if d:
            entities["date"] = d.group(1).lower()

        nums = self._NUMBER_PATTERN.findall(text)
        if nums:
            entities["numbers"] = [int(n) for n in nums]

        if intent == "GET_WEATHER":
            c = self._CITY_PATTERN.search(text)
            if c:
                entities["city"] = c.group(1).capitalize()

        if intent in ("OPEN_APPLICATION", "CLOSE_APPLICATION"):
            a = self._APP_PATTERN.search(text)
            if a:
                entities["app"] = a.group(1).lower()

        url = self._URL_PATTERN.search(text)
        if url:
            entities["url"] = url.group(0)

        lang = self._LANG_PATTERN.search(text)
        if lang:
            entities["target_language"] = lang.group(1)

        dur = self._DURATION_PATTERN.search(text)
        if dur:
            entities["duration"] = {"value": int(dur.group(1)), "unit": dur.group(2)}

        return entities
