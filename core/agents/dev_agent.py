"""
CHARAMOU AI - Agent Développement
Gestion du terminal, Git, et exécution de scripts.
"""
import os
import subprocess
from typing import Any, Dict, List, Optional
from core.agents.base_agent import BaseAgent
from core.exceptions import SecurityError

class DevAgent(BaseAgent):
    name = "dev_agent"
    description = "Gère le terminal, Git et le développement."

    def can_handle(self, task: str, entities: dict) -> bool:
        keywords = ["git", "terminal", "commande", "exécute", "python", "script", "commit", "push"]
        return any(kw in task.lower() for kw in keywords)

    def execute(self, task: str, entities: dict, context: Any = None) -> str:
        text = task.lower()

        # Sécurité : vérifier les permissions
        if self.security:
            self.security.require("terminal_access")

        if "git status" in text:
            return self._run_command(["git", "status"])
        elif "git commit" in text:
            msg = entities.get("raw_text", "Commit via CHARAMOU AI").split("commit")[-1].strip()
            return self._run_command(["git", "commit", "-m", msg])
        elif "python" in text or "exécute" in text:
            # Extraction sommaire du script
            return "L'exécution de scripts arbitraires nécessite une validation manuelle supplémentaire."
        
        return self._run_command(task.split())

    def _run_command(self, cmd: List[str]) -> str:
        try:
            # Validation supplémentaire via SecurityManager si possible
            if self.security:
                self.security.validate_command(" ".join(cmd))
            
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10, shell=True
            )
            if result.returncode == 0:
                output = result.stdout.strip()
                return f"Sortie :\n```\n{output[:500]}\n```"
            else:
                return f"Erreur (code {result.returncode}) :\n{result.stderr.strip()[:200]}"
        except Exception as e:
            return f"Échec de l'exécution : {e}"
