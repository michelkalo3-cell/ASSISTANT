"""
CHARAMOU AI - Planificateur de tâches
Gère rappels, alarmes, notifications et routines automatiques.
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Any
from dataclasses import dataclass, field
from core.logger import setup_logger

logger = setup_logger("Scheduler")


@dataclass
class ScheduledTask:
    name: str
    callback: Callable
    run_at: datetime
    repeat_seconds: Optional[float] = None   # None = unique
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    done: bool = False
    run_count: int = 0

    def is_due(self) -> bool:
        return datetime.now() >= self.run_at and not self.done

    def reschedule(self) -> None:
        if self.repeat_seconds:
            self.run_at = datetime.now() + timedelta(seconds=self.repeat_seconds)
            self.run_count += 1
        else:
            self.done = True


class Scheduler:
    """
    Planificateur interne.
    Fonctionne dans un thread de fond et déclenche les tâches à l'heure.
    """

    def __init__(self, tick_interval: float = 1.0):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._running = False
        self._tick_interval = tick_interval
        self._thread: Optional[threading.Thread] = None
        logger.info("Scheduler initialisé.")

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="Scheduler")
        self._thread.start()
        logger.info("Scheduler démarré.")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("Scheduler arrêté.")

    def add_task(
        self,
        name: str,
        callback: Callable,
        run_at: datetime,
        repeat_seconds: Optional[float] = None,
        *args, **kwargs
    ) -> str:
        task = ScheduledTask(
            name=name,
            callback=callback,
            run_at=run_at,
            repeat_seconds=repeat_seconds,
            args=args,
            kwargs=kwargs
        )
        with self._lock:
            self._tasks[name] = task
        logger.info(f"Tâche planifiée : '{name}' à {run_at.strftime('%H:%M:%S')}")
        return name

    def add_in(self, name: str, callback: Callable, seconds: float, **kwargs) -> str:
        """Planifie dans N secondes."""
        run_at = datetime.now() + timedelta(seconds=seconds)
        return self.add_task(name, callback, run_at, **kwargs)

    def add_daily(self, name: str, callback: Callable, hour: int, minute: int = 0) -> str:
        """Planifie une tâche quotidienne."""
        now = datetime.now()
        run_at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if run_at < now:
            run_at += timedelta(days=1)
        return self.add_task(name, callback, run_at, repeat_seconds=86400)

    def cancel(self, name: str) -> bool:
        with self._lock:
            if name in self._tasks:
                del self._tasks[name]
                logger.info(f"Tâche '{name}' annulée.")
                return True
        return False

    def list_tasks(self) -> List[dict]:
        with self._lock:
            return [
                {
                    "name": t.name,
                    "run_at": t.run_at.isoformat(),
                    "repeats": t.repeat_seconds is not None,
                    "done": t.done,
                    "run_count": t.run_count
                }
                for t in self._tasks.values()
            ]

    def _loop(self) -> None:
        while self._running:
            with self._lock:
                tasks = list(self._tasks.values())

            for task in tasks:
                if task.is_due():
                    self._execute(task)

            # Nettoyage des tâches terminées
            with self._lock:
                self._tasks = {
                    k: v for k, v in self._tasks.items() if not v.done
                }

            time.sleep(self._tick_interval)

    def _execute(self, task: ScheduledTask) -> None:
        def run():
            try:
                logger.info(f"Exécution planifiée : '{task.name}'")
                task.callback(*task.args, **task.kwargs)
            except Exception as e:
                logger.error(f"Erreur dans la tâche '{task.name}': {e}")
            finally:
                task.reschedule()

        threading.Thread(target=run, daemon=True, name=f"Task-{task.name}").start()
