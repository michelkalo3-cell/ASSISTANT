"""
CHARAMOU AI - Moniteur système
Surveille batterie, réseau et processus.
"""
import threading
import time
import psutil
from core.logger import setup_logger

logger = setup_logger("SystemMonitor")


class SystemMonitor:
    """
    Surveille en arrière-plan :
    - Batterie (alerte si < 20%)
    - Connexion réseau
    - Ressources CPU/RAM
    """

    def __init__(self, event_bus=None, check_interval: int = 30):
        self.bus = event_bus
        self.check_interval = check_interval
        self._running = False
        self._thread = None
        self._last_battery_warn = 100
        logger.info("SystemMonitor initialisé.")

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SystemMonitor")
        self._thread.start()
        logger.info("SystemMonitor démarré.")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_battery()
                self._check_network()
            except Exception as e:
                logger.debug(f"Erreur monitoring : {e}")
            time.sleep(self.check_interval)

    def _check_battery(self) -> None:
        battery = psutil.sensors_battery()
        if battery is None:
            return
        percent = battery.percent
        if percent < 15 and self._last_battery_warn > 15:
            logger.warning(f"Batterie critique : {percent}%")
            if self.bus:
                self.bus.publish("battery_low", {"percent": percent})
            self._last_battery_warn = percent
        elif percent > 20:
            self._last_battery_warn = percent

    def _check_network(self) -> None:
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except OSError:
            logger.warning("Connexion réseau perdue.")
            if self.bus:
                self.bus.publish("internet_disconnected", {})

    def get_stats(self) -> dict:
        """Retourne les statistiques système actuelles."""
        stats = {
            "cpu_percent":  psutil.cpu_percent(interval=1),
            "ram_percent":  psutil.virtual_memory().percent,
            "ram_used_gb":  round(psutil.virtual_memory().used / 1e9, 1),
            "disk_percent": psutil.disk_usage('/').percent,
        }
        battery = psutil.sensors_battery()
        if battery:
            stats["battery"] = {
                "percent": round(battery.percent),
                "charging": battery.power_plugged
            }
        return stats

    def get_stats_response(self) -> str:
        stats = self.get_stats()
        parts = [
            f"CPU à {stats['cpu_percent']}%",
            f"RAM à {stats['ram_percent']}% ({stats['ram_used_gb']} Go utilisés)",
        ]
        if "battery" in stats:
            b = stats["battery"]
            status = "en charge" if b["charging"] else "sur batterie"
            parts.append(f"Batterie à {b['percent']}% ({status})")
        return "État du système : " + ", ".join(parts) + "."
