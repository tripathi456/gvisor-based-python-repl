#!/usr/bin/env python3
import asyncio
import websockets
import json
import sys

async def send_receive(websocket, request_dict):
    """Send a request to the server and receive the response."""
    # Convert request to JSON
    request_json = json.dumps(request_dict)
    
    # Send the message
    await websocket.send(request_json)
    
    # Receive the response
    response_json = await websocket.recv()
    return json.loads(response_json)

async def main():
    # Server connection details
    host = "localhost"
    port = 8001  # WebSocket port
    uri = f"ws://{host}:{port}"
    
    try:
        # Connect to the server
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Receive initial greeting
            greeting = await websocket.recv()
            print(f"Server greeting: {greeting}")
            
            # Test 1: Execute code without a session ID (creates a new session)
            print("\n--- Test 1: Execute code without a session ID ---")
            response = await send_receive(websocket, {
                "code": "x = 42\nprint(f'x = {x}')"
            })
            print(f"Response: {json.dumps(response, indent=2)}")
            
            # Save the session ID for later use
            session_id = response.get("session_id")
            print(f"Session ID: {session_id}")
            
            # Test 2: Execute code in the same session (using the session ID)
            print("\n--- Test 2: Execute code in the same session ---")
            response = await send_receive(websocket, {
                "code": "y = x * 2\nprint(f'y = {y}')",
                "session_id": session_id
            })
            print(f"Response: {json.dumps(response, indent=2)}")
            
            # Test 3: Define a function in the session
            print("\n--- Test 3: Define a function in the session ---")
            response = await send_receive(websocket, {
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
            response = await send_receive(websocket, {
                "code": "print(greet('Python'))",
                "session_id": session_id
            })
            print(f"Response: {json.dumps(response, indent=2)}")
            
            # Test 5: Create a new session
            print("\n--- Test 5: Create a new session ---")
            response = await send_receive(websocket, {
                "code": "print('This is a new session')"
            })
            print(f"Response: {json.dumps(response, indent=2)}")
            new_session_id = response.get("session_id")
            print(f"New Session ID: {new_session_id}")
            
            # Test 6: Verify the new session doesn't have access to variables from the first session
            print("\n--- Test 6: Verify session isolation ---")
            response = await send_receive(websocket, {
                "code": "try:\n    print(f'x = {x}')\nexcept NameError as e:\n    print(f'Error: {e}')",
                "session_id": new_session_id
            })
            print(f"Response: {json.dumps(response, indent=2)}")
            
            # Test 7: Try to access a non-existent session
            print("\n--- Test 7: Try to access a non-existent session ---")
            response = await send_receive(websocket, {
                "code": "print('This should fail')",
                "session_id": "non-existent-session-id"
            })
            print(f"Response: {json.dumps(response, indent=2)}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())