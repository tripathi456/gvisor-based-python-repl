"""Component factory for ForeverVM service.

This module handles the initialization and lifecycle of core components
while maintaining proper dependency injection and separation of concerns.
"""

from typing import Optional
import threading
from dataclasses import dataclass

from forevervm_minimal.session_manager import SessionManager
from forevervm_minimal.snapshot_storage import LocalFileStorage
from forevervm_minimal.worker_manager import WorkerManager
from forevervm_minimal.task_manager import TaskManager
from forevervm_minimal.config import (
    SNAPSHOT_DIR,
    WORKER_POOL_SIZE,
    SESSION_CLEANUP_INTERVAL,
)

@dataclass
class ServiceComponents:
    """Container for core service components."""
    storage: LocalFileStorage
    worker_manager: WorkerManager
    session_manager: SessionManager
    task_manager: TaskManager

def create_components() -> ServiceComponents:
    """Create and wire up all required service components."""
    # Initialize storage first as it has no dependencies
    storage = LocalFileStorage(base_dir=SNAPSHOT_DIR)
    
    # Initialize worker manager next
    worker_manager = WorkerManager(pool_size=WORKER_POOL_SIZE)
    
    # Initialize session manager with its dependencies
    session_manager = SessionManager(
        snapshot_storage=storage,
        worker_manager=worker_manager
    )
    
    # Initialize task manager and add background tasks
    task_manager = TaskManager()
    task_manager.add_task(
        name="idle_session_checker",
        interval=SESSION_CLEANUP_INTERVAL,
        callback=session_manager.checkpoint_idle_sessions
    )
    
    return ServiceComponents(
        storage=storage,
        worker_manager=worker_manager,
        session_manager=session_manager,
        task_manager=task_manager
    )
