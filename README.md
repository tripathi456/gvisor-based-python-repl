# gVisor-based Python REPL

A secure, isolated Python REPL (Read-Eval-Print Loop) environment for executing untrusted code in LLM-based workflows.

## Introduction

This project provides a secure execution environment for running Python code in the context of Large Language Model (LLM) applications. It leverages gVisor, a container sandbox technology, to create an isolated execution environment that protects the host system from potentially malicious or unintended code execution.

The primary goal is to enable safe execution of user-provided or LLM-generated code while maintaining strong security boundaries. This is particularly important in AI applications where models might generate or execute code that could potentially harm the underlying system.

## Architecture

The system consists of several key components:

1. **TCP Server**: A Python TCP server that accepts code execution requests and maintains stateful sessions.
2. **Docker Container**: Provides containerization for the Python environment.
3. **gVisor Runtime**: Adds an additional layer of isolation by intercepting and filtering system calls.

The architecture follows a defense-in-depth approach, with multiple layers of isolation to prevent security breaches.

## File Descriptions

- `server.py`: The main Python file that implements both TCP and WebSocket servers which execute Python code sent via connections. It maintains stateful sessions with unique IDs, allowing variables and functions defined in one execution to be available in subsequent executions within the same session.
- `run.sh`: A shell script that runs the Python server inside a Docker container using gVisor's runsc runtime for isolation. It mounts the server.py file into the container and exposes ports 8000 (TCP) and 8001 (WebSocket).
- `test.sh`: A shell script that runs the test_tcp.py script to test the TCP server.
- `test_tcp.py`: A Python script that tests the TCP server by connecting to it, sending Python code to execute, and demonstrating session persistence.
- `test_ws.sh`: A shell script that runs the test_ws.py script to test the WebSocket server.
- `test_ws.py`: A Python script that tests the WebSocket server by connecting to it, sending Python code to execute, and demonstrating session persistence.
- `.gitignore`: A configuration file that specifies files to be ignored by version control.

## Setup Instructions

### Prerequisites

- Docker
- gVisor (runsc)

### Installation

1. Install gVisor:
   ```bash
   # Install runsc
   curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
   echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
   sudo apt-get update && sudo apt-get install -y runsc
   ```

2. Configure Docker to use gVisor:
   ```bash
   sudo mkdir -p /etc/docker
   cat <<EOF | sudo tee /etc/docker/daemon.json
   {
     "runtimes": {
       "runsc": {
         "path": "/usr/bin/runsc",
         "runtimeArgs": []
       }
     }
   }
   EOF
   sudo systemctl restart docker
   ```

3. Clone the repository:
   ```bash
   git clone https://github.com/username/gvisor-based-python-repl.git
   cd gvisor-based-python-repl
   ```

## Usage

### Running the Server

Execute the run.sh script to start the server:

```bash
./run.sh
```

This will start a Docker container with the Python server running on port 8000.

### Testing the Server

You can test the server using the provided test.sh script:

```bash
./test.sh
```

This will run the test_tcp.py script, which connects to the server, sends Python code to execute, and demonstrates session persistence.

### TCP Protocol

The server uses a simple protocol for communication:

1. **Message Format**: Each message (request or response) is prefixed with a 4-byte length field (big-endian), followed by the actual message content encoded as UTF-8 JSON.

2. **Request Format**:
   ```json
   {
     "code": "Python code to execute",
     "session_id": "optional-session-id"
   }
   ```

3. **Response Format**:
   ```json
   {
     "status": "ok|error",
     "output": "execution output (if status is ok)",
     "error": "error message (if status is error)",
     "session_id": "session-id"
   }
   ```

4. **Session Management**:
   - If no `session_id` is provided in the request, a new session is created with a unique ID.
   - If a `session_id` is provided, the code is executed in the context of that session.
   - If the provided `session_id` doesn't exist, an error is returned.

### WebSocket Protocol

The server also supports WebSocket connections on port 8001. The WebSocket protocol is simpler than the TCP protocol since WebSockets handle message framing automatically.

1. **Request Format**:
   ```json
   {
     "code": "Python code to execute",
     "session_id": "optional-session-id"
   }
   ```

2. **Response Format**:
   ```json
   {
     "status": "ok|error",
     "output": "execution output (if status is ok)",
     "error": "error message (if status is error)",
     "session_id": "session-id"
   }
   ```

