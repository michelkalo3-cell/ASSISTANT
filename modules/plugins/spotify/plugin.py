"""
CHARAMOU AI - Plugin Spotify v2
Contrôle complet de la lecture via Spotipy.
"""
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from core.plugin_manager import BasePlugin
from core.logger import setup_logger

logger = setup_logger("SpotifyPlugin")

class Plugin(BasePlugin):
    name = "spotify"
    description = "Contrôle la musique sur Spotify (Play, Pause, Volume, Recherche)."
    version = "2.0.0"

    def setup(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
        
        if not self.client_id or not self.client_secret:
            logger.warning("Clés Spotify manquantes dans le .env (SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET)")
            return False

        try:
            scope = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
            
            # Utilisation du CacheFileHandler pour éviter le DeprecationWarning
            cache_path = os.path.join("data", "cache", ".spotifycache")
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            handler = CacheFileHandler(cache_path=cache_path)

            self.sp_oauth = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=scope,
                cache_handler=handler
            )
            self.sp = spotipy.Spotify(auth_manager=self.sp_oauth)
            logger.info("Spotify Plugin initialisé.")
            return True
        except Exception as e:
            logger.error(f"Erreur initialisation Spotify: {e}")
            return False

    def register_routes(self, router):
        router.register("PLAY_MUSIC", self.handle_play)
        router.register("PAUSE_MUSIC", self.handle_pause)
        router.register("STOP_MUSIC", self.handle_pause)
        router.register("NEXT_MUSIC", self.handle_next)
        router.register("PREV_MUSIC", self.handle_prev)
        router.register("SET_VOLUME", self.handle_volume)
        router.register("GET_CURRENT_TRACK", self.handle_current_track)

    def _get_active_device(self):
        """Récupère l'ID du premier appareil actif trouvé."""
        devices = self.sp.devices()
        if not devices or not devices.get("devices"):
            return None
        
        # Chercher l'appareil actif
        for d in devices["devices"]:
            if d["is_active"]:
                return d["id"]
        
        # Sinon prendre le premier disponible
        return devices["devices"][0]["id"]

    def handle_play(self, entities, context):
        query = entities.get("raw_text", "").lower()
        # Nettoyage basique (enlever 'joue', 'lance', etc.)
        for word in ["joue", "lance", "met", "spotify"]:
            query = query.replace(word, "").strip()

        try:
            device_id = self._get_active_device()
            if not device_id:
                return "Aucun appareil Spotify actif détecté. Lancez Spotify sur un appareil."

            if not query or query in ["musique", "la musique"]:
                self.sp.start_playback(device_id=device_id)
                return "Lecture reprise."
            
            # Recherche
            results = self.sp.search(q=query, limit=1, type="track")
            if results["tracks"]["items"]:
                track = results["tracks"]["items"][0]
                self.sp.start_playback(device_id=device_id, uris=[track["uri"]])
                return f"Lecture de « {track['name']} » par {track['artists'][0]['name']}."
            else:
                return f"Je n'ai pas trouvé « {query} » sur Spotify."
        except Exception as e:
            logger.error(f"Erreur Spotify Play: {e}")
            return "Une erreur est survenue lors de la lecture Spotify. Vérifiez votre connexion."

    def handle_pause(self, entities, context):
        try:
            self.sp.pause_playback()
            return "Musique mise en pause."
        except Exception as e:
            logger.error(f"Erreur Spotify Pause: {e}")
            return "Impossible de mettre la musique en pause."

    def handle_next(self, entities, context):
        try:
            self.sp.next_track()
            return "Titre suivant."
        except Exception as e:
            return f"Erreur titre suivant : {e}"

    def handle_prev(self, entities, context):
        try:
            self.sp.previous_track()
            return "Titre précédent."
        except Exception as e:
            return f"Erreur titre précédent : {e}"

    def handle_volume(self, entities, context):
        # On suppose que l'entité 'value' contient le volume (0-100)
        volume = entities.get("value", 50)
        try:
            self.sp.volume(volume)
            return f"Volume réglé à {volume}%."
        except Exception as e:
            return f"Erreur réglage volume : {e}"

    def handle_current_track(self, entities, context):
        try:
            track = self.sp.current_user_playing_track()
            if track and track.get("item"):
                item = track["item"]
                return f"En cours : « {item['name']} » par {item['artists'][0]['name']}."
            return "Aucune musique en cours."
        except Exception as e:
            return "Erreur lors de la récupération du titre en cours."
