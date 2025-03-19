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
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

def send_receive(sock, request_dict):
    """Send a request to the server and receive the response (length-prefixed JSON)."""
    request_json = json.dumps(request_dict)
    request_bytes = request_json.encode('utf-8')

    # Send the length first (4 bytes, big-endian)
    length = len(request_bytes)
    sock.sendall(length.to_bytes(4, 'big'))
    # Then send the actual data
    sock.sendall(request_bytes)

    # Read response length
    length_bytes = sock.recv(4)
    if not length_bytes:
        return {}
    response_length = int.from_bytes(length_bytes, 'big')

    # Read response data
    chunks = []
    bytes_received = 0
    while bytes_received < response_length:
        chunk = sock.recv(min(4096, response_length - bytes_received))
        if not chunk:
            break
        chunks.append(chunk)
        bytes_received += len(chunk)

    response_str = b''.join(chunks).decode('utf-8')
    return json.loads(response_str)

def receive_greeting(sock):
    """Receive a single greeting message from the server (length-prefixed JSON)."""
    length_bytes = sock.recv(4)
    if not length_bytes:
        return None
    message_length = int.from_bytes(length_bytes, 'big')
    chunks = []
    bytes_received = 0
    while bytes_received < message_length:
        chunk = sock.recv(min(4096, message_length - bytes_received))
        if not chunk:
            break
        chunks.append(chunk)
        bytes_received += len(chunk)
    data = b''.join(chunks).decode('utf-8')
    return json.loads(data)

def client_thread(name, results, progress):
    """
    Each client:
      1. Connects to the server, receives greeting.
      2. Creates a session by sending code with no session_id (server should create new).
      3. Defines a variable, prints it.
      4. Sleeps long enough to trigger session timeout (6s).
      5. Executes code again to see if the session was snapshotted+restored.
    """
    host = "localhost"
    port = 8000

    task_id = progress.add_task(f"[green]{name} Starting", total=5)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    session_id = None
    try:
        sock.connect((host, port))
        progress.update(task_id, description=f"[green]{name}: Connected", advance=1)

        # 1) Receive initial greeting
        greeting = receive_greeting(sock)
        results[name]["greeting"] = greeting

        # 2) Create a new session by sending some code (omitting session_id => server should create it)
        progress.update(task_id, description=f"[green]{name}: Creating session", advance=1)
        resp_create = send_receive(sock, {
            "code": f"client_name = '{name}'\nprint('Hello from {name}!')"
        })
        # The server should respond with something like: {"session_id": "...", "output": "..."}
        session_id = resp_create.get("session_id")
        results[name]["session_id"] = session_id
        results[name]["outputs"].append(resp_create.get("output", ""))

        # 3) Define a variable and print it
        progress.update(task_id, description=f"[green]{name}: Defining variable", advance=1)
        myvar = f"value_{uuid.uuid4().hex[:6]}"
        code_str = f"""myvar_{name} = '{myvar}'\nprint('Set myvar_{name} = ' + myvar_{name})"""
        resp_define = send_receive(sock, {
            "session_id": session_id,
            "code": code_str
        })
        results[name]["outputs"].append(resp_define.get("output", ""))

        # 4) Sleep 7s to exceed the 6s inactivity timeout
        progress.update(task_id, description=f"[yellow]{name}: Sleeping 7s (timeout test)", advance=1)
        time.sleep(7)

        # 5) Execute new code => triggers restore if session was snapshotted
        progress.update(task_id, description=f"[green]{name}: Checking session restore", advance=1)
        resp_after_sleep = send_receive(sock, {
            "session_id": session_id,
            "code": f"print('After timeout, myvar_{name} is ' + myvar_{name})"
        })
        results[name]["outputs"].append(resp_after_sleep.get("output", ""))

        progress.update(task_id, description=f"[green]{name}: Finished", completed=True)

    except Exception as e:
        results[name]["error"] = str(e)
    finally:
        sock.close()

def main():
    console.clear()
    console.print(Panel.fit("[bold cyan]Timeout & Concurrency Test (6s Inactivity)[/bold cyan]", border_style="cyan"))

    # We'll track results from multiple clients
    # For demonstration, let's spin up two concurrent clients
    results = {
        "ClientA": {"session_id": None, "greeting": None, "outputs": [], "error": None},
        "ClientB": {"session_id": None, "greeting": None, "outputs": [], "error": None}
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        console.print("[bold]Starting two client threads...[/bold]\n")

        tA = threading.Thread(target=client_thread, args=("ClientA", results, progress))
        tB = threading.Thread(target=client_thread, args=("ClientB", results, progress))

        tA.start()
        tB.start()

        tA.join()
        tB.join()

    console.print("\n[bold green]All client threads completed![/bold green]\n")

    # Present a brief results summary table
    table = Table(title="Results Summary", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Client")
    table.add_column("Session ID")
    table.add_column("Error")
    table.add_column("Outputs")

    for client_name, data in results.items():
        session_id = data["session_id"] or "[None]"
        error = data["error"] or "[None]"
        outputs_joined = "\n---\n".join(data["outputs"]) if data["outputs"] else "[No outputs]"
        table.add_row(client_name, session_id, error, outputs_joined)

    console.print(table)

    console.print(Panel.fit(
        "[bold green]✓ Test completed. Check the logs above or your server logs to confirm sessions got snapshotted/restored after 6s of inactivity.[/bold green]",
        border_style="green"
    ))

if __name__ == "__main__":
    main()
