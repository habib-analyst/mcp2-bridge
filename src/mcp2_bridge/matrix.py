"""Programmatic compatibility matrix: which adapter works with which SDK."""

from __future__ import annotations

from mcp2_bridge.compat import COMPAT_MATRIX


def get_matrix() -> list[dict]:
    """Return the compatibility matrix rows (deep copies)."""
    return [dict(row) for row in COMPAT_MATRIX]


def _parse_major(version: str) -> int | None:
    try:
        return int(version.strip().split(".")[0])
    except (ValueError, AttributeError, IndexError):
        return None


def adapter_status(mcp_version: str, adapter: str) -> str:
    """Classify a (mcp SDK version, adapter) pair.

    Returns "supported", "broken", or "unknown".
    adapter is one of "langchain-mcp-adapters" (any 0.x) or "mcp2-bridge".
    """
    major = _parse_major(mcp_version)
    adapter = adapter.strip().lower()
    if major is None:
        return "unknown"
    if major >= 2:
        if adapter.startswith("langchain-mcp-adapters"):
            return "broken"
        if adapter == "mcp2-bridge":
            return "supported"
        return "unknown"
    # mcp 1.x
    if adapter.startswith("langchain-mcp-adapters") or adapter == "mcp2-bridge":
        return "supported"
    return "unknown"
