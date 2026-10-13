"""Quickstart: bridge a real MCP 2.x server into LangChain tools.

Run: python examples/quickstart.py
Spins up tests/server_2x.py over stdio, lists its tools, calls one.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mcp2_bridge import connect_stdio, load_mcp2_tools

SERVER = Path(__file__).resolve().parents[1] / "tests" / "server_2x.py"


async def main() -> None:
    async with connect_stdio(sys.executable, [str(SERVER)]) as conn:
        tools = await load_mcp2_tools(conn)
        print(f"Bridged {len(tools)} tools from the MCP 2.x server:")
        for t in tools:
            print(f"  - {t.name}: {t.description}")
        add = next(t for t in tools if t.name == "add")
        result = await add.ainvoke({"a": 19, "b": 23})
        print(f"\nadd(19, 23) -> {result}")


if __name__ == "__main__":
    asyncio.run(main())
