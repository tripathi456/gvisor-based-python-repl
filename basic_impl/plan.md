Below is an updated **ForeverVM** code plan that relies on a **custom serialization** approach rather than CRIU. The overall architecture remains similar (managing sessions, worker processes, and snapshots), but our **snapshot/restore** logic will revolve around **serializing Python’s REPL state** (global environment) instead of checkpointing an entire process. This means that only Python objects (variables, functions, classes, etc.) are preserved—not OS-level resources like open file descriptors or running threads.  

---

## 1. High-Level Changes

1. **No CRIU Dependency**  
   - We will **not** attempt to snapshot the entire Python process at the OS level.  
   - Instead, we’ll serialize Python objects (e.g., the `globals()` dict used by each session’s REPL).  

2. **Python Environment Serialization**  
   - We can use `pickle` or `dill` (a superset of pickle that handles more Python object types) to persist the session’s Python state to disk.  
   - On restore, we start a fresh Python interpreter in a new worker container/process, then **load** (un-pickle) the environment and inject it into that interpreter’s `globals()`.  

3. **Implications**  
   - Not all Python objects can be pickled (e.g., open file handles, certain C-extensions).  
   - This approach should be sufficient for typical REPL use cases (variables, functions, etc.), but any code using un-picklable resources might break upon restore.  
   - We still use **gVisor** for security and resource isolation.  

4. **Architecture**  
   - Almost the same as the previous plan, except we replace the “CRIU” module with a “custom serializer” module.  
   - The rest of the system (session manager, worker manager, storage, transport) remains very similar.

---

## 2. Overview of the New Flow

1. **User Code Execution**  
   - When the user executes code for session S, we run it in a Python REPL environment inside a worker. This environment is basically a dictionary of `globals()`, plus some helper code.

2. **Snapshot** (after 10 minutes inactivity)  
   - The session manager instructs the worker to **serialize** all relevant state (the environment dictionary, i.e., `globals()` or a specialized data structure) into a pickle/dill file.  
   - We store that file on disk using our `SnapshotStorage` interface, e.g. in `/var/forevervm/snapshots/<session_id>/session.pkl`.  
   - The worker is terminated or returned to a pool (with a fresh interpreter, not tied to the old environment).

3. **Restore** (on next request)  
   - Session manager obtains a new worker instance (fresh Python interpreter).  
   - Loads the saved pickle file from disk and unpickles it to obtain the environment dictionary.  
   - Injects that dictionary into the new Python REPL’s `globals()` so that the session picks up exactly where it left off in terms of Python variables, function definitions, etc.  

4. **Execution Continues**  
   - The user sees the same session state.  

---

## 3. Detailed Module Structure

Below is the revised module layout, focusing on custom serialization in place of CRIU calls.

### 3.1 `session_manager.py`
Manages session lifecycle (create, execute, snapshot, restore).

```python
# session_manager.py

import threading
import time
import uuid

from .worker_manager import WorkerManager
from .snapshot_storage import SnapshotStorage
from .custom_serializer import Serializer
from .session_data import SessionData

class SessionManager:
    def __init__(self, snapshot_storage: SnapshotStorage, worker_manager: WorkerManager):
        self.snapshot_storage = snapshot_storage
        self.worker_manager = worker_manager
        
        self.sessions = {}  # dict: session_id -> SessionData
        self.lock = threading.Lock()
        
        self.inactivity_timeout = 600  # 10 minutes, in seconds
        
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
```

### 3.2 `session_data.py`
A simple data class to hold session metadata.

```python
# session_data.py

class SessionData:
    def __init__(self, session_id, status, last_activity, worker, snapshot_path=None):
        self.session_id = session_id
        self.status = status  # active, snapshotted, snapshotting, restoring
        self.last_activity = last_activity
        self.worker = worker
        self.snapshot_path = snapshot_path
```

### 3.3 `worker_manager.py`
Manages a pool of workers (each worker is a separate Python REPL environment under gVisor).

```python
# worker_manager.py

import queue
import threading

from .worker import Worker

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

```

### 3.4 `worker.py`
Represents a single sandboxed Python REPL environment (using gVisor for isolation).  
Instead of CRIU, we have `serialize_environment()` and `restore_environment()`.

```python
# worker.py

import subprocess
import pickle
import time
import threading
import os

# For a real gVisor approach, you'd run a Docker container with --runtime=runsc.
# However, here we’ll conceptually wrap it.
# We'll assume we have a local Python process started in a container, and we can talk to it
# via a small server or direct method calls if they're in the same process (for demonstration).
# 
# For a production approach, you'd talk to a container via RPC, e.g.:
#   docker run --rm --runtime=runsc python:3.9 ...
# Then attach to a small server inside that container that runs code. 
# This example is a simplified single-process approach.

class Worker:
    def __init__(self):
        # We'll store the environment as a dictionary (like 'globals()')
        # that the user code interacts with
        self.env = {}
    
    def execute_code(self, code):
        # Execute code in self.env context
        try:
            output_buffer = []
            
            # We can redirect stdout, etc. for capturing
            exec_locals = {}
            exec(code, self.env, exec_locals)
            
            # gather any print statements or returned values as needed
            # for simplicity, we'll assume the code prints to stdout or modifies self.env
            # We'll return the final environment's string representation or something
            # In practice, you'd capture prints via io.StringIO or something
            return f"Executed: {code}\n"
        
        except Exception as e:
            return f"Error: {str(e)}\n"
    
    def serialize_environment(self):
        # Convert self.env into a pickle/dill
        # We can store only the parts we want
        return pickle.dumps(self.env)
    
    def restore_environment(self, pickled_env):
        # Unpickle into self.env
        self.env = pickle.loads(pickled_env)
    
    def terminate(self):
        # If we had an external container, we'd do `docker stop` or similar
        pass
```

