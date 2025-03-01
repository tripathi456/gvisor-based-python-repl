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


---

concurrent clients are stateful but isolated

```bash
❯ python test_concurrent_clients.py
Starting client threads...
Client B: Connected to localhost:8000
Client A: Connected to localhost:8000
Client A: Server greeting received
Client A: Creating a new session
Client B: Server greeting received
Client B: Creating a new session
Client A: Session ID: 7e5c0e5f-b3b9-4e9a-9462-f739e0130603
Client A: Defining a function
Client B: Session ID: 571dcdd7-8bf7-42ff-af4d-64b20fda90cd
Client B: Defining a function
Client A: Creating a unique variable
Client B: Creating a unique variable
Client A: Verifying unique variable
Client B: Verifying unique variable
Client B: Connection closed
Client A: Connection closed
Both client threads completed

--- Testing Cross-Session Access ---
Attempting to access Client A's variable 'unique_value_A' from Client B's session
Result: Error: name 'unique_value_A' is not defined

Attempting to access Client B's variable 'unique_value_B' from Client B's session (should succeed)
Result: Client B variable unique_value_B: 08c46eb0


--- Test Results Summary ---
Client A Session ID: 7e5c0e5f-b3b9-4e9a-9462-f739e0130603
Client A Variable Name: unique_value_A
Client A Unique Value: b285170e
Client A Outputs:
  Step 1: Client A initialized
  Step 2:
  Step 3: Set unique_value_A to b285170e
  Step 4: unique_value_A is b285170e

Client B Session ID: 571dcdd7-8bf7-42ff-af4d-64b20fda90cd
Client B Variable Name: unique_value_B
Client B Unique Value: 08c46eb0
Client B Outputs:
  Step 1: Client B initialized
  Step 2:
  Step 3: Set unique_value_B to 08c46eb0
  Step 4: unique_value_B is 08c46eb0

Cross-Session Access Result (B trying to access A's variable): Error: name 'unique_value_A' is not defined
Same-Session Access Result (B accessing its own variable): Client B variable unique_value_B: 08c46eb0

Session isolation verified: Client B cannot access Client A's variables


```

---

Enhanced test with common variable name testing

```bash
❯ python test_concurrent_clients.py
╭──────────────────────────────────────────────╮
│ Python REPL Server - Concurrent Clients Test │
╰──────────────────────────────────────────────╯
Starting client threads...
⠦ Client A: ✅ Completed 0:00:01
⠦ Client B: ✅ Completed 0:00:01
✓ Both client threads completed

╭──────────────────────────────╮
│ Testing Cross-Session Access │
╰──────────────────────────────╯
Attempting to access Client A's variable 'unique_value_A' from Client B's 
session
Result: Error: name 'unique_value_A' is not defined


Verifying 'common_variable' in Client B's session has Client B's value
Result: common_variable in B session: value_from_client_B_ef1d52
Is it B's value? True
Is it A's value? False


Verifying 'common_variable' in Client A's session has Client A's value
Result: common_variable in A session: value_from_client_A_25686d
Is it A's value? True
Is it B's value? False


Attempting to access Client B's variable 'unique_value_B' from Client B's 
session (should succeed)
Result: Client B variable unique_value_B: 13734060

╭──────────────────────╮
│ Test Results Summary │
╰──────────────────────╯
                                  Client A                                   
╭───────────────────────┬───────────────────────────────────────────────────╮
│ Property              │ Value                                             │
├───────────────────────┼───────────────────────────────────────────────────┤
│ Session ID            │ d7b97db3-2255-49de-bd45-f7e7bde7414c              │
│ Variable Name         │ unique_value_A                                    │
│ Unique Value          │ fef5e358                                          │
│ Common Variable Value │ value_from_client_A_25686d                        │
│ Step 1 Output         │ Client A initialized                              │
│ Step 2 Output         │                                                   │
│ Step 3 Output         │ Set unique_value_A to fef5e358                    │
│ Step 4 Output         │ Set common_variable to value_from_client_A_25686d │
│ Step 5 Output         │ unique_value_A is fef5e358                        │
│                       │ common_variable is value_from_client_A_25686d     │
╰───────────────────────┴───────────────────────────────────────────────────╯
                                  Client B                                   
╭───────────────────────┬───────────────────────────────────────────────────╮
│ Property              │ Value                                             │
├───────────────────────┼───────────────────────────────────────────────────┤
│ Session ID            │ 270781c9-e2ec-4a5d-862f-e754139de04f              │
│ Variable Name         │ unique_value_B                                    │
│ Unique Value          │ 13734060                                          │
│ Common Variable Value │ value_from_client_B_ef1d52                        │
│ Step 1 Output         │ Client B initialized                              │
│ Step 2 Output         │                                                   │
│ Step 3 Output         │ Set unique_value_B to 13734060                    │
│ Step 4 Output         │ Set common_variable to value_from_client_B_ef1d52 │
│ Step 5 Output         │ unique_value_B is 13734060                        │
│                       │ common_variable is value_from_client_B_ef1d52     │
╰───────────────────────┴───────────────────────────────────────────────────╯
                           Cross-Session Test Results                           
╭─────────────────────────────────┬────────────────────────────────────────────╮
│ Test                            │ Result                                     │
├─────────────────────────────────┼────────────────────────────────────────────┤
│ B trying to access A's variable │ Error: name 'unique_value_A' is not        │
│                                 │ defined                                    │
│ common_variable in B's session  │ common_variable in B session:              │
│                                 │ value_from_client_B_ef1d52                 │
│                                 │ Is it B's value? True                      │
│                                 │ Is it A's value? False                     │
│ common_variable in A's session  │ common_variable in A session:              │
│                                 │ value_from_client_A_25686d                 │
│                                 │ Is it A's value? True                      │
│                                 │ Is it B's value? False                     │
│ B accessing its own variable    │ Client B variable unique_value_B: 13734060 │
╰─────────────────────────────────┴────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────────────╮
│ ✓ Session isolation verified: Clients have independent environments with     │
│ isolated variables                                                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```