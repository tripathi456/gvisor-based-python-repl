#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as websocket:
        # Send Python code to execute
        code = "print('Hello from WebSocket')"
        print(f"Sending code: {code}")
        await websocket.send(code)
        
        # Receive the result
        response = await websocket.recv()
        result = json.loads(response)
        
        print("Response status:", result["status"])
        if result["status"] == "ok":
            print("Output:", result["output"])
        else:
            print("Error:", result["error"])
        
        # Test with more complex code
        code = """
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

result = fibonacci(10)
print(f"The 10th Fibonacci number is {result}")
"""
        print(f"\nSending more complex code...")
        await websocket.send(code)
        
        # Receive the result
        response = await websocket.recv()
        result = json.loads(response)
        
        print("Response status:", result["status"])
        if result["status"] == "ok":
            print("Output:", result["output"])
        else:
            print("Error:", result["error"])

if __name__ == "__main__":
    asyncio.run(test_websocket())