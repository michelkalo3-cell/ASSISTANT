"""
CHARAMOU AI - Interface CLI (terminal)
Interface textuelle complète avec Rich pour le terminal.
"""
import sys
from pathlib import Path

# Ajout du répertoire racine au path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


def run_cli():
    """Lance l'assistant en mode CLI pur."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    # Bannière
    banner = """
  ██████╗██╗  ██╗ █████╗ ██████╗  █████╗ ███╗   ███╗ ██████╗ ██╗   ██╗
 ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔══██╗████╗ ████║██╔═══██╗██║   ██║
 ██║     ███████║███████║██████╔╝███████║██╔████╔██║██║   ██║██║   ██║
 ██║     ██╔══██║██╔══██║██╔══██╗██╔══██║██║╚██╔╝██║██║   ██║██║   ██║
 ╚██████╗██║  ██║██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║╚██████╔╝╚██████╔╝
  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝
                    Votre Assistant Personnel IA
    """

    if use_rich:
        console.print(Panel(banner, style="bold cyan", border_style="blue"))
        console.print("[yellow]Mode CLI — Tapez votre commande ou 'quitter' pour sortir.[/yellow]\n")
    else:
        print(banner)
        print("Mode CLI — Tapez votre commande ou 'quitter' pour sortir.\n")

    # Lancement du moteur
    from core.engine import AssistantEngine
    engine = AssistantEngine()
    engine._voice_enabled = False  # Force le mode CLI

    # Init modules sans boucle principale
    engine._init_modules()
    engine._init_agents()
    engine._register_routes()
    engine._subscribe_events()
    engine._register_health_checks()
    engine.scheduler.start()

    if use_rich:
        console.print(f"[green]✅ {engine.name} prêt ![/green]\n")
    else:
        print(f"✅ {engine.name} prêt !\n")

    # Boucle CLI
    try:
        while True:
            if use_rich:
                user_input = console.input("[bold blue]Vous[/bold blue] → ").strip()
            else:
                user_input = input("Vous → ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("quitter", "quit", "exit", "au revoir"):
                print("Au revoir !")
                break

            if user_input.lower() == "stats":
                print(engine.state.summary())
                continue

            if user_input.lower() == "aide":
                print("Commandes disponibles :", engine.router.available_intents())
                continue

            response = engine.process_input(user_input)

    except KeyboardInterrupt:
        print("\nInterruption — au revoir !")
    except EOFError:
        pass
    finally:
        engine.shutdown()


if __name__ == "__main__":
    run_cli()
