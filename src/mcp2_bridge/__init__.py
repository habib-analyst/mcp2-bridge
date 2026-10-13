"""mcp2-bridge: working LangGraph <-> MCP 2.x adapter + compat shim.

The canonical glue (langchain-mcp-adapters 0.3.2) pins mcp<2.0.0 while the
MCP Python SDK is at 2.x with breaking module reshuffles
(mcp.server.fastmcp gone). This package bridges that gap.
"""

from mcp2_bridge.adapter import (
    BridgeConnection,
    connect_stdio,
    load_mcp2_tools,
    mcp_tool_to_langchain,
)
from mcp2_bridge.compat import (
    COMPAT_MATRIX,
    ensure_fastmcp_shim,
    fastmcp_class,
    mcp_major_version,
    translate_import_path,
)
from mcp2_bridge.matrix import adapter_status, get_matrix

__all__ = [
    "BridgeConnection",
    "COMPAT_MATRIX",
    "adapter_status",
    "connect_stdio",
    "ensure_fastmcp_shim",
    "fastmcp_class",
    "get_matrix",
    "load_mcp2_tools",
    "mcp_major_version",
    "mcp_tool_to_langchain",
    "translate_import_path",
]

__version__ = "0.1.0"
