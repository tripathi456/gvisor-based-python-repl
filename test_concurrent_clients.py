#!/usr/bin/env python3
import socket
import json
import sys
import threading
import time
import uuid

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

def client_session(client_id, results):
    """Run a client session that connects to the server and executes code."""
    # Server connection details
    host = "localhost"
    port = 8000
    
    # Create a socket and connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    session_id = None
    
    try:
        sock.connect((host, port))
        print(f"Client {client_id}: Connected to {host}:{port}")
        
        # Receive initial greeting
        greeting = receive_response(sock)
        print(f"Client {client_id}: Server greeting received")
        
        # Step 1: Create a new session by executing code
        print(f"Client {client_id}: Creating a new session")
        response = send_receive(sock, {
            "code": f"client_id = '{client_id}'\nprint(f'Client {client_id} initialized')"
        })
        session_id = response.get("session_id")
        print(f"Client {client_id}: Session ID: {session_id}")
        results[client_id]["session_id"] = session_id
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 2: Define a function in the session
        print(f"Client {client_id}: Defining a function")
        response = send_receive(sock, {
            "code": f"""
def get_client_info():
    return f"This is client {client_id} with session {{{session_id}}}"
print(get_client_info())
""",
            "session_id": session_id
        })
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 3: Create a unique variable for this client with a client-specific name
        print(f"Client {client_id}: Creating a unique variable")
        unique_value = uuid.uuid4().hex[:8]
        var_name = f"unique_value_{client_id}"  # Use client-specific variable names
        response = send_receive(sock, {
            "code": f"{var_name} = '{unique_value}'\nprint(f'Set {var_name} to {{{var_name}}}')",
            "session_id": session_id
        })
        results[client_id]["unique_value"] = unique_value
        results[client_id]["var_name"] = var_name
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 4: Sleep to simulate concurrent work
        time.sleep(1)
        
        # Step 5: Verify the unique variable is still correct
        print(f"Client {client_id}: Verifying unique variable")
        response = send_receive(sock, {
            "code": f"print(f'{var_name} is {{{var_name}}}')",
            "session_id": session_id
        })
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 6: Try to access the other client's session (should fail)
        # We'll attempt this in the main function after both threads complete
        
    except Exception as e:
        print(f"Client {client_id}: Error: {e}")
        results[client_id]["error"] = str(e)
    finally:
        sock.close()
        print(f"Client {client_id}: Connection closed")

def main():
    # Dictionary to store results from both clients
    results = {
        "A": {"session_id": None, "unique_value": None, "var_name": None, "outputs": [], "error": None},
        "B": {"session_id": None, "unique_value": None, "var_name": None, "outputs": [], "error": None}
    }
    
    # Create and start two client threads
    thread_a = threading.Thread(target=client_session, args=("A", results))
    thread_b = threading.Thread(target=client_session, args=("B", results))
    
    print("Starting client threads...")
    thread_a.start()
    thread_b.start()
    
    # Wait for both threads to complete
    thread_a.join()
    thread_b.join()
    print("Both client threads completed")
    
    # Now test cross-session access with a third connection
    print("\n--- Testing Cross-Session Access ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(("localhost", 8000))
        
        # Skip greeting
        receive_response(sock)
        
        # Try to access Client A's unique value from Client B's session
        session_a = results["A"]["session_id"]
        session_b = results["B"]["session_id"]
        unique_value_a = results["A"]["unique_value"]
        unique_value_b = results["B"]["unique_value"]
        var_name_a = results["A"]["var_name"]
        var_name_b = results["B"]["var_name"]
        
        print(f"Attempting to access Client A's variable '{var_name_a}' from Client B's session")
        response = send_receive(sock, {
            "code": f"try:\n    print(f'Client A variable {var_name_a}: {{{var_name_a}}}')\nexcept NameError as e:\n    print(f'Error: {{e}}')",
            "session_id": session_b
        })
        cross_session_result_a = response.get("output", "")
        print(f"Result: {cross_session_result_a}")
        
        # Also try to access Client B's variable from Client B's session (should succeed)
        print(f"Attempting to access Client B's variable '{var_name_b}' from Client B's session (should succeed)")
        response = send_receive(sock, {
            "code": f"try:\n    print(f'Client B variable {var_name_b}: {{{var_name_b}}}')\nexcept NameError as e:\n    print(f'Error: {{e}}')",
            "session_id": session_b
        })
        same_session_result = response.get("output", "")
        print(f"Result: {same_session_result}")
        
        # Print summary of results
        print("\n--- Test Results Summary ---")
        print(f"Client A Session ID: {session_a}")
        print(f"Client A Variable Name: {var_name_a}")
        print(f"Client A Unique Value: {unique_value_a}")
        print(f"Client A Outputs:")
        for i, output in enumerate(results["A"]["outputs"]):
            print(f"  Step {i+1}: {output.strip()}")
        
        print(f"\nClient B Session ID: {session_b}")
        print(f"Client B Variable Name: {var_name_b}")
        print(f"Client B Unique Value: {unique_value_b}")
        print(f"Client B Outputs:")
        for i, output in enumerate(results["B"]["outputs"]):
            print(f"  Step {i+1}: {output.strip()}")
        
        print(f"\nCross-Session Access Result (B trying to access A's variable): {cross_session_result_a.strip()}")
        print(f"Same-Session Access Result (B accessing its own variable): {same_session_result.strip()}")
        
        # Verify session isolation
        if "Error: name '" + var_name_a + "' is not defined" in cross_session_result_a:
            print("\nSession isolation verified: Client B cannot access Client A's variables")
        else:
            print("\nWARNING: Session isolation may be compromised!")
        
    except Exception as e:
        print(f"Error in cross-session test: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
