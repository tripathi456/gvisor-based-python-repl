# main.py

import sys
import os
import logging

# Add the parent directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forevervm_minimal.http_server import run_http_server
from forevervm_minimal.component_factory import create_components
from forevervm_minimal.config import (
    SERVER_HOST,
    SERVER_PORT,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # Initialize all components using the factory
    components = create_components()
    
    try:
        # Start the HTTP server with the session manager
        run_http_server(components.session_manager, host=SERVER_HOST, port=SERVER_PORT)
    finally:
        # Ensure clean shutdown of background tasks
        components.task_manager.stop_all_tasks()

if __name__ == "__main__":
    main()