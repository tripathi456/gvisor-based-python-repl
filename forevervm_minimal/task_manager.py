"""Task manager for ForeverVM service.

Handles background tasks and their lifecycle management.
Follows the principles:
- Single Responsibility: Each task has one clear purpose
- Proper Lifecycle: Tasks can be started, stopped, and monitored
- Clean Shutdown: All tasks can be gracefully terminated
"""

import threading
import time
from typing import Callable, Dict, Optional
from dataclasses import dataclass
import signal
import logging

logger = logging.getLogger(__name__)

@dataclass
class Task:
    """Represents a background task."""
    name: str
    interval: float  # seconds
    callback: Callable
    thread: Optional[threading.Thread] = None
    should_stop: Optional[threading.Event] = None

class TaskManager:
    """Manages background tasks for the service."""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._shutdown_event = threading.Event()
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
    
    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received shutdown signal {signum}")
        self.stop_all_tasks()
    
    def _task_loop(self, task: Task):
        """Main loop for a background task."""
        logger.info(f"Starting task: {task.name}")
        while not task.should_stop.is_set():
            try:
                task.callback()
            except Exception as e:
                logger.error(f"Error in task {task.name}: {e}")
            time.sleep(task.interval)
        logger.info(f"Task stopped: {task.name}")
    
    def add_task(self, name: str, interval: float, callback: Callable):
        """Add a new background task."""
        if name in self.tasks:
            raise ValueError(f"Task {name} already exists")
        
        task = Task(
            name=name,
            interval=interval,
            callback=callback,
            should_stop=threading.Event()
        )
        
        thread = threading.Thread(
            target=self._task_loop,
            args=(task,),
            daemon=True,
            name=f"Task-{name}"
        )
        task.thread = thread
        self.tasks[name] = task
        thread.start()
    
    def stop_task(self, name: str):
        """Stop a specific task."""
        if task := self.tasks.get(name):
            logger.info(f"Stopping task: {name}")
            task.should_stop.set()
            if task.thread and task.thread.is_alive():
                task.thread.join(timeout=5.0)
            del self.tasks[name]
    
    def stop_all_tasks(self):
        """Stop all running tasks gracefully."""
        logger.info("Stopping all tasks")
        task_names = list(self.tasks.keys())
        for name in task_names:
            self.stop_task(name)
    
    def is_task_running(self, name: str) -> bool:
        """Check if a task is currently running."""
        task = self.tasks.get(name)
        return bool(task and task.thread and task.thread.is_alive())
