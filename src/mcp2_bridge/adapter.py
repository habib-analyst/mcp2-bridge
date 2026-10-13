"""Core adapter: convert MCP 2.x tools into LangChain StructuredTools.

Design: one async connection owns the MCP client session (stdio transport).
Every bridged tool is a LangChain StructuredTool whose coroutine delegates
to that session's call_tool. The connection must stay open for the lifetime
of the tools (same contract as langchain-mcp-adapters' MultiServerMCPClient).
"""

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, Sequence

from langchain_core.tools import StructuredTool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool

_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def sanitize_tool_name(name: str) -> str:
    """Make an MCP tool name safe for LangChain (alnum, dot, dash, underscore)."""
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", name).strip("._-")
    return cleaned or "unnamed_tool"


def _json_schema_to_pydantic(name: str, schema: dict) -> type:
    """Build a pydantic model class from a JSON-Schema object schema."""
    from pydantic import BaseModel, Field, create_model

    properties: dict = schema.get("properties", {}) or {}
    required: set = set(schema.get("required", []) or [])
    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        annotation = _json_type_to_python(prop_schema)
        description = prop_schema.get("description", "")
        if prop_name in required:
            fields[prop_name] = (annotation, Field(description=description))
        else:
            default = prop_schema.get("default", None)
            fields[prop_name] = (annotation, Field(default=default, description=description))
    model = create_model(f"{name}Args", __base__=BaseModel, **fields)  # type: ignore[call-overload]
    return model


def _json_type_to_python(prop_schema: dict) -> Any:
    """Best-effort JSON-Schema type -> Python annotation mapping."""
    from typing import List, Optional

    t = prop_schema.get("type")
    if isinstance(t, list):
        non_null = [x for x in t if x != "null"]
        inner = _json_type_to_python({**prop_schema, "type": non_null[0]}) if non_null else Any
        return Optional[inner] if "null" in t else inner
    mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": List[Any],
        "object": dict,
    }
    if t in mapping:
        return mapping[t]
    if "enum" in prop_schema:
        return str
    return Any


def _extract_text(result: Any) -> str:
    """Flatten a CallToolResult into a plain string (text blocks joined)."""
    parts: list[str] = []
    for block in getattr(result, "content", []) or []:
        btype = getattr(block, "type", "")
        if btype == "text":
            parts.append(getattr(block, "text", ""))
        else:
            parts.append(f"[{btype} content omitted]")
    if getattr(result, "is_error", False):  # mcp 2.x renamed isError -> is_error
        raise RuntimeError("MCP tool returned an error: " + "\n".join(parts))
    return "\n".join(parts)


class BridgeConnection:
    """Owns one MCP 2.x stdio client session; tools delegate to it."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    @property
    def session(self) -> ClientSession:
        return self._session

    async def list_tools(self) -> Sequence[MCPTool]:
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, name: str, arguments: dict | None = None) -> str:
        result = await self._session.call_tool(name, arguments or {})
        return _extract_text(result)


def mcp_tool_to_langchain(
    tool: MCPTool,
    call: Callable[[str, dict], Awaitable[str]],
) -> StructuredTool:
    """Convert one MCP 2.x tool definition into a LangChain StructuredTool."""
    name = sanitize_tool_name(tool.name)
    description = (tool.description or "").strip() or f"MCP tool: {tool.name}"
    schema = tool.input_schema or {"type": "object", "properties": {}}
    args_model = _json_schema_to_pydantic(name, schema)

    async def _run(**kwargs: Any) -> str:
        return await call(tool.name, kwargs)

    return StructuredTool(
        name=name,
        description=description,
        args_schema=args_model,
        coroutine=_run,
    )


async def load_mcp2_tools(connection: BridgeConnection) -> list[StructuredTool]:
    """List tools on the server and convert each to a LangChain StructuredTool.

    Mirrors the role of langchain-mcp-adapters' load_mcp_tools for MCP 2.x.
    """
    mcp_tools = await connection.list_tools()
    return [mcp_tool_to_langchain(t, connection.call_tool) for t in mcp_tools]


@asynccontextmanager
async def connect_stdio(
    command: str,
    args: Sequence[str] | None = None,
    env: dict | None = None,
) -> AsyncIterator[BridgeConnection]:
    """Open a stdio connection to an MCP 2.x server and yield a BridgeConnection.

    Example:
        async with connect_stdio("python", ["server.py"]) as conn:
            tools = await load_mcp2_tools(conn)
    """
    params = StdioServerParameters(command=command, args=list(args or []), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield BridgeConnection(session)
