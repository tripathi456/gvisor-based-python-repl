# worker_manager.py

import queue
import threading

from forevervm_minimal.worker import Worker

class WorkerManager:
    def __init__(self, pool_size=2):
        self.pool_size = pool_size
        self.idle_workers = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        
        # Optionally pre-spawn a few workers
        for _ in range(pool_size):
            w = self._spawn_worker()
            self.idle_workers.put(w)
        
    def get_worker(self):
        try:
            worker = self.idle_workers.get_nowait()
        except queue.Empty:
            # spawn on demand
            worker = self._spawn_worker()
        return worker
    
    def release_worker(self, worker):
        # if there's room in idle queue, keep it
        with self.lock:
            if not self.idle_workers.full():
                self.idle_workers.put(worker)
            else:
                # or tear down if no space
                worker.terminate()
    
    def _spawn_worker(self):
        return Worker()