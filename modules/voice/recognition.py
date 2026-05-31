"""
CHARAMOU AI - Reconnaissance vocale (Speech-to-Text)
Supporte : Google STT, Whisper local, Vosk.
"""
import speech_recognition as sr
from typing import Optional
from core.logger import setup_logger
from core.exceptions import SpeechRecognitionError, MicrophoneError

logger = setup_logger("SpeechRecognizer")


class SpeechRecognizer:
    """
    Convertit la voix en texte.
    Moteurs supportés : 'google' (défaut), 'whisper', 'sphinx'.
    """

    def __init__(self, config: dict = None):
        self.config = config or {}
        voice_cfg = self._load_voice_config()

        self.engine       = voice_cfg.get("stt_engine", "google")
        self.language     = voice_cfg.get("stt_language", "fr-FR")
        self.timeout      = voice_cfg.get("stt_timeout", 5)
        self.phrase_limit = voice_cfg.get("stt_phrase_time_limit", 10)
        self.energy_threshold = voice_cfg.get("energy_threshold", 300)
        self.dynamic_energy   = voice_cfg.get("dynamic_energy", True)
        self.mic_index        = voice_cfg.get("microphone_index", None)

        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = self.energy_threshold
        self._recognizer.dynamic_energy_threshold = self.dynamic_energy

        logger.info(f"SpeechRecognizer initialisé : engine={self.engine}, lang={self.language}")

    def _load_voice_config(self) -> dict:
        try:
            import json
            from pathlib import Path
            path = Path(__file__).parent.parent.parent / "config" / "voice.json"
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def listen(self) -> Optional[str]:
        """
        Écoute le micro et retourne le texte reconnu.
        Retourne None si rien n'est capté.
        """
        try:
            mic_kwargs = {"device_index": self.mic_index} if self.mic_index is not None else {}
            with sr.Microphone(**mic_kwargs) as source:
                logger.debug("Ajustement au bruit ambiant...")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.debug("En écoute...")
                audio = self._recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=self.phrase_limit
                )
            return self._transcribe(audio)

        except sr.WaitTimeoutError:
            logger.debug("Timeout : aucune voix détectée.")
            return None
        except OSError as e:
            raise MicrophoneError(f"Impossible d'accéder au microphone : {e}")
        except Exception as e:
            logger.error(f"Erreur écoute : {e}")
            return None

    def _transcribe(self, audio: sr.AudioData) -> Optional[str]:
        """Transcrit l'audio en texte selon le moteur choisi."""
        try:
            if self.engine == "google":
                text = self._recognizer.recognize_google(audio, language=self.language)
            elif self.engine == "whisper":
                text = self._recognizer.recognize_whisper(audio, language="french")
            elif self.engine == "sphinx":
                text = self._recognizer.recognize_sphinx(audio)
            else:
                text = self._recognizer.recognize_google(audio, language=self.language)

            logger.info(f"Reconnu : '{text}'")
            return text.strip()

        except sr.UnknownValueError:
            logger.debug("Audio non reconnu.")
            return None
        except sr.RequestError as e:
            logger.error(f"Erreur API reconnaissance : {e}")
            return None

    def listen_once_cli(self) -> str:
        """Mode CLI : lit depuis stdin (test sans micro)."""
        return input("🎤 Vous : ").strip()
