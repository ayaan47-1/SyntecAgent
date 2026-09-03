"""Agent 3 — Foundation table pipeline.

Deterministic map of structured table rows to ``LineItem``s. No LLM: this is
the genuinely independent method that P2 (PDF/GPT-4o) is checked against.
"""
from __future__ import annotations

import json

from agent.layer2.classify import classify_component
from agent.layer2.models import LineItem, LineItemization

SOURCE_PIPELINE = "foundation"


def load_source(source_path: str) -> list:
    with open(source_path) as f:
        return json.load(f)


def run(source_path: str) -> LineItemization:
    """Read the Foundation table and classify each row into a LineItem."""
    rows = load_source(source_path)
    items = []
    for i, row in enumerate(rows):
        code = classify_component(row["component"])
        items.append(LineItem(
            classification_code=code,
            description=row["component"],
            quantity=row["quantity"],
            unit=row["unit"],
            source_ref=row.get("row_ref", f"row-{i}"),
            source_pipeline=SOURCE_PIPELINE,
        ))
    return LineItemization(pipeline_id="agent3-foundation", source_id=source_path, items=items)
