#!/usr/bin/env python3
# test_client.py

import requests
import json
import time

def main():
    base_url = "http://localhost:8000"
    
    # Create a new session
    print("Creating a new session...")
    response = requests.post(f"{base_url}/session")
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"Session created with ID: {session_id}")
    
    # Execute some code in the session
    print("\nExecuting code to define a variable...")
    code1 = "x = 42\nprint(f'x = {x}')"
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code1}
    )
    print(f"Response: {response.json()}")
    
    # Execute more code that uses the previously defined variable
    print("\nExecuting code that uses the previously defined variable...")
    code2 = "y = x * 2\nprint(f'y = {y}')"
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code2}
    )
    print(f"Response: {response.json()}")
    
    # Simulate inactivity (in a real scenario, you'd wait for the inactivity_timeout)
    print("\nSimulating session inactivity...")
    print("In a real scenario, you'd wait for the inactivity_timeout (10 minutes by default)")
    print("For testing, you can modify the inactivity_timeout in session_manager.py to a smaller value")
    
    # Execute code after the "inactivity period" to demonstrate session persistence
    print("\nExecuting code after the 'inactivity period'...")
    code3 = "z = x + y\nprint(f'z = {z}')"
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code3}
    )
    print(f"Response: {response.json()}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()