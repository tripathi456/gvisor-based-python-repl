in first terminal 

```bash
bash run.sh
```

---

concurrent clients are stateful but isolated

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


---

SIMPLER example: 
