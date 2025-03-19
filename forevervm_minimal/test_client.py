#!/usr/bin/env python3
# test_client.py

import requests
import json
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    base_url = "http://localhost:8000"
    
    # Create a new session
    logger.info("Creating a new session...")
    response = requests.post(f"{base_url}/session")
    session_data = response.json()
    session_id = session_data["session_id"]
    logger.info(f"Session created with ID: {session_id}")
    
    # Execute some code in the session
    logger.info("\nStep 1: Defining initial variables...")
    code1 = """
x = 42
y = [1, 2, 3]
print(f'Initial state: x = {x}, y = {y}')
"""
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code1}
    )
    logger.info(f"Response: {response.json()}")
    
    # Execute more code to verify state
    logger.info("\nStep 2: Verifying variable state...")
    code2 = """
y.append(x)
print(f'Updated state: y = {y}')
"""
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code2}
    )
    logger.info(f"Response: {response.json()}")
    
    # Wait for session inactivity timeout
    inactivity_period = 8  # seconds (longer than SESSION_INACTIVITY_TIMEOUT)
    logger.info(f"\nStep 3: Simulating inactivity for {inactivity_period} seconds...")
    logger.info("Session should be checkpointed during this time")
    time.sleep(inactivity_period)
    
    # Execute code after inactivity to verify session restoration
    logger.info("\nStep 4: Testing session restoration...")
    code3 = """
print(f'Restored state: x = {x}, y = {y}')
z = sum(y)
print(f'New computation: sum(y) = {z}')
"""
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code3}
    )
    logger.info(f"Response: {response.json()}")
    
    # Final verification
    logger.info("\nStep 5: Final state verification...")
    code4 = """
print(f'Final state check:')
print(f'x = {x}')
print(f'y = {y}')
print(f'z = {z}')
"""
    response = requests.post(
        f"{base_url}/session/{session_id}/execute",
        json={"code": code4}
    )
    logger.info(f"Response: {response.json()}")
    
    logger.info("\nTest completed successfully!")

if __name__ == "__main__":
    main()