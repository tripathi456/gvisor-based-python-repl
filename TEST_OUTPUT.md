in first terminal 

```bash
bash run.sh
```

---

in second terminal 

```bash
❯ python test_tcp.py
Connected to localhost:8000
Server greeting: {
  "status": "ok",
  "message": "Python REPL Server. Send JSON with 'code' to execute. Optional 'session_id' to continue a session."
}

--- Test 1: Execute code without a session ID ---
Response: {
  "status": "ok",
  "output": "x = 42\n",
  "session_id": "e9506d65-4fd5-416d-9f11-f33fa8e29ce7"
}
Session ID: e9506d65-4fd5-416d-9f11-f33fa8e29ce7

--- Test 2: Execute code in the same session ---
Response: {
  "status": "ok",
  "output": "y = 84\n",
  "session_id": "e9506d65-4fd5-416d-9f11-f33fa8e29ce7"
}

--- Test 3: Define a function in the session ---
Response: {
  "status": "ok",
  "output": "Hello, World!\n",
  "session_id": "e9506d65-4fd5-416d-9f11-f33fa8e29ce7"
}

--- Test 4: Call the function defined in the previous request ---
Response: {
  "status": "ok",
  "output": "Hello, Python!\n",
  "session_id": "e9506d65-4fd5-416d-9f11-f33fa8e29ce7"
}

--- Test 5: Create a new session ---
Response: {
  "status": "ok",
  "output": "This is a new session\n",
  "session_id": "6cd4928d-fc6c-451c-96b1-2cc7ea56b325"
}
New Session ID: 6cd4928d-fc6c-451c-96b1-2cc7ea56b325

--- Test 6: Verify session isolation ---
Response: {
  "status": "ok",
  "output": "Error: name 'x' is not defined\n",
  "session_id": "6cd4928d-fc6c-451c-96b1-2cc7ea56b325"
}

--- Test 7: Try to access a non-existent session ---
Response: {
  "status": "error",
  "error": "Session non-existent-session-id not found"
}
Connection closed

```