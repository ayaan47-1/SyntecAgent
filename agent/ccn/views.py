"""Read ``05-Views`` as structured rows for the CCN rules engine (Step 2a).

Step 1 (:mod:`agent.ccn.parse`) pulls a single Views column as a vocabulary.
The rules engine needs *whole rows*: the two generated-name columns plus the
per-row component fields those names are composed from. Columns are resolved by
header **text**, never by position, because letters drift between revisions.

Only the canonical left-hand data table is read. The far-right stale ``(X)``
superseded block and loose guidance prose that Step 1 already identifies are
never touched here — the reader looks solely at the columns it resolved by
header, all of which sit left of the stale block.
"""
from __future__ import annotations

from dataclasses import dataclass

import openpyxl

from .parse import VIEWS_SHEET, _cell, _load_grid, _norm, _views_header_row


@dataclass(frozen=True)
class ViewRow:
    """One data row of ``05-Views`` with a 1-indexed source row for evidence.

    ``view_type``/``phase``/``discipline`` hold the *declared* component cells
    (``ABBR_Full Name`` form); the rules extract the abbreviation from them.
    """

    row: int
    generated_name: str
    value_only: str
    view_type: str
    level: str
    phase: str
    discipline: str


# Each field is resolved to a column by the first header cell whose lowercased
# text satisfies the predicate (leftmost match wins — this skips the duplicate
# bare "Level"/"Discipline" headers that reappear in the far-right stale block).
_COLUMN_SPECS = (
    ("generated_name", lambda h: "generated" in h),
    ("value_only", lambda h: "value only" in h),
    ("view_type", lambda h: "abb" in h and "view type" in h),
    ("level", lambda h: h == "level"),
    ("phase", lambda h: "abb" in h and "phase" in h),
    ("discipline", lambda h: "abb" in h and "discipline" in h),
)


def _resolve_columns(header_cells) -> dict:
    """Map each field name -> 0-indexed column (leftmost header match)."""
    resolved: dict = {}
    for c in range(len(header_cells)):
        text = _norm(header_cells[c]).lower()
        if not text:
            continue
        for field_name, predicate in _COLUMN_SPECS:
            if field_name not in resolved and predicate(text):
                resolved[field_name] = c
    return resolved


def read_views_rows(path: str) -> list:
    """Open ``path`` and return the ``05-Views`` data table as ``ViewRow``s."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if VIEWS_SHEET not in wb.sheetnames:
            return []
        grid = _load_grid(wb[VIEWS_SHEET])
    finally:
        wb.close()
    return rows_from_grid(grid)


def rows_from_grid(grid: list) -> list:
    """Build ``ViewRow``s from an already-loaded grid (testable without I/O)."""
    header_row = _views_header_row(grid)
    header_cells = grid[header_row] if header_row < len(grid) else ()
    cols = _resolve_columns(header_cells)

    def field(r: int, name: str) -> str:
        col = cols.get(name)
        return _cell(grid, r, col) if col is not None else ""

    rows: list = []
    for r in range(header_row + 1, len(grid)):
        record = {name: field(r, name) for name, _ in _COLUMN_SPECS}
        # A data row is one that carries a generated name (or its value-only
        # twin) or at least one declared component. Wholly empty rows and the
        # untouched right-hand hazards never qualify.
        if not any(record.values()):
            continue
        rows.append(
            ViewRow(
                row=r + 1,
                generated_name=record["generated_name"],
                value_only=record["value_only"],
                view_type=record["view_type"],
                level=record["level"],
                phase=record["phase"],
                discipline=record["discipline"],
            )
        )
    return rows
