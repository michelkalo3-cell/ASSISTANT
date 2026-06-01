"""
CHARAMOU AI - Service de traduction multilingue
Via MyMemory API (gratuit, sans clé) + googletrans.
"""
import re
from core.logger import setup_logger

logger = setup_logger("TranslationService")

if "requests" not in globals():
    try:
        import requests
    except ImportError:
        class _MissingRequests:
            def get(self, *args, **kwargs):
                raise RuntimeError("requests non installé")

        requests = _MissingRequests()

LANG_MAP = {
    "anglais":   "en", "français": "fr", "espagnol": "es",
    "arabe":     "ar", "allemand": "de", "italien":  "it",
    "portugais": "pt", "chinois":  "zh", "japonais": "ja",
    "russe":     "ru"
}


class TranslationService:

    def translate(self, text: str, target_lang: str, source_lang: str = "fr") -> str:
        lang_code = LANG_MAP.get(target_lang.lower().replace("en ", ""), target_lang[:2])
        try:
            url    = "https://api.mymemory.translated.net/get"
            params = {"q": text, "langpair": f"{source_lang}|{lang_code}"}
            r      = requests.get(url, params=params, timeout=5)
            data   = r.json()
            translated = data["responseData"]["translatedText"]
            logger.info(f"Traduction : '{text[:30]}' → {lang_code} : '{translated[:30]}'")
            return translated
        except Exception as e:
            logger.error(f"Traduction échouée : {e}")
            return f"[Traduction indisponible : {e}]"

    def detect_language(self, text: str) -> str:
        """Détecte la langue d'un texte."""
        try:
            from langdetect import detect
            lang = detect(text)
            logger.debug(f"Langue détectée : {lang}")
            return lang
        except ImportError:
            # Heuristique simple
            if any(c in text for c in "éèêëàâùûîïô"):
                return "fr"
            return "en"
        except Exception:
            return "unknown"

    def handle(self, entities: dict = None, context=None) -> str:
        entities    = entities or {}
        raw_text    = entities.get("raw_text", "")
        target_lang = entities.get("target_language", "anglais")

        # Extrait le texte à traduire
        text_to_translate = re.sub(
            r'\b(traduis|traduction|en\s+\w+)\b', '', raw_text,
            flags=re.IGNORECASE
        ).strip(' ,.')

        if not text_to_translate:
            return "Que souhaitez-vous traduire ?"

        translated = self.translate(text_to_translate, target_lang)
        return f"« {text_to_translate} » en {target_lang} : « {translated} »"
