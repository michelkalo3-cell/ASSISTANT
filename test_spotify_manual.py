"""
Script de test manuel pour simuler une commande Spotify via le moteur CHARAMOU AI.
"""
import os
import sys
from pathlib import Path

# Ajouter le répertoire racine au sys.path
sys.path.insert(0, str(Path(__file__).parent))

from core.engine import AssistantEngine
from core.logger import setup_logger

logger = setup_logger("TestManual")

def simulate_test():
    print("\n--- Simulation CHARAMOU AI : Test Spotify ---")
    
    # On force des clés bidon pour éviter l'échec immédiat du setup si .env est vide
    os.environ["SPOTIFY_CLIENT_ID"] = "fake_id"
    os.environ["SPOTIFY_CLIENT_SECRET"] = "fake_secret"
    
    try:
        engine = AssistantEngine()
        # On initialise manuellement sans lancer la boucle infinie
        engine._init_modules()
        engine._init_agents()
        engine._register_routes()
        engine.plugins.load_all()
        
        test_commands = [
            "joue Bohemian Rhapsody",
            "met en pause la musique",
            "titre suivant",
            "quel est le titre en cours ?"
        ]
        
        for cmd in test_commands:
            print(f"\n[Utilisateur] : {cmd}")
            # On utilise process_input qui fait le pipeline complet
            # Note: cela risque de logguer une erreur Spotify car les clés sont fausses,
            # mais cela valide la classification et le routing.
            response = engine.process_input(cmd)
            print(f"[Assistant]   : {response}")

    except Exception as e:
        print(f"Erreur pendant le test : {e}")

if __name__ == "__main__":
    simulate_test()
