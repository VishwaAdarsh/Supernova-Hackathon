#!/usr/bin/env python3
"""
SUPERNOVA 2026 - Root Entrypoint
Delegates execution to backend.server for clean modular architecture.
Maintains full backward compatibility for all existing CLI commands, local execution, and deployment hooks.
"""
import sys
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import all public symbols from backend server
from server import *

if __name__ == "__main__":
    run_server()
