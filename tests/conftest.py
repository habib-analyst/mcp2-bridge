"""Shared path to the real MCP 2.x test server (no mocks anywhere)."""

from pathlib import Path

SERVER = Path(__file__).parent / "server_2x.py"
