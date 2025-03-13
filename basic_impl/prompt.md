<__init__.py>
L1: # __init__.py
L2: # This file makes the directory a proper Python package
</__init__.py>

<custom_serializer.py>
L1: # custom_serializer.py
L2: 
L3: class Serializer:
L4:     """Optional: A wrapper around pickle or dill for easy swapping."""
L5:     # For now we do everything directly in worker.py
L6:     pass
</custom_serializer.py>

<http_server.py>
L1: # http_server.py
L2: 
L3: from flask import Flask, request, jsonify
L5: 
L6: app = Flask(__name__)
L7: 
L8: session_manager = None  # we'll set this from main.py
L9: 
L10: @app.route("/session", methods=["POST"])
L11: def create_session():
L12:     session_id = session_manager.create_session()
L13:     return jsonify({"session_id": session_id})
L14: 
L15: @app.route("/session/<session_id>/execute", methods=["POST"])
L16: def execute_code(session_id):
L17:     data = request.json
L18:     code = data.get("code", "")
L19:     try:
L20:         output = session_manager.execute_code(session_id, code)
L21:         return jsonify({"status": "ok", "output": output})
L22:     except Exception as e:
L23:         return jsonify({"status": "error", "error": str(e)}), 400
L24: 
L25: def run_http_server(host="0.0.0.0", port=8000):
L26:     app.run(host=host, port=port)
</http_server.py>

<main.py>
L1: # main.py
L2: 
L7: 
L8: # Add the parent directory to sys.path to allow absolute imports
L9: sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
L10: 
L11: from forevervm_minimal.session_manager import SessionManager
L12: from forevervm_minimal.snapshot_storage import LocalFileStorage
L13: from forevervm_minimal.worker_manager import WorkerManager
L14: from forevervm_minimal.http_server import run_http_server, app, session_manager as global_session_manager
L15: 
L16: def main():
L17:     storage = LocalFileStorage(base_dir="/var/forevervm/snapshots")
L18:     worker_manager = WorkerManager(pool_size=2)
L19:     session_manager = SessionManager(snapshot_storage=storage, worker_manager=worker_manager)
L20:     
L21:     # Provide session_manager to the Flask app
L22:     global global_session_manager
L23:     global_session_manager = session_manager
L24:     
L25:     # Start background thread for idle checking
L26:     def idle_check_loop():
L27:         while True:
L28:             time.sleep(60)  # check every minute
L29:             session_manager.checkpoint_idle_sessions()
L30:     
L31:     t = threading.Thread(target=idle_check_loop, daemon=True)
L32:     t.start()
L33:     
L34:     # Start the HTTP server
L35:     run_http_server()
L36: 
L37: if __name__ == "__main__":
L38:     main()
</main.py>

<session_data.py>
L1: # session_data.py
L2: 
L3: class SessionData:
L4:     def __init__(self, session_id, status, last_activity, worker, snapshot_path=None):
L5:         self.session_id = session_id
L6:         self.status = status  # active, snapshotted, snapshotting, restoring
L7:         self.last_activity = last_activity
L8:         self.worker = worker
L9:         self.snapshot_path = snapshot_path
</session_data.py>

