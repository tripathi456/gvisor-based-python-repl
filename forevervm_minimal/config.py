"""Configuration management for the ForeverVM service.

Following the Zen of Python:
- Explicit is better than implicit
- Simple is better than complex
- Configuration should be discoverable
"""

import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.getenv('FOREVERVM_DATA_DIR', BASE_DIR / 'data_dir')
SNAPSHOT_DIR = os.getenv('FOREVERVM_SNAPSHOT_DIR', DATA_DIR / 'snapshots')

# Worker Configuration
WORKER_POOL_SIZE = int(os.getenv('FOREVERVM_WORKER_POOL_SIZE', '2'))
WORKER_SPAWN_TIMEOUT = int(os.getenv('FOREVERVM_WORKER_SPAWN_TIMEOUT', '5'))  # seconds

# Session Configuration
SESSION_INACTIVITY_TIMEOUT = int(os.getenv('FOREVERVM_SESSION_TIMEOUT', '6'))  # 6 seconds for testing
SESSION_CLEANUP_INTERVAL = int(os.getenv('FOREVERVM_CLEANUP_INTERVAL', '2'))  # check every 2 seconds

# Server Configuration
SERVER_HOST = os.getenv('FOREVERVM_HOST', '0.0.0.0')
SERVER_PORT = int(os.getenv('FOREVERVM_PORT', '8000'))
SERVER_DEBUG = os.getenv('FOREVERVM_DEBUG', 'true').lower() == 'true'

# Create required directories
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
