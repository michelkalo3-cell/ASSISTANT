"""
CHARAMOU AI - Détection du mot de réveil
Supporte : détection simple par mots-clés (fallback léger).
Prêt pour Porcupine (pvporcupine) en production.
"""
import threading
from typing import Callable, Optional
from core.logger import setup_logger

logger = setup_logger("WakeWord")


class WakeWordDetector:
    """
    Détecte le mot de réveil dans le flux audio.

    Mode léger (défaut) : surveille la transcription pour le mot-clé.
    Mode Porcupine : détection bas niveau sur le flux PCM brut.
    """

    def __init__(self, wake_word: str = "charamou", on_detected: Callable = None):
        self.wake_word   = wake_word.lower()
        self.on_detected = on_detected
        self._active     = False
        self._thread: Optional[threading.Thread] = None
        logger.info(f"WakeWordDetector prêt — mot clé : '{self.wake_word}'")

    def check_text(self, text: str) -> bool:
        """
        Vérifie si le mot de réveil est présent dans une transcription.
        Retourne True si détecté.
        """
        if self.wake_word in text.lower():
            logger.info(f"Mot de réveil détecté dans : '{text}'")
            if self.on_detected:
                self.on_detected()
            return True
        return False

    def start_porcupine(self, access_key: str, keyword_path: str = None) -> bool:
        """
        Démarre la détection Porcupine (haute précision, offline).
        Nécessite pvporcupine installé et une clé d'accès Picovoice.
        """
        try:
            import pvporcupine
            import pyaudio
            import struct

            if keyword_path:
                porcupine = pvporcupine.create(
                    access_key=access_key,
                    keyword_paths=[keyword_path]
                )
            else:
                porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=["jarvis"]  # mot de réveil Porcupine standard
                )

            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length
            )

            self._active = True
            logger.info("Porcupine démarré — en attente du wake word...")

            def _loop():
                while self._active:
                    pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                    result = porcupine.process(pcm)
                    if result >= 0:
                        logger.info("Wake word Porcupine détecté !")
                        if self.on_detected:
                            self.on_detected()

                stream.stop_stream()
                stream.close()
                pa.terminate()
                porcupine.delete()

            self._thread = threading.Thread(target=_loop, daemon=True, name="WakeWord")
            self._thread.start()
            return True

        except ImportError:
            logger.warning("pvporcupine non installé — utilisation du mode texte uniquement.")
            return False
        except Exception as e:
            logger.error(f"Erreur Porcupine : {e}")
            return False

    def stop(self) -> None:
        self._active = False
        logger.info("WakeWordDetector arrêté.")
