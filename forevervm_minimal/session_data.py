# session_data.py

class SessionData:
    def __init__(self, session_id, status, last_activity, worker, snapshot_path=None):
        self.session_id = session_id
        self.status = status  # active, snapshotted, snapshotting, restoring
        self.last_activity = last_activity
        self.worker = worker
        self.snapshot_path = snapshot_path