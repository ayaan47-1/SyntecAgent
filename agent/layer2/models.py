"""Layer 2 data models: LineItem, LineItemization, DeltaRow, DeltaReport."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

STATUSES = (
    "match",
    "quantity_mismatch",
    "unit_mismatch",
    "missing_in_A",
    "missing_in_B",
    "unclassifiable",
    "mixed_units",
)


@dataclass
class LineItem:
    classification_code: str
    description: str
    quantity: float
    unit: str
    source_ref: str
    source_pipeline: str  # "pdf" | "foundation"

    def to_dict(self) -> dict:
        return {
            "classification_code": self.classification_code,
            "description": self.description,
            "quantity": self.quantity,
            "unit": self.unit,
            "source_ref": self.source_ref,
            "source_pipeline": self.source_pipeline,
        }


@dataclass
class LineItemization:
    pipeline_id: str
    source_id: str
    items: list = field(default_factory=list)  # list[LineItem]

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "source_id": self.source_id,
            "items": [i.to_dict() for i in self.items],
        }


@dataclass
class DeltaRow:
    classification_code: str
    status: str
    a_value: Optional[dict]
    b_value: Optional[dict]
    severity: str

    def to_dict(self) -> dict:
        return {
            "classification_code": self.classification_code,
            "status": self.status,
            "a_value": self.a_value,
            "b_value": self.b_value,
            "severity": self.severity,
        }


@dataclass
class DeltaReport:
    rows: list = field(default_factory=list)  # list[DeltaRow]
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "rows": [r.to_dict() for r in self.rows],
            "summary": self.summary,
        }
