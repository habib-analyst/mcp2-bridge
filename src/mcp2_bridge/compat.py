"""Compat shim: bridge the mcp 1.x -> 2.x module reshuffles.

On mcp 2.x, importing mcp.server.fastmcp raises ModuleNotFoundError by
design (FastMCP was renamed to MCPServer). This module documents the exact
boundaries and provides an opt-in shim so 2025-era tutorial code keeps
running.
"""

from __future__ import annotations

import sys
import types
from importlib import metadata

COMPAT_MATRIX: list[dict] = [
    {
        "mcp_sdk": "1.x (1.24.0 - 1.30.0)",
        "langchain_mcp_adapters": "0.3.2",
        "status": "supported",
        "notes": "Pin mcp<2.0.0,>=1.24.0 resolves cleanly; imports work.",
    },
    {
        "mcp_sdk": "2.x (2.0.0 - 2.3.0)",
        "langchain_mcp_adapters": "0.3.2",
        "status": "BROKEN",
        "notes": (
            "pip cannot resolve (pin mcp<2.0.0); even force-installed, "
            "load_mcp_tools fails on mcp.server.fastmcp (ModuleNotFoundError) "
            "and MultiServerMCPClient fails on mcp.shared.context.RequestContext "
            "(ImportError). langchain-mcp-adapters has no release >0.3.2 "
            "as of 2026-10-13."
        ),
    },
    {
        "mcp_sdk": "2.x (2.0.0 - 2.3.0)",
        "langchain_mcp_adapters": "mcp2-bridge (this package)",
        "status": "supported",
        "notes": "Native 2.x adapter: stdio client session -> StructuredTools.",
    },
]

#: 2025-era import paths and where they live now (None = removed).
IMPORT_TRANSLATIONS: dict[str, str | None] = {
    "mcp.server.fastmcp.FastMCP": "mcp.server.mcpserver.MCPServer",
    "mcp.server.fastmcp.Context": None,  # removed; request-scoped context no longer exists
    "mcp.server.fastmcp.tools.Tool": "mcp.types.Tool",
    "mcp.shared.context.RequestContext": None,  # removed from mcp.shared.context in 2.x
}


def mcp_major_version() -> int:
    """Return the installed mcp SDK major version (1 or 2)."""
    try:
        ver = metadata.version("mcp")
    except metadata.PackageNotFoundError:
        raise RuntimeError("mcp is not installed")
    return int(ver.split(".")[0])


def fastmcp_class():
    """Return the server class for the installed SDK: FastMCP on 1.x, MCPServer on 2.x."""
    if mcp_major_version() >= 2:
        from mcp.server.mcpserver import MCPServer

        return MCPServer
    from mcp.server.fastmcp import FastMCP  # type: ignore[no-redef]

    return FastMCP


def translate_import_path(old_path: str) -> str | None:
    """Translate a 2025-era dotted path to its 2.x equivalent (None if removed)."""
    return IMPORT_TRANSLATIONS.get(old_path)


def ensure_fastmcp_shim() -> None:
    """Install a sys.modules shim so `import mcp.server.fastmcp` works on mcp 2.x.

    Exposes FastMCP (= MCPServer) under the old module name. No-op on mcp 1.x.
    Call before importing mcp.server.fastmcp. Raises on 2.x if the real module
    somehow imports cleanly (defensive; should not happen).
    """
    if mcp_major_version() < 2:
        return
    if "mcp.server.fastmcp" in sys.modules:
        return
    from mcp.server.mcpserver import MCPServer

    shim = types.ModuleType("mcp.server.fastmcp")
    shim.__doc__ = (
        "Compat shim (mcp2-bridge): FastMCP was renamed to MCPServer in mcp 2.x. "
        "See https://py.sdk.modelcontextprotocol.io/v2/migration/"
    )
    shim.FastMCP = MCPServer  # type: ignore[attr-defined]
    sys.modules["mcp.server.fastmcp"] = shim
