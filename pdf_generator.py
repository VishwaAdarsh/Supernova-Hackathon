#!/usr/bin/env python3
"""
SUPERNOVA 2026 - Root Delegation Wrapper
Exposes backend.pdf_generator for seamless backward compatibility.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pdf_generator import *
