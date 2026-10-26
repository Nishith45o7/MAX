"""
Tideline Long-Term Memory Package.
Model-agnostic memory engine with provenance write-gate, origin isolation,
hybrid BM25+vector recall, bi-temporal decay, typed link graph, and MCP server.
"""
from pathlib import Path
from typing import Optional
from tideline.schema import FactRecord, FactSegment, FactTier
from tideline.store import FactStore
from tideline.engine import TidelineEngine

def open_memory(workspace_dir: Path, origin: str = "owner") -> TidelineEngine:
    """Opens a Tideline memory engine for a workspace."""
    store = FactStore(workspace_dir)
    return TidelineEngine(store, default_origin=origin)

__all__ = ["FactRecord", "FactSegment", "FactTier", "FactStore", "TidelineEngine", "open_memory"]
