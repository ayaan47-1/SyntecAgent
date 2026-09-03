"""Layer 3 — the Trusted-Data gate.

``promote_to_trusted`` writes the reconciled itemization to the Trusted-Data
store iff ``zero_delta``, else raises ``GateBlocked`` carrying the report.
Deterministic, no LLM (spec section 5).

PoC store: an in-memory dict, keyed like a ChromaDB/SQLite record would be
(spec section 3.2.6) — a real collection/table is a drop-in swap behind
``init()`` (mirrors ``agent/chromadb_sync.py``'s late-binding pattern)
without touching the gate logic itself.
"""
from __future__ import annotations

from agent.layer2.models import DeltaReport

_store: dict = {}


class GateBlocked(Exception):
    """Raised when a DeltaReport is not zero_delta; carries the report."""

    def __init__(self, report: DeltaReport):
        self.report = report
        delta_count = report.summary.get("delta_count")
        super().__init__(f"Gate blocked: {delta_count} delta row(s) outstanding")


def promote_to_trusted(report: DeltaReport, key: str = "default") -> dict:
    """Promote a reconciled itemization to Trusted Data iff zero_delta."""
    if not report.summary.get("zero_delta"):
        raise GateBlocked(report)
    _store[key] = report.to_dict()
    return {"promoted": True, "key": key}


def get_trusted(key: str = "default"):
    """Return the trusted record for `key`, or None if never promoted."""
    return _store.get(key)


def reset(key: str = None) -> None:
    """Test/demo helper: clear the store (or one key)."""
    if key is None:
        _store.clear()
    else:
        _store.pop(key, None)
