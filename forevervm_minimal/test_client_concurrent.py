#!/usr/bin/env python3
# test_client_concurrent.py

import requests
import json
import time
import logging
import threading
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Initialize Rich console
console = Console()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def client_session(client_id, results, progress):
    """Run a client session that connects to the server and executes code."""
    base_url = "http://localhost:8000"
    task_id = progress.add_task(f"[cyan]Client {client_id}", total=6)
    
    try:
        # Step 1: Create a new session
        progress.update(task_id, description=f"[cyan]Client {client_id}: Creating session", advance=0.2)
        response = requests.post(f"{base_url}/session")
        session_data = response.json()
        session_id = session_data["session_id"]
        results[client_id]["session_id"] = session_id
        
        # Step 2: Initialize client-specific variables
        progress.update(task_id, description=f"[cyan]Client {client_id}: Initializing variables", advance=0.2)
        unique_value = uuid.uuid4().hex[:8]
        var_name = f"unique_value_{client_id}"
        code = f"""
{var_name} = '{unique_value}'
shared_list = [1, 2, 3]
print(f'Initial state: {var_name} = {{{var_name}}}, shared_list = {{shared_list}}')
"""
        response = requests.post(
            f"{base_url}/session/{session_id}/execute",
            json={"code": code}
        )
        results[client_id]["outputs"].append(response.json().get("output", ""))
        results[client_id]["unique_value"] = unique_value
        results[client_id]["var_name"] = var_name
        
        # Step 3: Modify shared data structure
        progress.update(task_id, description=f"[cyan]Client {client_id}: Modifying shared list", advance=0.2)
        code = f"""
client_marker = '{client_id}'
shared_list.append(client_marker)
print(f'Modified shared_list = {{shared_list}}')
"""
        response = requests.post(
            f"{base_url}/session/{session_id}/execute",
            json={"code": code}
        )
        results[client_id]["outputs"].append(response.json().get("output", ""))
        
        # Step 4: Simulate some work
        progress.update(task_id, description=f"[cyan]Client {client_id}: Simulating work", advance=0.2)
        time.sleep(2)  # Simulate work that might trigger checkpointing
        
        # Step 5: Verify session state after potential checkpoint
        progress.update(task_id, description=f"[cyan]Client {client_id}: Verifying state", advance=0.2)
        code = f"""
print(f'State after work:')
print(f'{var_name} = {{{var_name}}}')
print(f'shared_list = {{shared_list}}')
"""
        response = requests.post(
            f"{base_url}/session/{session_id}/execute",
            json={"code": code}
        )
        results[client_id]["outputs"].append(response.json().get("output", ""))
        
        # Step 6: Final computation
        progress.update(task_id, description=f"[cyan]Client {client_id}: Final computation", advance=0.2)
        code = f"""
result = sum([int(x) if str(x).isdigit() else 0 for x in shared_list])
print(f'Final computation: sum(shared_list) = {{result}}')
"""
        response = requests.post(
            f"{base_url}/session/{session_id}/execute",
            json={"code": code}
        )
        results[client_id]["outputs"].append(response.json().get("output", ""))
        progress.update(task_id, description=f"[cyan]Client {client_id}: ✅ Completed", completed=True)
        
    except Exception as e:
        results[client_id]["error"] = str(e)
        progress.update(task_id, description=f"[red]Client {client_id}: Error: {str(e)}", advance=1.0)

def test_cross_session_access(results):
    """Test isolation between sessions by attempting cross-session variable access."""
    base_url = "http://localhost:8000"
    
    session_a = results["A"]["session_id"]
    session_b = results["B"]["session_id"]
    var_name_a = results["A"]["var_name"]
    unique_value_a = results["A"]["unique_value"]
    
    # Try to access Client A's variable from Client B's session
    code = f"""
try:
    print(f'Attempting to access {var_name_a} from session B')
    print(f'Value: {{{var_name_a}}}')
except NameError as e:
    print(f'Expected error: {{e}}')
"""
    response = requests.post(
        f"{base_url}/session/{session_b}/execute",
        json={"code": code}
    )
    cross_session_result = response.json().get("output", "")
    
    # Verify the variable in original session
    code = f"""
print(f'Verifying {var_name_a} in original session A')
print(f'Value: {{{var_name_a}}}')
"""
    response = requests.post(
        f"{base_url}/session/{session_a}/execute",
        json={"code": code}
    )
    original_session_result = response.json().get("output", "")
    
    return {
        "cross_session_access": cross_session_result,
        "original_session_access": original_session_result
    }

def main():
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]ForeverVM Python REPL - Concurrent Clients Test[/bold cyan]",
        border_style="cyan"
    ))
    
    # Dictionary to store results from both clients
    results = {
        "A": {"session_id": None, "unique_value": None, "var_name": None, "outputs": [], "error": None},
        "B": {"session_id": None, "unique_value": None, "var_name": None, "outputs": [], "error": None}
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
        
        thread_a.join()
        thread_b.join()
    
    console.print("[bold green]✓[/bold green] Both client threads completed\n")
    
    # Test cross-session access
    console.print(Panel.fit(
        "[bold yellow]Testing Cross-Session Access[/bold yellow]",
        border_style="yellow"
    ))
    
    with console.status("[cyan]Testing session isolation...[/cyan]"):
        cross_session_results = test_cross_session_access(results)
    
    # Create results tables
    for client_id in ["A", "B"]:
        table = Table(title=f"Client {client_id}", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Property", style="dim")
        table.add_column("Value")
        
        table.add_row("Session ID", results[client_id]["session_id"])
        table.add_row("Variable Name", results[client_id]["var_name"])
        table.add_row("Unique Value", results[client_id]["unique_value"])
        
        for i, output in enumerate(results[client_id]["outputs"]):
            table.add_row(f"Step {i+1} Output", output.strip())
        
        if results[client_id]["error"]:
            table.add_row("Error", results[client_id]["error"])
        
        console.print(table)
        console.print("")
    
    # Create cross-session test results table
    table_cross = Table(
        title="Cross-Session Test Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold yellow"
    )
    table_cross.add_column("Test", style="dim")
    table_cross.add_column("Result")
    
    table_cross.add_row(
        "Access from other session",
        cross_session_results["cross_session_access"].strip()
    )
    table_cross.add_row(
        "Access from original session",
        cross_session_results["original_session_access"].strip()
    )
    
    console.print(table_cross)
    
    # Verify session isolation
    isolation_verified = all([
        # Check that B cannot access A's variable (should get NameError)
        "name 'unique_value_A' is not defined" in cross_session_results["cross_session_access"],
        # Check that A can still access its own variable
        f"Value: {results['A']['unique_value']}" in cross_session_results["original_session_access"],
        # Verify both sessions completed without errors
        not results["A"]["error"],
        not results["B"]["error"]
    ])
    
    if isolation_verified:
        console.print(Panel.fit(
            "[bold green]✓ Session isolation verified: Sessions have independent environments[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "[bold red]⚠ WARNING: Session isolation may be compromised![/bold red]",
            border_style="red"
        ))

if __name__ == "__main__":
    main()
