"""Adapter tests: tool list/call roundtrip through the REAL stdio wire.

Note: connections are opened inline per test (not via yield fixtures)
because anyio cancel scopes must exit in the same task they were entered in.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

from mcp2_bridge.adapter import (
    connect_stdio,
    load_mcp2_tools,
    mcp_tool_to_langchain,
    sanitize_tool_name,
)

SERVER = Path(__file__).parent / "server_2x.py"


@asynccontextmanager
async def bridge():
    async with connect_stdio(sys.executable, [str(SERVER)]) as conn:
        yield conn


@asynccontextmanager
async def tools_ctx():
    async with bridge() as conn:
        yield {t.name: t for t in await load_mcp2_tools(conn)}


async def test_list_tools_roundtrip():
    async with bridge() as conn:
        tools = await conn.list_tools()
    names = sorted(t.name for t in tools)
    assert names == ["add", "boom", "echo", "no_args"]


async def test_call_tool_add():
    async with bridge() as conn:
        assert await conn.call_tool("add", {"a": 2, "b": 3}) == "5"


async def test_call_tool_echo_with_default():
    async with bridge() as conn:
        assert await conn.call_tool("echo", {"text": "hi"}) == "hi"
        assert await conn.call_tool("echo", {"text": "hi", "repeat": 3}) == "hi hi hi"


async def test_call_tool_no_args():
    async with bridge() as conn:
        assert await conn.call_tool("no_args", {}) == "ok"


async def test_call_tool_error_propagates():
    # Measured mcp 2.x behavior: the server wraps tool exceptions in
    # UnexpectedToolError; the client sees "Error executing tool boom"
    # (the original message stays server-side).
    async with bridge() as conn:
        with pytest.raises(RuntimeError, match="Error executing tool boom"):
            await conn.call_tool("boom", {})


async def test_load_mcp2_tools_names():
    async with tools_ctx() as tools:
        assert sorted(tools) == ["add", "boom", "echo", "no_args"]


async def test_structured_tool_invoke_add():
    async with tools_ctx() as tools:
        assert await tools["add"].ainvoke({"a": 40, "b": 2}) == "42"


async def test_structured_tool_default_applies():
    async with tools_ctx() as tools:
        assert await tools["echo"].ainvoke({"text": "yo"}) == "yo"


async def test_tool_description_survives():
    async with tools_ctx() as tools:
        assert "Add two integers" in tools["add"].description


async def test_tool_args_schema_validates():
    async with tools_ctx() as tools:
        add = tools["add"]
        parsed = add.args_schema.model_validate({"a": 1, "b": 2})
        assert parsed.a == 1 and parsed.b == 2
        with pytest.raises(Exception):
            add.args_schema.model_validate({"a": "not-an-int", "b": 2})


async def test_tool_error_surfaces_through_langchain():
    async with tools_ctx() as tools:
        with pytest.raises(Exception, match="Error executing tool boom"):
            await tools["boom"].ainvoke({})


def test_sanitize_tool_name():
    assert sanitize_tool_name("get-user!") == "get-user"
    assert sanitize_tool_name("a b/c") == "a_b_c"
    assert sanitize_tool_name("") == "unnamed_tool"


async def test_mcp_tool_to_langchain_unit():
    from mcp.types import Tool as MCPTool

    async def fake_call(name, args):
        return f"{name}:{args['x']}"

    tool = MCPTool(
        name="weird name!",
        description="",
        inputSchema={"type": "object", "properties": {"x": {"type": "integer"}}, "required": ["x"]},
    )
    lc = mcp_tool_to_langchain(tool, fake_call)
    assert lc.name == "weird_name"
    assert "MCP tool" in lc.description  # fallback description
    assert await lc.ainvoke({"x": 7}) == "weird name!:7"
