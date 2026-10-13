# mcp2-bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](pyproject.toml)
[![GitHub stars](https://img.shields.io/github/stars/habib-analyst/mcp2-bridge.svg)](https://github.com/habib-analyst/mcp2-bridge/stargazers)

The working LangGraph ↔ MCP 2.x adapter. `langchain-mcp-adapters` 0.3.2 pins
`mcp<2.0.0` while the MCP Python SDK is at 2.x with breaking module reshuffles
(`mcp.server.fastmcp` is gone) — every 2025 MCP tutorial is broken against the
current SDK. This package bridges the gap: native 2.x tools become LangChain
`StructuredTool`s, plus a compat shim that makes legacy tutorial code import
again.

## Quickstart

```bash
pip install mcp2-bridge
```

```python
import asyncio
from mcp2_bridge import connect_stdio, load_mcp2_tools

async def main():
    async with connect_stdio("python", ["my_server.py"]) as conn:
        tools = await load_mcp2_tools(conn)   # MCP 2.x tools -> StructuredTools
        add = next(t for t in tools if t.name == "add")
        print(await add.ainvoke({"a": 19, "b": 23}))

asyncio.run(main())
```

Real output against a live MCP 2.x server over stdio (see `examples/quickstart.py`):

```
Bridged 4 tools from the MCP 2.x server:
  - add: Add two integers.
  - echo: Echo text back, repeated N times.
  - boom: Always raises, to exercise error propagation.
  - no_args: Takes no arguments.

add(19, 23) -> 42
```

Legacy 2025-era code keeps working with one call:

```python
from mcp2_bridge import ensure_fastmcp_shim
ensure_fastmcp_shim()
from mcp.server.fastmcp import FastMCP  # works again on mcp 2.x (alias for MCPServer)
```

## Measured results

All numbers measured 2026-10-13 on mcp 2.3.0, langchain-core 1.6.10, Python 3.12,
CPU only, real stdio wire (no mocks).

| Check | Result |
|---|---|
| Test suite | **24/24 passing** (`pytest tests/`, ~16s) |
| Tool list roundtrip (stdio) | 4/4 tools discovered with names, descriptions, JSON schemas |
| Tool call roundtrip latency (n=20) | mean **2.7 ms**, p50 2.3 ms, max 4.3 ms |
| LangGraph end-to-end (real StateGraph) | agent calls bridged tool, returns "The answer is 42." |
| Version-matrix assertions | 7/7 boundary cases classified correctly |
| The break, reproduced | `pip` refuses `langchain-mcp-adapters==0.3.2` + `mcp>=2.2` (pin `mcp<2.0.0`); force-installed, `load_mcp_tools` dies on `mcp.server.fastmcp` (ModuleNotFoundError) and `MultiServerMCPClient` dies on `mcp.shared.context.RequestContext` (ImportError). Latest upstream adapter is still 0.3.2 |

## Compatibility matrix

| mcp SDK | langchain-mcp-adapters 0.3.2 | mcp2-bridge |
|---|---|---|
| 1.x (1.24.0 - 1.30.0) | supported | supported |
| 2.x (2.0.0 - 2.3.0) | **BROKEN** | supported |

Also available programmatically: `from mcp2_bridge import adapter_status, get_matrix`.

## How it works

```
 MCP 2.x server (MCPServer, stdio)
        │  list_tools / call_tool  (real wire)
        ▼
 BridgeConnection (owns the ClientSession)
        │  JSON Schema -> pydantic args model
        ▼
 StructuredTool per MCP tool  ──►  LangGraph StateGraph node
```

- `connect_stdio(command, args)` opens the stdio client session and yields a
  `BridgeConnection`.
- `load_mcp2_tools(conn)` converts each `mcp.types.Tool` into a LangChain
  `StructuredTool`: name sanitized, description preserved, `input_schema`
  compiled into a pydantic `args_schema`, and an async coroutine delegating to
  `session.call_tool`. Text content blocks are joined; tool errors surface as
  `RuntimeError`.
- `compat.ensure_fastmcp_shim()` installs a `sys.modules` alias so
  `from mcp.server.fastmcp import FastMCP` resolves to `MCPServer` on 2.x.
  `compat.translate_import_path()` maps other moved/removed 2025-era paths.

## Limitations (honest)

- Stdio transport only in this release; Streamable HTTP / SSE not yet bridged.
- Only text content blocks are returned; image/audio blocks are replaced with a
  placeholder note.
- The LangGraph end-to-end test uses a scripted planner node as a stand-in for
  an LLM call (documented in `tests/test_langgraph_e2e.py`); the graph, tools,
  and wire are real.
- On mcp 2.x the server wraps tool exceptions in `UnexpectedToolError`, so the
  client sees "Error executing tool X" — the original exception message stays
  server-side (measured, not a bridge bug).
- Requires `mcp>=2.0.0`. For mcp 1.x, keep using `langchain-mcp-adapters`.
- Companion doc `docs/AGENTIC_OAUTH_MIGRATION.md` covers Google's agentic OAuth
  classification for Workspace MCP servers (Nov 11, 2026 enforcement).

## Citation

```bibtex
@software{rehman2026mcp2bridge,
  author  = {Habib Ur Rehman},
  title   = {mcp2-bridge: Working LangGraph to MCP 2.x Adapter and Compat Shim},
  year    = {2026},
  url     = {https://github.com/habib-analyst/mcp2-bridge}
}
```

---
Built by [Habib Ur Rehman](https://github.com/habib-analyst) · ML/AI Engineer & healthcare-AI researcher ·
[LinkedIn](https://www.linkedin.com/in/hur-dev) · [habib.top](https://habib.top)
