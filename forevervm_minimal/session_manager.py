# session_manager.py

import threading
import time
import uuid

from forevervm_minimal.worker_manager import WorkerManager
from forevervm_minimal.snapshot_storage import SnapshotStorage
from forevervm_minimal.custom_serializer import Serializer
from forevervm_minimal.session_data import SessionData
from forevervm_minimal.config import SESSION_INACTIVITY_TIMEOUT

class SessionManager:
    def __init__(self, snapshot_storage: SnapshotStorage, worker_manager: WorkerManager):
        self.snapshot_storage = snapshot_storage
        self.worker_manager = worker_manager
        
        self.sessions = {}  # dict: session_id -> SessionData
        self.lock = threading.Lock()
        
        self.inactivity_timeout = SESSION_INACTIVITY_TIMEOUT

    def create_session(self):
        session_id = str(uuid.uuid4())
        # create a new worker
        worker = self.worker_manager.get_worker()
        
        # create SessionData object
        session_data = SessionData(
            session_id=session_id,
            status="active",
            last_activity=time.time(),
            worker=worker,
            snapshot_path=None
        )
        
        with self.lock:
            self.sessions[session_id] = session_data
        
        return session_id

    def execute_code(self, session_id, code):
        with self.lock:
            session_data = self.sessions.get(session_id)
            if not session_data:
                raise ValueError(f"Session {session_id} not found.")
        
        # If session is snapshotted => restore
        if session_data.status == "snapshotted":
            self._restore_session(session_data)
        
        # Now session should be active and have a worker
        output = session_data.worker.execute_code(code)
        
        # Update last activity
        session_data.last_activity = time.time()
        
        return output

    def checkpoint_idle_sessions(self):
        """Called periodically by a background thread."""
        with self.lock:
            now = time.time()
            for session_data in self.sessions.values():
                if session_data.status == "active":
                    if now - session_data.last_activity > self.inactivity_timeout:
                        self._checkpoint_session(session_data)

    def _checkpoint_session(self, session_data):
        # Mark status -> 'snapshotting' to avoid concurrency issues
        session_data.status = "snapshotting"
        
        # Instruct the worker to produce a serialized environment
        pickled_env = session_data.worker.serialize_environment()
        
        # Store the pickled data in snapshot_storage
        snapshot_path = self.snapshot_storage.save_snapshot(session_data.session_id, pickled_env)
        session_data.snapshot_path = snapshot_path
        
        # Release the worker
        self.worker_manager.release_worker(session_data.worker)
        session_data.worker = None
        session_data.status = "snapshotted"

    def _restore_session(self, session_data):
        # Mark status -> 'restoring'
        session_data.status = "restoring"
        
        # get a new worker
        worker = self.worker_manager.get_worker()
        session_data.worker = worker
        
        # load the pickled environment
        pickled_env = self.snapshot_storage.load_snapshot(session_data.session_id)
        
        # inject environment into worker
        worker.restore_environment(pickled_env)
        
        # mark active
        session_data.status = "active"
        session_data.last_activity = time.time()