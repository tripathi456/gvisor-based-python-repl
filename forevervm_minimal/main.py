# main.py

import threading
import time
import sys
import os

# Add the parent directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forevervm_minimal.session_manager import SessionManager
from forevervm_minimal.snapshot_storage import LocalFileStorage
from forevervm_minimal.worker_manager import WorkerManager
from forevervm_minimal.http_server import run_http_server, app, session_manager as global_session_manager

def main():
    storage = LocalFileStorage(base_dir="/var/forevervm/snapshots")
    worker_manager = WorkerManager(pool_size=2)
    session_manager = SessionManager(snapshot_storage=storage, worker_manager=worker_manager)
    
    # Provide session_manager to the Flask app
    global global_session_manager
    global_session_manager = session_manager
    
    # Start background thread for idle checking
    def idle_check_loop():
        while True:
            time.sleep(60)  # check every minute
            session_manager.checkpoint_idle_sessions()
    
    t = threading.Thread(target=idle_check_loop, daemon=True)
    t.start()
    
    # Start the HTTP server
    run_http_server()

if __name__ == "__main__":
    main()