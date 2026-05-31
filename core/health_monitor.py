"""
CHARAMOU AI - HealthMonitor + RecoveryManager + Watchdog
Surveillance de la santé du système et récupération automatique.
"""
import threading
import time
from datetime import datetime
from typing import Callable, Dict, Optional, Any
from core.logger import setup_logger

logger = setup_logger("HealthMonitor")


# ─────────────────────────────────────────────────────────────────────────────
# Module Health Status
# ─────────────────────────────────────────────────────────────────────────────
class ModuleHealth:
    def __init__(self, name: str):
        self.name          = name
        self.status        = "unknown"   # ok | degraded | down
        self.last_check    = None
        self.error_count   = 0
        self.last_error    = None
        self.uptime_start  = datetime.now()

    def mark_ok(self) -> None:
        self.status     = "ok"
        self.last_check = datetime.now()
        self.error_count = 0

    def mark_error(self, error: str) -> None:
        self.status     = "degraded" if self.error_count < 3 else "down"
        self.last_error = error
        self.error_count += 1
        self.last_check = datetime.now()

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "status":      self.status,
            "error_count": self.error_count,
            "last_error":  self.last_error,
            "last_check":  self.last_check.isoformat() if self.last_check else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# HealthMonitor
# ─────────────────────────────────────────────────────────────────────────────
class HealthMonitor:
    """
    Surveille la santé de chaque module.
    Publie des événements si un module tombe.
    """

    def __init__(self, event_bus=None, check_interval: int = 30):
        self.bus            = event_bus
        self.check_interval = check_interval
        self._modules: Dict[str, ModuleHealth] = {}
        self._checks: Dict[str, Callable]      = {}
        self._running       = False
        self._thread: Optional[threading.Thread] = None
        logger.info("HealthMonitor initialisé.")

    def register(self, name: str, check_fn: Callable) -> None:
        """Enregistre un module avec sa fonction de vérification."""
        self._modules[name] = ModuleHealth(name)
        self._checks[name]  = check_fn
        logger.debug(f"Module enregistré pour monitoring : '{name}'")

    def start(self) -> None:
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True, name="HealthMonitor")
        self._thread.start()
        logger.info("HealthMonitor démarré.")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            self._run_checks()
            time.sleep(self.check_interval)

    def _run_checks(self) -> None:
        for name, check_fn in self._checks.items():
            module = self._modules[name]
            try:
                check_fn()
                module.mark_ok()
            except Exception as e:
                module.mark_error(str(e))
                logger.warning(f"Module '{name}' dégradé : {e}")
                if self.bus:
                    self.bus.publish("module_degraded", {"module": name, "error": str(e)})
                if module.status == "down":
                    logger.error(f"Module '{name}' HS !")
                    if self.bus:
                        self.bus.publish("module_down", {"module": name})

    def get_report(self) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now().isoformat(),
            "modules":   {n: m.to_dict() for n, m in self._modules.items()},
            "overall":   self._overall_status()
        }

    def _overall_status(self) -> str:
        statuses = [m.status for m in self._modules.values()]
        if all(s == "ok" for s in statuses):
            return "healthy"
        if any(s == "down" for s in statuses):
            return "critical"
        return "degraded"

    def is_healthy(self, module: str) -> bool:
        m = self._modules.get(module)
        return m.status == "ok" if m else False


# ─────────────────────────────────────────────────────────────────────────────
# RecoveryManager
# ─────────────────────────────────────────────────────────────────────────────
class RecoveryManager:
    """
    Tente de récupérer automatiquement un module tombé.
    Stratégies : restart, fallback, disable.
    """

    def __init__(self):
        self._strategies: Dict[str, Callable] = {}
        self._fallbacks:  Dict[str, Any]      = {}
        logger.info("RecoveryManager initialisé.")

    def register_restart(self, module_name: str, restart_fn: Callable) -> None:
        self._strategies[module_name] = restart_fn

    def register_fallback(self, module_name: str, fallback: Any) -> None:
        self._fallbacks[module_name] = fallback

    def recover(self, module_name: str) -> bool:
        """Tente la récupération d'un module. Retourne True si succès."""
        fn = self._strategies.get(module_name)
        if fn:
            try:
                fn()
                logger.info(f"Module '{module_name}' récupéré avec succès.")
                return True
            except Exception as e:
                logger.error(f"Récupération de '{module_name}' échouée : {e}")
        return False

    def get_fallback(self, module_name: str) -> Optional[Any]:
        return self._fallbacks.get(module_name)

    def on_module_down(self, data: dict) -> None:
        """Callback pour l'EventBus."""
        module = data.get("module", "unknown")
        logger.warning(f"Tentative de récupération : '{module}'")
        if not self.recover(module):
            fb = self.get_fallback(module)
            if fb:
                logger.info(f"Fallback activé pour '{module}'.")