3. **Session Management**:
   - If no `session_id` is provided in the request, a new session is created with a unique ID.
   - If a `session_id` is provided, the code is executed in the context of that session.
   - If the provided `session_id` doesn't exist, an error is returned.

### Testing WebSocket Connection

You can test the WebSocket connection using the provided test_ws.sh script:

```bash
./test_ws.sh
```

This will run the test_ws.py script, which connects to the server via WebSocket, sends Python code to execute, and demonstrates session persistence.

### Python WebSocket Client Example

Here's a simple example of how to use the server from Python with WebSockets:

```python
import asyncio
import websockets
import json

async def send_code(websocket, code, session_id=None):
    # Prepare request
    request = {"code": code}
    if session_id:
        request["session_id"] = session_id
    
    # Convert to JSON
    request_json = json.dumps(request)
    
    # Send the message
    await websocket.send(request_json)
    
    # Receive the response
    response_json = await websocket.recv()
    return json.loads(response_json)

async def main():
    # Connect to the server
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as websocket:
        # Receive initial greeting
        greeting = await websocket.recv()
        print(f"Server greeting: {greeting}")
        
        # Execute code in a new session
        response = await send_code(websocket, "x = 42\nprint(f'x = {x}')")
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Save the session ID for later use
        session_id = response.get("session_id")
        
        # Execute more code in the same session
        response = await send_code(websocket, "y = x * 2\nprint(f'y = {y}')", session_id)
        print(f"Response: {json.dumps(response, indent=2)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Python Client Example

Here's a simple example of how to use the server from Python:

```python
import socket
import json

def send_code(sock, code, session_id=None):
    # Prepare request
    request = {"code": code}
    if session_id:
        request["session_id"] = session_id
    
    # Convert to JSON and encode
    request_json = json.dumps(request)
    request_bytes = request_json.encode('utf-8')
    
    # Send message length first (4 bytes)
    length = len(request_bytes)
    sock.sendall(length.to_bytes(4, byteorder='big'))
    
    # Send the actual message
    sock.sendall(request_bytes)
    
    # Receive response length (4 bytes)
    length_bytes = sock.recv(4)
    message_length = int.from_bytes(length_bytes, byteorder='big')
    
    # Receive the actual response
    response_bytes = b''
    while len(response_bytes) < message_length:
        chunk = sock.recv(min(4096, message_length - len(response_bytes)))
        if not chunk:
            break
        response_bytes += chunk
    
    # Parse and return the response
    response_json = response_bytes.decode('utf-8')
    return json.loads(response_json)

# Connect to the server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 8000))

# Receive initial greeting
greeting = sock.recv(1024)
print(f"Server greeting: {greeting.decode('utf-8')}")

# Execute code in a new session
response = send_code(sock, "x = 42\nprint(f'x = {x}')")
print(f"Response: {json.dumps(response, indent=2)}")

# Save the session ID for later use
session_id = response.get("session_id")

# Execute more code in the same session
response = send_code(sock, "y = x * 2\nprint(f'y = {y}')", session_id)
print(f"Response: {json.dumps(response, indent=2)}")

# Close the connection
sock.close()
```

## Significance in LLM-based Workflows

This project addresses several key challenges in LLM-based workflows:

1. **Code Execution Safety**: Provides a secure environment for executing potentially untrusted code generated by LLMs.

2. **Persistent State**: Maintains state between executions through session management, allowing for multi-step code generation and execution workflows.

3. **Isolation**: Ensures that code execution cannot affect the host system, even if the code is malicious or contains vulnerabilities.

4. **Agentic Workflows**: Enables longer-running agentic workflows where LLMs can generate, execute, and iterate on code based on results.

5. **Reduced Context Window Usage**: By maintaining state between executions, there's no need to include the entire execution history in the LLM's context window.

## Security Considerations

This project implements several layers of security:

1. **Container Isolation**: Docker provides basic isolation from the host system.
2. **gVisor Sandbox**: Adds an additional layer of security by intercepting and filtering system calls.
3. **TCP Interface**: Limits interaction to a simple TCP API, reducing attack surface.

### Security Limitations

While this system provides strong isolation, it is not perfect:

- Side-channel attacks might still be possible
- Resource exhaustion could affect container performance
- New vulnerabilities in gVisor or Docker could compromise security

Regular updates and security audits are recommended.

## License

This project is licensed under the MIT License - see the LICENSE file for details.