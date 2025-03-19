# ForeverVM Minimal

A minimal implementation of ForeverVM, a system that provides persistent Python REPL sessions using custom serialization.

## Overview

ForeverVM allows you to create Python REPL sessions that persist even after periods of inactivity. It uses custom serialization (pickle) to save the state of the Python environment and restore it when needed.

## Features

- **Session Persistence**: Sessions are automatically saved after a period of inactivity (10 minutes by default) and restored when needed.
- **Custom Serialization**: Uses Python's pickle module to serialize the session state.
- **HTTP API**: Provides a simple HTTP API for creating sessions and executing code.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/tripathi456/forevervm-minimal.git
   cd forevervm-minimal/forevervm_minimal
   ```

2. just run using `uv` (astral's python package manager)
   ```bash
   uv run main.py
   ```

## Usage

### Running the Server

```bash
python -m forevervm_minimal.main
```

This will start the HTTP server on port 8000.

### Testing the Server

The repository includes a test client that demonstrates session creation, code execution, and session persistence:

```bash
python test_client.py
```

The test client performs the following steps:
1. Creates a new session
2. Executes code to define variables
3. Modifies the session state
4. Waits for session inactivity timeout (configurable in config.py)
5. Verifies session restoration after inactivity

### API Endpoints

#### Create a Session

```bash
curl -X POST http://localhost:8000/session
```

Response:
```json
{
  "session_id": "unique-session-id"
}
```

#### Execute Code in a Session

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"code": "x = 1\nprint(x*2)"}' \
  http://localhost:8000/session/your-session-id/execute
```

Response:
```json
{
  "status": "ok",
  "output": "Executed: x = 1\nprint(x*2)\n"
}
```

### Configuration

Key settings can be configured through environment variables or in `config.py`:
- `FOREVERVM_SESSION_TIMEOUT`: Session inactivity timeout (default: 6 seconds)
- `FOREVERVM_CLEANUP_INTERVAL`: Interval to check for inactive sessions (default: 2 seconds)
- `FOREVERVM_PORT`: Server port (default: 8000)
- `FOREVERVM_HOST`: Server host (default: 0.0.0.0)

## Architecture

The system consists of several components:

- **SessionManager**: Manages session lifecycle (create, execute, snapshot, restore).
- **WorkerManager**: Manages a pool of workers (each worker is a separate Python REPL environment).
- **Worker**: Represents a single Python REPL environment.
- **SnapshotStorage**: Handles saving and loading session snapshots.
- **HTTP Server**: Provides a simple HTTP API for interacting with the system.

## Customization

You can customize the system by modifying the following parameters:

- **Inactivity Timeout**: Change the `inactivity_timeout` parameter in `SessionManager` to adjust how long a session can be inactive before it's snapshotted.
- **Worker Pool Size**: Change the `pool_size` parameter in `WorkerManager` to adjust the number of pre-spawned workers.
- **Snapshot Storage Location**: Change the `base_dir` parameter in `LocalFileStorage` to adjust where snapshots are stored.

## Security Considerations

This is a minimal implementation and does not include security features like authentication or rate limiting. In a production environment, you should add these features and run each worker in a secure environment (e.g., using gVisor or another container sandbox).