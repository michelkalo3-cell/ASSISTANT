"""
Tests pour le plugin Spotify.
Vérifie le chargement et le routage des commandes.
"""
import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from pathlib import Path

# Ajouter le chemin racine au sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.plugins.spotify.plugin import Plugin

class TestSpotifyPlugin(unittest.TestCase):

    def setUp(self):
        # On simule les variables d'environnement
        os.environ["SPOTIFY_CLIENT_ID"] = "test_id"
        os.environ["SPOTIFY_CLIENT_SECRET"] = "test_secret"
        
        # On mock SpotifyOAuth et Spotify dans le namespace du plugin
        self.patcher_oauth = patch('modules.plugins.spotify.plugin.SpotifyOAuth')
        self.patcher_sp = patch('modules.plugins.spotify.plugin.spotipy.Spotify')
        self.patcher_cache = patch('modules.plugins.spotify.plugin.CacheFileHandler')
        
        self.mock_oauth = self.patcher_oauth.start()
        self.mock_sp = self.patcher_sp.start()
        self.mock_cache = self.patcher_cache.start()
        
        self.plugin = Plugin()

    def tearDown(self):
        self.patcher_oauth.stop()
        self.patcher_sp.stop()
        self.patcher_cache.stop()

    def test_setup_success(self):
        """Vérifie que le setup réussit avec les clés API."""
        result = self.plugin.setup()
        self.assertTrue(result)
        self.mock_oauth.assert_called_once()
        self.mock_sp.assert_called_once()

    def test_setup_failure_missing_keys(self):
        """Vérifie que le setup échoue si les clés sont manquantes."""
        del os.environ["SPOTIFY_CLIENT_ID"]
        plugin = Plugin()
        result = plugin.setup()
        self.assertFalse(result)

    def test_handle_pause(self):
        """Vérifie que la commande pause appelle sp.pause_playback."""
        self.plugin.setup()
        result = self.plugin.handle_pause({}, {})
        self.plugin.sp.pause_playback.assert_called_once()
        self.assertIn("pause", result.lower())

    def test_handle_play_search(self):
        """Vérifie que la commande play avec texte effectue une recherche."""
        self.plugin.setup()
        
        # Mock de l'appareil actif
        self.plugin.sp.devices.return_value = {"devices": [{"id": "dev1", "is_active": True}]}
        
        # Mock de la recherche
        self.plugin.sp.search.return_value = {
            "tracks": {
                "items": [{"name": "Song A", "uri": "spotify:track:123", "artists": [{"name": "Artist B"}]}]
            }
        }
        
        entities = {"raw_text": "joue Bohemian Rhapsody"}
        result = self.plugin.handle_play(entities, {})
        
        self.plugin.sp.search.assert_called()
        self.plugin.sp.start_playback.assert_called_with(device_id="dev1", uris=["spotify:track:123"])
        self.assertIn("Lecture de « Song A »", result)

    def test_handle_next(self):
        """Vérifie que la commande next appelle sp.next_track."""
        self.plugin.setup()
        result = self.plugin.handle_next({}, {})
        self.plugin.sp.next_track.assert_called_once()
        self.assertIn("suivant", result.lower())

if __name__ == "__main__":
    unittest.main()
