"""Compatibility launcher for existing Replit workflow and deployment commands."""

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_server.main import run


if __name__ == "__main__":
    run()