"""LangGraph agent end-to-end with bridged MCP 2.x tools.

Run: python examples/langgraph_agent.py
A scripted planner node (deterministic stand-in for an LLM) parses a simple
"a+b" question and calls the bridged `add` tool through a real StateGraph.
"""

import asyncio
import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langgraph.graph import END, StateGraph

from mcp2_bridge import connect_stdio, load_mcp2_tools

SERVER = Path(__file__).resolve().parents[1] / "tests" / "server_2x.py"


class AgentState(TypedDict):
    question: str
    answer: str


async def main() -> None:
    async with connect_stdio(sys.executable, [str(SERVER)]) as conn:
        tools = await load_mcp2_tools(conn)
        add = next(t for t in tools if t.name == "add")

        async def planner(state: AgentState) -> AgentState:
            lhs, rhs = (p.strip() for p in state["question"].split("+"))
            out = await add.ainvoke({"a": int(lhs), "b": int(rhs)})
            return {"question": state["question"], "answer": f"The answer is {out}."}

        graph = StateGraph(AgentState)
        graph.add_node("planner", planner)
        graph.set_entry_point("planner")
        graph.add_edge("planner", END)
        app = graph.compile()

        final = await app.ainvoke({"question": "19+23", "answer": ""})
        print(final["answer"])


if __name__ == "__main__":
    asyncio.run(main())
