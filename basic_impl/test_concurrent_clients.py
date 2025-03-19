#!/usr/bin/env python3
import socket
import json
import sys
import threading
import time
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Initialize Rich console
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

def client_session(client_id, results, progress):
    """Run a client session that connects to the server and executes code."""
    # Server connection details
    host = "localhost"
    port = 8000
    
    # Create a socket and connect to the server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    session_id = None
    
    task_id = progress.add_task(f"[cyan]Client {client_id}", total=6)  # Increased total for new step
    
    try:
        sock.connect((host, port))
        progress.update(task_id, description=f"[cyan]Client {client_id}: Connected to {host}:{port}", advance=0.2)
        
        # Receive initial greeting
        greeting = receive_response(sock)
        progress.update(task_id, description=f"[cyan]Client {client_id}: Server greeting received", advance=0.2)
        
        # Step 1: Create a new session by executing code
        progress.update(task_id, description=f"[cyan]Client {client_id}: Creating a new session", advance=0.2)
        response = send_receive(sock, {
            "code": f"client_id = '{client_id}'\nprint(f'Client {client_id} initialized')"
        })
        session_id = response.get("session_id")
        progress.update(task_id, description=f"[cyan]Client {client_id}: Session ID: {session_id[:8]}...", advance=0.2)
        results[client_id]["session_id"] = session_id
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 2: Define a function in the session
        progress.update(task_id, description=f"[cyan]Client {client_id}: Defining a function", advance=0.2)
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
        progress.update(task_id, description=f"[cyan]Client {client_id}: Creating a unique variable", advance=0.2)
        unique_value = uuid.uuid4().hex[:8]
        var_name = f"unique_value_{client_id}"  # Use client-specific variable names
        response = send_receive(sock, {
            "code": f"{var_name} = '{unique_value}'\nprint(f'Set {var_name} to {{{var_name}}}')",
            "session_id": session_id
        })
        results[client_id]["unique_value"] = unique_value
        results[client_id]["var_name"] = var_name
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 4: Create a common variable name with client-specific value
        progress.update(task_id, description=f"[cyan]Client {client_id}: Setting common variable", advance=0.2)
        common_value = f"value_from_client_{client_id}_{uuid.uuid4().hex[:6]}"
        response = send_receive(sock, {
            "code": f"common_variable = '{common_value}'\nprint(f'Set common_variable to {{common_variable}}')",
            "session_id": session_id
        })
        results[client_id]["common_value"] = common_value
        results[client_id]["outputs"].append(response.get("output", ""))
        
        # Step 5: Sleep to simulate concurrent work
        progress.update(task_id, description=f"[cyan]Client {client_id}: Simulating work...", advance=0.2)
        time.sleep(1)
        
        # Step 6: Verify the variables are still correct
        progress.update(task_id, description=f"[cyan]Client {client_id}: Verifying variables", advance=0.2)
        response = send_receive(sock, {
            "code": f"print(f'{var_name} is {{{var_name}}}\\ncommon_variable is {{common_variable}}')",
            "session_id": session_id
        })
        results[client_id]["outputs"].append(response.get("output", ""))
        progress.update(task_id, description=f"[cyan]Client {client_id}: ✅ Completed", advance=0.2)
        
    except Exception as e:
        results[client_id]["error"] = str(e)
        progress.update(task_id, description=f"[red]Client {client_id}: Error: {str(e)}", advance=1.0)
    finally:
        sock.close()
        if not results[client_id]["error"]:
            progress.update(task_id, completed=True)