<session_manager.py>
L1: # session_manager.py
L2: 
L6: 
L7: from forevervm_minimal.worker_manager import WorkerManager
L8: from forevervm_minimal.snapshot_storage import SnapshotStorage
L9: from forevervm_minimal.custom_serializer import Serializer
L10: from forevervm_minimal.session_data import SessionData
L11: 
L12: class SessionManager:
L13:     def __init__(self, snapshot_storage: SnapshotStorage, worker_manager: WorkerManager):
L14:         self.snapshot_storage = snapshot_storage
L15:         self.worker_manager = worker_manager
L16:         
L17:         self.sessions = {}  # dict: session_id -> SessionData
L18:         self.lock = threading.Lock()
L19:         
L20:         self.inactivity_timeout = 600  # 10 minutes, in seconds
L21:         
L22:     def create_session(self):
L23:         session_id = str(uuid.uuid4())
L24:         # create a new worker
L25:         worker = self.worker_manager.get_worker()
L26:         
L27:         # create SessionData object
L28:         session_data = SessionData(
L29:             session_id=session_id,
L30:             status="active",
L31:             last_activity=time.time(),
L32:             worker=worker,
L33:             snapshot_path=None
L34:         )
L35:         
L36:         with self.lock:
L37:             self.sessions[session_id] = session_data
L38:         
L39:         return session_id
L40: 
L41:     def execute_code(self, session_id, code):
L42:         with self.lock:
L43:             session_data = self.sessions.get(session_id)
L44:             if not session_data:
L45:                 raise ValueError(f"Session {session_id} not found.")
L46:         
L47:         # If session is snapshotted => restore
L48:         if session_data.status == "snapshotted":
L49:             self._restore_session(session_data)
L50:         
L51:         # Now session should be active and have a worker
L52:         output = session_data.worker.execute_code(code)
L53:         
L54:         # Update last activity
L55:         session_data.last_activity = time.time()
L56:         
L57:         return output
L58: 
L59:     def checkpoint_idle_sessions(self):
L60:         """Called periodically by a background thread."""
L61:         with self.lock:
L62:             now = time.time()
L63:             for session_data in self.sessions.values():
L64:                 if session_data.status == "active":
L65:                     if now - session_data.last_activity > self.inactivity_timeout:
L66:                         self._checkpoint_session(session_data)
L67: 
L68:     def _checkpoint_session(self, session_data):
L69:         # Mark status -> 'snapshotting' to avoid concurrency issues
L70:         session_data.status = "snapshotting"
L71:         
L72:         # Instruct the worker to produce a serialized environment
L73:         pickled_env = session_data.worker.serialize_environment()
L74:         
L75:         # Store the pickled data in snapshot_storage
L76:         snapshot_path = self.snapshot_storage.save_snapshot(session_data.session_id, pickled_env)
L77:         session_data.snapshot_path = snapshot_path
L78:         
L79:         # Release the worker
L80:         self.worker_manager.release_worker(session_data.worker)
L81:         session_data.worker = None
L82:         session_data.status = "snapshotted"
L83: 
L84:     def _restore_session(self, session_data):
L85:         # Mark status -> 'restoring'
L86:         session_data.status = "restoring"
L87:         
L88:         # get a new worker
L89:         worker = self.worker_manager.get_worker()
L90:         session_data.worker = worker
L91:         
L92:         # load the pickled environment
L93:         pickled_env = self.snapshot_storage.load_snapshot(session_data.session_id)
L94:         
L95:         # inject environment into worker
L96:         worker.restore_environment(pickled_env)
L97:         
L98:         # mark active
L99:         session_data.status = "active"
L100:         session_data.last_activity = time.time()
</session_manager.py>

<snapshot_storage.py>
L1: # snapshot_storage.py
L2: 
L5: 
L6: class SnapshotStorage(abc.ABC):
L7:     @abc.abstractmethod
L8:     def save_snapshot(self, session_id: str, snapshot_data: bytes) -> str:
L9:         """Save pickled environment. Return path or reference."""
L10:         pass
L11: 
L12:     @abc.abstractmethod
L13:     def load_snapshot(self, session_id: str) -> bytes:
L14:         """Load pickled environment from storage."""
L15:         pass
L16: 
L17:     @abc.abstractmethod
L18:     def delete_snapshot(self, session_id: str) -> None:
L19:         """Remove snapshot from storage."""
L20:         pass
L21: 
L22: 
L23: class LocalFileStorage(SnapshotStorage):
L24:     def __init__(self, base_dir="/var/forevervm/snapshots"):
L25:         self.base_dir = base_dir
L26:         os.makedirs(self.base_dir, exist_ok=True)
L27:     
L28:     def save_snapshot(self, session_id: str, snapshot_data: bytes) -> str:
L29:         path = os.path.join(self.base_dir, session_id)
L30:         os.makedirs(path, exist_ok=True)
L31:         
L32:         snapshot_file = os.path.join(path, "env.pkl")
L33:         with open(snapshot_file, "wb") as f:
L34:             f.write(snapshot_data)
L35:         
L36:         return snapshot_file
L37:     
L38:     def load_snapshot(self, session_id: str) -> bytes:
L39:         snapshot_file = os.path.join(self.base_dir, session_id, "env.pkl")
L40:         with open(snapshot_file, "rb") as f:
L41:             data = f.read()
L42:         return data
L43:     
L44:     def delete_snapshot(self, session_id: str) -> None:
L45:         snapshot_file = os.path.join(self.base_dir, session_id, "env.pkl")
L46:         if os.path.exists(snapshot_file):
L47:             os.remove(snapshot_file)
L48:         # optionally remove the directory as well
L49:         session_dir = os.path.join(self.base_dir, session_id)
L50:         if os.path.isdir(session_dir):
L51:             os.rmdir(session_dir)
</snapshot_storage.py>

