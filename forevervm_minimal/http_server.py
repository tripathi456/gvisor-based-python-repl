# http_server.py

from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Singleton instance of session manager
_session_manager = None

def init_session_manager(manager):
    """Initialize the session manager singleton."""
    global _session_manager
    _session_manager = manager

def get_session_manager():
    """Get the session manager instance."""
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized")
    return _session_manager

@app.route("/session", methods=["POST"])
def create_session():
    session_id = get_session_manager().create_session()
    return jsonify({"session_id": session_id})

@app.route("/session/<session_id>/execute", methods=["POST"])
def execute_code(session_id):
    data = request.json
    code = data.get("code", "")
    try:
        output = get_session_manager().execute_code(session_id, code)
        return jsonify({"status": "ok", "output": output})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

def run_http_server(session_mgr, host="0.0.0.0", port=8000):
    init_session_manager(session_mgr)
    app.run(host=host, debug=True, port=port)