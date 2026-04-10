"""ASGI entrypoint shim to run backend app from repository root."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"

# Ensure backend modules like `database.py` are importable when launching from repo root.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.main import app
