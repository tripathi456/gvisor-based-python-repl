#!/usr/bin/env python3
import socket
import json
import sys
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import print as rprint

# Create a Rich console object
console = Console()

def send_receive(sock, request_dict):
    """Send a request to the server and receive the response."""
    # Convert request to JSON and encode
    request_json = json.dumps(request_dict)
    request_bytes = request_json.encode('utf-8')
    
    # Send message length first (4 bytes)
    length = len(request_bytes)
    sock.sendall(length.to_bytes(4, byteorder='big'))
    
    # Send the actual message
    sock.sendall(request_bytes)
    
    # Receive response length (4 bytes)
    length_bytes = sock.recv(4)
    if not length_bytes:
        return None
    
    # Convert bytes to integer
    message_length = int.from_bytes(length_bytes, byteorder='big')
    
    # Receive the actual response
    chunks = []
    bytes_received = 0
    while bytes_received < message_length:
        chunk = sock.recv(min(4096, message_length - bytes_received))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data")
        chunks.append(chunk)
        bytes_received += len(chunk)
    
    response_json = b''.join(chunks).decode('utf-8')
    return json.loads(response_json)

def receive_response(sock):
    """Receive a response from the server using the length-prefixed protocol."""
    # Receive response length (4 bytes)
    length_bytes = sock.recv(4)
    if not length_bytes:
        return None
    
    # Convert bytes to integer
    message_length = int.from_bytes(length_bytes, byteorder='big')
    
    # Receive the actual response
    chunks = []
    bytes_received = 0
    while bytes_received < message_length:
        chunk = sock.recv(min(4096, message_length - bytes_received))
        if not chunk:
            raise ConnectionError("Connection closed while receiving data")
        chunks.append(chunk)
        bytes_received += len(chunk)
    
    response_json = b''.join(chunks).decode('utf-8')
    return json.loads(response_json)

def display_response(response, title="Response"):
    """Display a response using Rich formatting."""
    # Create a table for the response
    table = Table(title=title)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in response.items():
        if key == "output":
            # Format output as a panel
            table.add_row(key, Panel(value.strip(), border_style="blue"))
        elif key == "error":
            # Format error with red text
            table.add_row(key, f"[bold red]{value}[/bold red]")
        else:
            # Format other values normally
            table.add_row(key, str(value))
    
    console.print(table)

def main():
    # Server connection details
    host = "localhost"
    port = 8000
    
    # Create a socket and connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        console.print(f"Connected to [bold]{host}:{port}[/bold]", style="green")
        
        # Receive initial greeting using the length-prefixed protocol
        greeting = receive_response(sock)
        console.print(Panel(Syntax(json.dumps(greeting, indent=2), "json", theme="monokai"), 
                           title="Server Greeting", border_style="green"))
        
        # Test 1: Execute code without a session ID (creates a new session)
        console.rule("[bold]Test 1: Execute code without a session ID[/bold]")
        response = send_receive(sock, {
            "code": "x = 42\nprint(f'x = {x}')"
        })
        display_response(response, "Test 1 Response")
        
        # Save the session ID for later use
        session_id = response.get("session_id")
        console.print(f"Session ID: [bold cyan]{session_id}[/bold cyan]")
        
        # Test 2: Execute code in the same session (using the session ID)
        console.rule("[bold]Test 2: Execute code in the same session[/bold]")
        response = send_receive(sock, {
            "code": "y = x * 2\nprint(f'y = {y}')",
            "session_id": session_id
        })
        display_response(response, "Test 2 Response")
        
        # Test 3: Define a function in the session
        console.rule("[bold]Test 3: Define a function in the session[/bold]")
        response = send_receive(sock, {
            "code": """
def greet(name):
    return f"Hello, {name}!"
print(greet("World"))
""",
            "session_id": session_id
        })
        display_response(response, "Test 3 Response")
        
        # Test 4: Call the function defined in the previous request
        console.rule("[bold]Test 4: Call the function defined in the previous request[/bold]")
        response = send_receive(sock, {
            "code": "print(greet('Python'))",
            "session_id": session_id
        })
        display_response(response, "Test 4 Response")
        
        # Test 5: Create a new session
        console.rule("[bold]Test 5: Create a new session[/bold]")
        response = send_receive(sock, {
            "code": "print('This is a new session')"
        })
        display_response(response, "Test 5 Response")
        new_session_id = response.get("session_id")
        console.print(f"New Session ID: [bold cyan]{new_session_id}[/bold cyan]")
        
        # Test 6: Verify the new session doesn't have access to variables from the first session
        console.rule("[bold]Test 6: Verify session isolation[/bold]")
        response = send_receive(sock, {
            "code": "try:\n    print(f'x = {x}')\nexcept NameError as e:\n    print(f'Error: {e}')",
            "session_id": new_session_id
        })
        display_response(response, "Test 6 Response")
        
        # Test 7: Try to access a non-existent session
        console.rule("[bold]Test 7: Try to access a non-existent session[/bold]")
        response = send_receive(sock, {
            "code": "print('This should fail')",
            "session_id": "non-existent-session-id"
        })
        display_response(response, "Test 7 Response")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
    finally:
        sock.close()
        console.print("Connection closed", style="yellow")

if __name__ == "__main__":
    main()