### 3.5 `snapshot_storage.py`
The snapshot interface now deals with **binary data** (pickled environment) instead of CRIU dump files.

```python
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
```

### 3.6 `custom_serializer.py`
*(Optional)* If you want a dedicated module for controlling pickling, especially if you might switch from `pickle` to `dill`, or add custom logic:

```python
# custom_serializer.py

class Serializer:
    """Optional: A wrapper around pickle or dill for easy swapping."""
    # For now we do everything directly in worker.py
    pass
```

### 3.7 `http_server.py` (Transport Layer - HTTP)
Uses a simple Flask app to expose `POST /session` and `POST /session/<id>/execute`.

```python
# http_server.py

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

session_manager = None  # we’ll set this from main.py

@app.route("/session", methods=["POST"])
def create_session():
    session_id = session_manager.create_session()
    return jsonify({"session_id": session_id})

@app.route("/session/<session_id>/execute", methods=["POST"])
def execute_code(session_id):
    data = request.json
    code = data.get("code", "")
    try:
        output = session_manager.execute_code(session_id, code)
        return jsonify({"status": "ok", "output": output})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

def run_http_server(host="0.0.0.0", port=8000):
    app.run(host=host, port=port)
```

### 3.8 `main.py`
Initializes everything and starts the system.

```python
# main.py

import threading
import time

from .session_manager import SessionManager
from .snapshot_storage import LocalFileStorage
from .worker_manager import WorkerManager
from .http_server import run_http_server, app

def main():
    storage = LocalFileStorage(base_dir="/var/forevervm/snapshots")
    worker_manager = WorkerManager(pool_size=2)
    session_manager = SessionManager(snapshot_storage=storage, worker_manager=worker_manager)
    
    # Provide session_manager to the Flask app
    from .http_server import session_manager as global_session_manager
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
```

---

## 4. Implementation Instructions for an AI Agent or Developer

Below are step-by-step instructions to build and run this custom serialization approach:

1. **Set Up Your Python Environment**  
   - Create a virtual environment with Python 3.9+ (preferably).  
   - `pip install flask dill` (or just `pip install flask` and rely on `pickle` if that suffices).  

2. **Create the Package Structure**  
   - Make a folder `forevervm/` containing the Python modules (`session_manager.py`, `worker_manager.py`, `worker.py`, `snapshot_storage.py`, `session_data.py`, `custom_serializer.py`, and `http_server.py`).  
   - In `main.py`, import these modules and assemble them as shown.  

3. **Use gVisor** (Optional for Now)  
   - If you want to run each worker inside a gVisor container, you need to orchestrate Docker with `--runtime=runsc`.  
   - A full integration involves a real container-based `Worker` that communicates with a small server or uses `exec` to run code inside the container.  
   - For proof-of-concept, you can keep `Worker` as a local object.  

4. **Implement Worker-Container Integration** (If needed)  
   - If you want each `Worker` to be an actual container, you might have:  
     ```python
     def _spawn_worker(self):
         # Launch container with runsc:
         # e.g., docker run -d --runtime=runsc --name=... python:3.9-slim tail -f /dev/null
         # Then return a Worker object with container_id = ...
     ```  
   - For executing code inside it, you might do:  
     ```python
     def execute_code(self, code):
         # docker exec <container_id> python -c <code>
         # capture output
     ```  
   - For serialization, you might store the environment in a volume or a shared path the container can read/write.  

5. **Test the Basic Flow**  
   - Run `python main.py` (or however you orchestrate it).  
   - `POST /session` to create a session:  
     ```bash
     curl -X POST http://localhost:8000/session
     ```  
   - Copy the returned `session_id`.  
   - `POST /session/<session_id>/execute` with a JSON body:  
     ```bash
     curl -X POST -H "Content-Type: application/json" \
        -d '{"code": "x = 1\nprint(x*2)"}' \
        http://localhost:8000/session/<session_id>/execute
     ```  
   - Wait 10+ minutes (or lower inactivity threshold for quick testing), then call `execute` again. The session manager should have snapshotted the environment, killed the worker, and now must restore it. Check logs to ensure environment is reloaded.  

6. **Enhance & Debug**  
   - Ensure the pickling approach works for typical Python code (variables, functions). If you need advanced features (like lambdas, classes, closures), consider `dill` instead of `pickle`.  
   - If code references un-picklable state (like open sockets), you’ll need to handle that gracefully (the user’s code might break upon restore).  

7. **Security**  
   - For a real deployment, ensure you run each worker in a secure environment (e.g. gVisor container).  
   - Add authentication, rate limiting, etc. to the HTTP layer if needed.  

8. **Scale & Productionize**  
   - Implement logging, metrics, and error handling.  
   - Consider a more robust storage solution (like S3) if needed.  
   - Add concurrency controls if many sessions are created or executed in parallel.  

---

## 5. Summary

This plan removes the dependency on CRIU and **instead** uses Python’s built-in (or extended) serialization to store and restore the session’s dictionary-based environment. While this won’t preserve true OS-level process state, it will preserve Python variables, functions, and modules well enough for most REPL-driven logic. The rest of the architecture (session management, transport interface, worker pool, etc.) remains effectively the same.

By following these steps, an AI agent or any developer can implement and test a custom Python-based serialization approach for “ForeverVM,” giving a persistent REPL experience—while still leveraging gVisor for sandboxing and an HTTP server as a transport.

-----

CREATE A NEW FOLDER - forevervm-minimal 
AND 
implement the above instructions.