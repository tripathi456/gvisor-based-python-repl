# snapshot_storage.py

import abc
import os

class SnapshotStorage(abc.ABC):
    @abc.abstractmethod
    def save_snapshot(self, session_id: str, snapshot_data: bytes) -> str:
        """Save pickled environment. Return path or reference."""
        pass

    @abc.abstractmethod
    def load_snapshot(self, session_id: str) -> bytes:
        """Load pickled environment from storage."""
        pass

    @abc.abstractmethod
    def delete_snapshot(self, session_id: str) -> None:
        """Remove snapshot from storage."""
        pass


class LocalFileStorage(SnapshotStorage):
    def __init__(self, base_dir="/var/forevervm/snapshots"):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
    
    def save_snapshot(self, session_id: str, snapshot_data: bytes) -> str:
        path = os.path.join(self.base_dir, session_id)
        os.makedirs(path, exist_ok=True)
        
        snapshot_file = os.path.join(path, "env.pkl")
        with open(snapshot_file, "wb") as f:
            f.write(snapshot_data)
        
        return snapshot_file
    
    def load_snapshot(self, session_id: str) -> bytes:
        snapshot_file = os.path.join(self.base_dir, session_id, "env.pkl")
        with open(snapshot_file, "rb") as f:
            data = f.read()
        return data
    
    def delete_snapshot(self, session_id: str) -> None:
        snapshot_file = os.path.join(self.base_dir, session_id, "env.pkl")
        if os.path.exists(snapshot_file):
            os.remove(snapshot_file)
        # optionally remove the directory as well
        session_dir = os.path.join(self.base_dir, session_id)
        if os.path.isdir(session_dir):
            os.rmdir(session_dir)