<test_client.py>
L1: #!/usr/bin/env python3
L2: # test_client.py
L3: 
L7: 
L8: def main():
L9:     base_url = "http://localhost:8000"
L10:     
L11:     # Create a new session
L12:     print("Creating a new session...")
L13:     response = requests.post(f"{base_url}/session")
L14:     session_data = response.json()
L15:     session_id = session_data["session_id"]
L16:     print(f"Session created with ID: {session_id}")
L17:     
L18:     # Execute some code in the session
L19:     print("\nExecuting code to define a variable...")
L20:     code1 = "x = 42\nprint(f'x = {x}')"
L21:     response = requests.post(
L22:         f"{base_url}/session/{session_id}/execute",
L23:         json={"code": code1}
L24:     )
L25:     print(f"Response: {response.json()}")
L26:     
L27:     # Execute more code that uses the previously defined variable
L28:     print("\nExecuting code that uses the previously defined variable...")
L29:     code2 = "y = x * 2\nprint(f'y = {y}')"
L30:     response = requests.post(
L31:         f"{base_url}/session/{session_id}/execute",
L32:         json={"code": code2}
L33:     )
L34:     print(f"Response: {response.json()}")
L35:     
L36:     # Simulate inactivity (in a real scenario, you'd wait for the inactivity_timeout)
L37:     print("\nSimulating session inactivity...")
L38:     print("In a real scenario, you'd wait for the inactivity_timeout (10 minutes by default)")
L39:     print("For testing, you can modify the inactivity_timeout in session_manager.py to a smaller value")
L40:     
L41:     # Execute code after the "inactivity period" to demonstrate session persistence
L42:     print("\nExecuting code after the 'inactivity period'...")
L43:     code3 = "z = x + y\nprint(f'z = {z}')"
L44:     response = requests.post(
L45:         f"{base_url}/session/{session_id}/execute",
L46:         json={"code": code3}
L47:     )
L48:     print(f"Response: {response.json()}")
L49:     
L50:     print("\nTest completed successfully!")
L51: 
L52: if __name__ == "__main__":
L53:     main()
</test_client.py>

<worker.py>
L1: # worker.py
L2: 
L10: 
L11: class Worker:
L12:     def __init__(self):
L13:         # We'll store the environment as a dictionary (like 'globals()')
L14:         # that the user code interacts with
L15:         self.env = {}
L16:     
L17:     def execute_code(self, code):
L18:         # Execute code in self.env context and capture stdout
L19:         old_stdout = sys.stdout
L20:         redirected_output = io.StringIO()
L21:         sys.stdout = redirected_output
L22:         
L23:         result = None
L24:         
L25:         try:
L26:             # Try to compile as an expression first
L27:             try:
L28:                 compiled_code = compile(code, "<string>", "eval")
L29:                 result = eval(compiled_code, self.env)
L30:             except SyntaxError:
L31:                 # If it's not an expression, compile as a statement
L32:                 compiled_code = compile(code, "<string>", "exec")
L33:                 exec(compiled_code, self.env)
L34:             
L35:             # Get the stdout output
L36:             output = redirected_output.getvalue()
L37:             
L38:             # If there was a result from eval, add it to the output
L39:             if result is not None:
L40:                 if output and not output.endswith('\n'):
L41:                     output += '\n'
L42:                 output += f"Result: {result}\n"
L43:             
L44:             return f"Output:\n{output}" if output else "No output"
L45:         
L46:         except Exception as e:
L47:             # Get the traceback
L48:             error_traceback = traceback.format_exc()
L49:             return f"Error:\n{error_traceback}"
L50:         
L51:         finally:
L52:             # Restore stdout
L53:             sys.stdout = old_stdout
L54:     
L55:     def serialize_environment(self):
L56:         # Convert self.env into a pickle/dill
L57:         # We can store only the parts we want
L58:         return pickle.dumps(self.env)
L59:     
L60:     def restore_environment(self, pickled_env):
L61:         # Unpickle into self.env
L62:         self.env = pickle.loads(pickled_env)
L63:     
L64:     def terminate(self):
L65:         # If we had an external container, we'd do `docker stop` or similar
L66:         pass
</worker.py>

<worker_manager.py>
L1: # worker_manager.py
L2: 
L5: 
L6: from forevervm_minimal.worker import Worker
L7: 
L8: class WorkerManager:
L9:     def __init__(self, pool_size=2):
L10:         self.pool_size = pool_size
L11:         self.idle_workers = queue.Queue(maxsize=pool_size)
L12:         self.lock = threading.Lock()
L13:         
L14:         # Optionally pre-spawn a few workers
L15:         for _ in range(pool_size):
L16:             w = self._spawn_worker()
L17:             self.idle_workers.put(w)
L18:         
L19:     def get_worker(self):
L20:         try:
L21:             worker = self.idle_workers.get_nowait()
L22:         except queue.Empty:
L23:             # spawn on demand
L24:             worker = self._spawn_worker()
L25:         return worker
L26:     
L27:     def release_worker(self, worker):
L28:         # if there's room in idle queue, keep it
L29:         with self.lock:
L30:             if not self.idle_workers.full():
L31:                 self.idle_workers.put(worker)
L32:             else:
L33:                 # or tear down if no space
L34:                 worker.terminate()
L35:     
L36:     def _spawn_worker(self):
L37:         return Worker()
</worker_manager.py>

-------

What we want to achieve?

## 2. Overview of the Flow

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

------
INSTRUCTIONS:

you have to take a cue from the command

docker run --runtime=runsc --rm -it \
  -v "$(pwd)/server.py:/server.py" \
  -p 8000:8000 \
  python:3.9.21-alpine3.21 \
  python /server.py

So that the main.py you wrote can be run inside a docker (inside gvisor)


-------