def main():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]Python REPL Server - Concurrent Clients Test[/bold cyan]",
        border_style="cyan"
    ))
    
    # Dictionary to store results from both clients
    results = {
        "A": {"session_id": None, "unique_value": None, "var_name": None, "common_value": None, "outputs": [], "error": None},
        "B": {"session_id": None, "unique_value": None, "var_name": None, "common_value": None, "outputs": [], "error": None}
    }
    
    # Create and start two client threads with progress bars
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        console.print("[bold]Starting client threads...[/bold]")
        
        thread_a = threading.Thread(target=client_session, args=("A", results, progress))
        thread_b = threading.Thread(target=client_session, args=("B", results, progress))
        
        thread_a.start()
        thread_b.start()
        
        # Wait for both threads to complete
        thread_a.join()
        thread_b.join()
    
    console.print("[bold green]✓[/bold green] Both client threads completed\n")
    
    # Now test cross-session access with a third connection
    console.print(Panel.fit(
        "[bold yellow]Testing Cross-Session Access[/bold yellow]",
        border_style="yellow"
    ))
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with console.status("[cyan]Connecting to server for cross-session test...[/cyan]"):
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
            common_value_a = results["A"]["common_value"]
            common_value_b = results["B"]["common_value"]
        
        console.print(f"[yellow]Attempting to access Client A's variable [bold]'{var_name_a}'[/bold] from Client B's session[/yellow]")
        response = send_receive(sock, {
            "code": f"try:\n    print(f'Client A variable {var_name_a}: {{{var_name_a}}}')\nexcept NameError as e:\n    print(f'Error: {{e}}')",
            "session_id": session_b
        })
        cross_session_result_a = response.get("output", "")
        console.print(f"[cyan]Result:[/cyan] {cross_session_result_a}")
        
        # Try to access common_variable from Client B's session and verify it has Client B's value
        console.print(f"\n[yellow]Verifying [bold]'common_variable'[/bold] in Client B's session has Client B's value[/yellow]")
        response = send_receive(sock, {
            "code": f"try:\n    print(f'common_variable in B session: {{common_variable}}')\n    print(f'Is it B\\'s value? {{common_variable == \"{common_value_b}\"}}')\n    print(f'Is it A\\'s value? {{common_variable == \"{common_value_a}\"}}')\nexcept NameError as e:\n    print(f'Error: {{e}}')",
            "session_id": session_b
        })
        common_var_b_result = response.get("output", "")
        console.print(f"[cyan]Result:[/cyan] {common_var_b_result}")
        
        # Try to access common_variable from Client A's session and verify it has Client A's value
        console.print(f"\n[yellow]Verifying [bold]'common_variable'[/bold] in Client A's session has Client A's value[/yellow]")
        response = send_receive(sock, {
            "code": f"try:\n    print(f'common_variable in A session: {{common_variable}}')\n    print(f'Is it A\\'s value? {{common_variable == \"{common_value_a}\"}}')\n    print(f'Is it B\\'s value? {{common_variable == \"{common_value_b}\"}}')\nexcept NameError as e:\n    print(f'Error: {{e}}')",
            "session_id": session_a
        })
        common_var_a_result = response.get("output", "")
        console.print(f"[cyan]Result:[/cyan] {common_var_a_result}")
        
        # Also try to access Client B's variable from Client B's session (should succeed)
        console.print(f"\n[yellow]Attempting to access Client B's variable [bold]'{var_name_b}'[/bold] from Client B's session (should succeed)[/yellow]")
        response = send_receive(sock, {
            "code": f"try:\n    print(f'Client B variable {var_name_b}: {{{var_name_b}}}')\nexcept NameError as e:\n    print(f'Error: {{e}}')",
            "session_id": session_b
        })
        same_session_result = response.get("output", "")
        console.print(f"[cyan]Result:[/cyan] {same_session_result}")
        
        # Print summary of results in a table
        console.print(Panel.fit(
            "[bold green]Test Results Summary[/bold green]",
            border_style="green"
        ))
        
        # Create a table for Client A
        table_a = Table(title="Client A", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table_a.add_column("Property", style="dim")
        table_a.add_column("Value")
        
        table_a.add_row("Session ID", session_a)
        table_a.add_row("Variable Name", var_name_a)
        table_a.add_row("Unique Value", unique_value_a)
        table_a.add_row("Common Variable Value", common_value_a)
        
        for i, output in enumerate(results["A"]["outputs"]):
            table_a.add_row(f"Step {i+1} Output", output.strip())
        
        console.print(table_a)
        
        # Create a table for Client B
        table_b = Table(title="Client B", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table_b.add_column("Property", style="dim")
        table_b.add_column("Value")
        
        table_b.add_row("Session ID", session_b)
        table_b.add_row("Variable Name", var_name_b)
        table_b.add_row("Unique Value", unique_value_b)
        table_b.add_row("Common Variable Value", common_value_b)
        
        for i, output in enumerate(results["B"]["outputs"]):
            table_b.add_row(f"Step {i+1} Output", output.strip())
        
        console.print(table_b)
        
        # Create a table for cross-session test results
        table_cross = Table(title="Cross-Session Test Results", box=box.ROUNDED, show_header=True, header_style="bold yellow")
        table_cross.add_column("Test", style="dim")
        table_cross.add_column("Result")
        
        table_cross.add_row(
            "B trying to access A's variable", 
            cross_session_result_a.strip()
        )
        table_cross.add_row(
            "common_variable in B's session", 
            common_var_b_result.strip()
        )
        table_cross.add_row(
            "common_variable in A's session", 
            common_var_a_result.strip()
        )
        table_cross.add_row(
            "B accessing its own variable", 
            same_session_result.strip()
        )
        
        console.print(table_cross)
        
        # Verify session isolation
        isolation_verified = (
            "Error: name '" + var_name_a + "' is not defined" in cross_session_result_a and
            "Is it A's value? True" in common_var_a_result and
            "Is it B's value? False" in common_var_a_result and
            "Is it B's value? True" in common_var_b_result and
            "Is it A's value? False" in common_var_b_result
        )
        
        if isolation_verified:
            console.print(Panel.fit(
                "[bold green]✓ Session isolation verified: Clients have independent environments with isolated variables[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                "[bold red]⚠ WARNING: Session isolation may be compromised![/bold red]",
                border_style="red"
            ))
        
    except Exception as e:
        console.print(f"[bold red]Error in cross-session test: {e}[/bold red]")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
