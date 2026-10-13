"""Compat shim + version-matrix boundary tests."""

import sys

import pytest

from mcp2_bridge.compat import (
    COMPAT_MATRIX,
    ensure_fastmcp_shim,
    fastmcp_class,
    mcp_major_version,
    translate_import_path,
)
from mcp2_bridge.matrix import adapter_status, get_matrix


def test_mcp_major_version_is_2():
    assert mcp_major_version() == 2


def test_fastmcp_class_is_mcpserver_on_2x():
    from mcp.server.mcpserver import MCPServer

    assert fastmcp_class() is MCPServer


def test_fastmcp_shim_allows_legacy_import():
    ensure_fastmcp_shim()
    assert "mcp.server.fastmcp" in sys.modules
    from mcp.server.fastmcp import FastMCP

    from mcp.server.mcpserver import MCPServer

    assert FastMCP is MCPServer
    server = FastMCP("shim-probe")
    assert server.name == "shim-probe"


def test_translate_import_path_known():
    assert translate_import_path("mcp.server.fastmcp.FastMCP") == "mcp.server.mcpserver.MCPServer"


def test_translate_import_path_removed():
    assert translate_import_path("mcp.shared.context.RequestContext") is None
    assert translate_import_path("mcp.server.fastmcp.Context") is None


def test_translate_import_path_unknown():
    assert translate_import_path("mcp.server.something.Else") is None


def test_matrix_rows_have_required_columns():
    for row in get_matrix():
        assert set(row) >= {"mcp_sdk", "langchain_mcp_adapters", "status", "notes"}


def test_matrix_documents_the_break():
    broken = [r for r in get_matrix() if r["status"] == "BROKEN"]
    assert len(broken) == 1
    assert "2.x" in broken[0]["mcp_sdk"]
    assert "0.3.2" in broken[0]["langchain_mcp_adapters"]


def test_adapter_status_boundaries():
    assert adapter_status("2.3.0", "langchain-mcp-adapters") == "broken"
    assert adapter_status("2.0.0", "langchain-mcp-adapters==0.3.2") == "broken"
    assert adapter_status("1.30.0", "langchain-mcp-adapters") == "supported"
    assert adapter_status("2.3.0", "mcp2-bridge") == "supported"
    assert adapter_status("1.24.0", "mcp2-bridge") == "supported"
    assert adapter_status("2.3.0", "something-else") == "unknown"
    assert adapter_status("garbage", "mcp2-bridge") == "unknown"
