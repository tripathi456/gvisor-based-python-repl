# gVisor-based Python REPL

A secure, isolated Python REPL (Read-Eval-Print Loop) environment for executing untrusted code in LLM-based workflows.

## Introduction

This project provides a secure execution environment for running Python code in the context of Large Language Model (LLM) applications. It leverages gVisor, a container sandbox technology, to create an isolated execution environment that protects the host system from potentially malicious or unintended code execution.

The primary goal is to enable safe execution of user-provided or LLM-generated code while maintaining strong security boundaries. This is particularly important in AI applications where models might generate or execute code that could potentially harm the underlying system.

## Architecture

The system consists of several key components:

1. **HTTP Server**: A simple Python HTTP server that accepts code via POST requests and executes it in a persistent environment.
2. **WebSocket Server**: A WebSocket server that allows for real-time code execution and result streaming.
3. **Docker Container**: Provides containerization for the Python environment.
4. **gVisor Runtime**: Adds an additional layer of isolation by intercepting and filtering system calls.

The architecture follows a defense-in-depth approach, with multiple layers of isolation to prevent security breaches.

## File Descriptions

- `server.py`: The main Python file that implements both HTTP and WebSocket servers for executing Python code. It maintains a persistent execution environment, allowing variables defined in one execution to be available in subsequent executions.
- `run.sh`: A shell script that runs the Python server inside a Docker container using gVisor's runsc runtime for isolation. It mounts the server.py file into the container and exposes ports 8000 (HTTP) and 8001 (WebSocket).
- `test.sh`: A simple shell script that tests the HTTP server by sending a POST request with Python code to execute.
- `test_ws.py`: A Python script that tests the WebSocket server by connecting to it and sending Python code to execute.
- `test_ws.sh`: A shell script that installs the required dependencies and runs the test_ws.py script.
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

This will start a Docker container with the Python server running on port 8000 (HTTP) and port 8001 (WebSocket).

### Command-line Arguments

The server supports the following command-line arguments:

- `--tcp`: Enable the HTTP server (default: enabled if neither --tcp nor --ws is specified)
- `--ws`: Enable the WebSocket server (default: enabled if neither --tcp nor --ws is specified)
- `--tcp-port PORT`: Set the HTTP server port (default: 8000)
- `--ws-port PORT`: Set the WebSocket server port (default: 8001)
- `--host HOST`: Set the host to bind to (default: 0.0.0.0)

Example:
```bash
python server.py --tcp --ws --tcp-port 8000 --ws-port 8001
```

### Testing the HTTP Server

You can test the HTTP server using the provided test.sh script:

```bash
./test.sh
```

This will send a simple Python print statement to the server and display the result.

### Testing the WebSocket Server

You can test the WebSocket server using the provided test_ws.sh script:

```bash
./test_ws.sh
```

This will connect to the WebSocket server, send Python code to execute, and display the results.

### API Usage

#### HTTP API

Send code to execute:

```bash
curl -X POST http://localhost:8000/exec -d "print('Hello, World!')"
```

Or using Python:

```python
import requests

code = """
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

result = fibonacci(10)
print(f"The 10th Fibonacci number is {result}")
"""

response = requests.post(
    "http://localhost:8000/exec",
    data=code
)

print(response.json())
```

#### WebSocket API

Connect to the WebSocket server and send code to execute:

```python
import asyncio
import websockets
import json

async def execute_code():
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as websocket:
        # Send Python code to execute
        code = "print('Hello from WebSocket')"
        await websocket.send(code)
        
        # Receive the result
        response = await websocket.recv()
        result = json.loads(response)
        
        print("Response status:", result["status"])
        if result["status"] == "ok":
            print("Output:", result["output"])
        else:
            print("Error:", result["error"])

asyncio.run(execute_code())
```

## Significance in LLM-based Workflows

This project addresses several key challenges in LLM-based workflows:

1. **Code Execution Safety**: Provides a secure environment for executing potentially untrusted code generated by LLMs.

2. **Persistent State**: Maintains state between executions, allowing for multi-step code generation and execution workflows.

3. **Isolation**: Ensures that code execution cannot affect the host system, even if the code is malicious or contains vulnerabilities.

4. **Agentic Workflows**: Enables longer-running agentic workflows where LLMs can generate, execute, and iterate on code based on results.

5. **Reduced Context Window Usage**: By maintaining state between executions, there's no need to include the entire execution history in the LLM's context window.

6. **Multiple Connection Methods**: Supports both HTTP and WebSocket connections, allowing for different integration patterns based on the use case.

## Security Considerations

This project implements several layers of security:

1. **Container Isolation**: Docker provides basic isolation from the host system.
2. **gVisor Sandbox**: Adds an additional layer of security by intercepting and filtering system calls.
3. **HTTP/WebSocket Interface**: Limits interaction to simple HTTP and WebSocket APIs, reducing attack surface.

### Security Limitations

While this system provides strong isolation, it is not perfect:

- Side-channel attacks might still be possible
- Resource exhaustion could affect container performance
- New vulnerabilities in gVisor or Docker could compromise security

Regular updates and security audits are recommended.

## License

This project is licensed under the MIT License - see the LICENSE file for details.