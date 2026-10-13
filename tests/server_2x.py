"""Real MCP 2.x server (MCPServer) used by the test suite over stdio.

Run: python tests/server_2x.py
"""

import asyncio

from mcp.server.mcpserver import MCPServer

server = MCPServer("mcp2-bridge-test")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@server.tool()
def echo(text: str, repeat: int = 1) -> str:
    """Echo text back, repeated N times."""
    return " ".join([text] * repeat)


@server.tool()
def boom() -> str:
    """Always raises, to exercise error propagation."""
    raise ValueError("kaboom")


@server.tool()
def no_args() -> str:
    """Takes no arguments."""
    return "ok"


async def main() -> None:
    await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(main())
