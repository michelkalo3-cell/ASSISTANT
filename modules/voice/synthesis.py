"""
CHARAMOU AI - Synthèse vocale (Text-to-Speech)
Moteur principal : pyttsx3 (offline, Windows/Linux/macOS).
"""
import threading
from typing import Optional
from core.logger import setup_logger
from core.exceptions import SynthesisError

logger = setup_logger("Synthesizer")


class Synthesizer:
    """
    Convertit du texte en parole.
    Utilise pyttsx3 par défaut (offline).
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        voice_cfg = self._load_voice_config()

        self.rate   = voice_cfg.get("tts_rate", 175)
        self.volume = voice_cfg.get("tts_volume", 0.9)
        self.voice_id = voice_cfg.get("tts_voice_id", None)
        self._lock  = threading.Lock()
        self._engine = None
        self._init_engine()

    def _load_voice_config(self) -> dict:
        try:
            import json
            from pathlib import Path
            path = Path(__file__).parent.parent.parent / "config" / "voice.json"
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _init_engine(self) -> None:
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)

            # Sélection de la voix française si disponible
            voices = self._engine.getProperty("voices")
            french_voice = None
            for v in voices:
                lang = getattr(v, "languages", [])
                name = v.name.lower()
                if "fr" in str(lang).lower() or "french" in name or "hortense" in name:
                    french_voice = v.id
                    break

            if self.voice_id:
                self._engine.setProperty("voice", self.voice_id)
            elif french_voice:
                self._engine.setProperty("voice", french_voice)

            logger.info(f"Synthesizer pyttsx3 initialisé (rate={self.rate}, vol={self.volume}).")
        except Exception as e:
            logger.warning(f"pyttsx3 indisponible : {e}")
            self._engine = None

    def speak(self, text: str) -> None:
        """Prononce le texte à voix haute (bloquant)."""
        if not text.strip():
            return
        with self._lock:
            if self._engine:
                try:
                    self._engine.say(text)
                    self._engine.runAndWait()
                except Exception as e:
                    logger.error(f"Erreur synthèse : {e}")
                    raise SynthesisError(str(e))
            else:
                # Fallback silencieux (affiche uniquement)
                logger.debug(f"[TTS MUET] {text}")

    def speak_async(self, text: str) -> threading.Thread:
        """Prononce de façon non bloquante."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    def set_rate(self, rate: int) -> None:
        self.rate = rate
        if self._engine:
            self._engine.setProperty("rate", rate)

    def set_volume(self, volume: float) -> None:
        volume = max(0.0, min(1.0, volume))
        self.volume = volume
        if self._engine:
            self._engine.setProperty("volume", volume)

    def list_voices(self) -> list:
        if self._engine:
            return [{"id": v.id, "name": v.name} for v in self._engine.getProperty("voices")]
        return []
