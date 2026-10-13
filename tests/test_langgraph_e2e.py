"""End-to-end: a real LangGraph StateGraph using bridged MCP 2.x tools.

The planner node is scripted (deterministic stand-in for an LLM call);
documented as such in PAPER.md. Everything else is real: real stdio wire,
real MCP 2.x server, real StructuredTool, real StateGraph execution.
"""

import sys
from pathlib import Path
from typing import TypedDict

import pytest

from mcp2_bridge.adapter import connect_stdio, load_mcp2_tools

pytestmark = pytest.mark.asyncio

SERVER = Path(__file__).parent / "server_2x.py"


class AgentState(TypedDict):
    question: str
    tool_calls: list
    result: str


async def test_langgraph_agent_uses_bridged_tools():
    async with connect_stdio(sys.executable, [str(SERVER)]) as conn:
        tools = await load_mcp2_tools(conn)
        by_name = {t.name: t for t in tools}

        # Scripted planner: parses "a+b" out of the question, calls the
        # bridged `add` tool through LangChain's standard tool interface.
        async def planner(state: AgentState) -> AgentState:
            question = state["question"]
            lhs, rhs = (p.strip() for p in question.split("+"))
            out = await by_name["add"].ainvoke({"a": int(lhs), "b": int(rhs)})
            return {
                "question": question,
                "tool_calls": state["tool_calls"] + [("add", {"a": lhs, "b": rhs})],
                "result": f"The answer is {out}.",
            }

        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("planner", planner)
        graph.set_entry_point("planner")
        graph.add_edge("planner", END)
        app = graph.compile()

        final = await app.ainvoke(
            {"question": "19+23", "tool_calls": [], "result": ""},
            config={"recursion_limit": 10},
        )

    assert final["result"] == "The answer is 42."
    assert final["tool_calls"] == [("add", {"a": "19", "b": "23"})]


async def test_langgraph_agent_tool_error_path():
    async with connect_stdio(sys.executable, [str(SERVER)]) as conn:
        tools = await load_mcp2_tools(conn)
        by_name = {t.name: t for t in tools}

        async def planner(state: AgentState) -> AgentState:
            try:
                await by_name["boom"].ainvoke({})
                result = "no error"
            except Exception as exc:  # noqa: BLE001
                result = f"caught: {exc}"
            return {"question": state["question"], "tool_calls": [], "result": result}

        from langgraph.graph import END, StateGraph

        graph = StateGraph(AgentState)
        graph.add_node("planner", planner)
        graph.set_entry_point("planner")
        graph.add_edge("planner", END)
        app = graph.compile()

        final = await app.ainvoke(
            {"question": "trigger the error tool", "tool_calls": [], "result": ""},
        )

    assert "caught:" in final["result"] and "Error executing tool boom" in final["result"]
