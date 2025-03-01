#!/usr/bin/env python3
import socket
import json
import sys

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

def main():
    # Server connection details
    host = "localhost"
    port = 8000
    
    # Create a socket and connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")
        
        # Receive initial greeting using the length-prefixed protocol
        greeting = receive_response(sock)
        print(f"Server greeting: {json.dumps(greeting, indent=2)}")
        
        # Test 1: Execute code without a session ID (creates a new session)
        print("\n--- Test 1: Execute code without a session ID ---")
        response = send_receive(sock, {
            "code": "x = 42\nprint(f'x = {x}')"
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Save the session ID for later use
        session_id = response.get("session_id")
        print(f"Session ID: {session_id}")
        
        # Test 2: Execute code in the same session (using the session ID)
        print("\n--- Test 2: Execute code in the same session ---")
        response = send_receive(sock, {
            "code": "y = x * 2\nprint(f'y = {y}')",
            "session_id": session_id
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Test 3: Define a function in the session
        print("\n--- Test 3: Define a function in the session ---")
        response = send_receive(sock, {
            "code": """
def greet(name):
    return f"Hello, {name}!"
print(greet("World"))
""",
            "session_id": session_id
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Test 4: Call the function defined in the previous request
        print("\n--- Test 4: Call the function defined in the previous request ---")
        response = send_receive(sock, {
            "code": "print(greet('Python'))",
            "session_id": session_id
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Test 5: Create a new session
        print("\n--- Test 5: Create a new session ---")
        response = send_receive(sock, {
            "code": "print('This is a new session')"
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        new_session_id = response.get("session_id")
        print(f"New Session ID: {new_session_id}")
        
        # Test 6: Verify the new session doesn't have access to variables from the first session
        print("\n--- Test 6: Verify session isolation ---")
        response = send_receive(sock, {
            "code": "try:\n    print(f'x = {x}')\nexcept NameError as e:\n    print(f'Error: {e}')",
            "session_id": new_session_id
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        
        # Test 7: Try to access a non-existent session
        print("\n--- Test 7: Try to access a non-existent session ---")
        response = send_receive(sock, {
            "code": "print('This should fail')",
            "session_id": "non-existent-session-id"
        })
        print(f"Response: {json.dumps(response, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()
        print("Connection closed")

if __name__ == "__main__":
    main()