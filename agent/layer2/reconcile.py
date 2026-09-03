"""Agent 4a — the zero-delta reconciler.

Deterministic join by ``classification_code`` over the two source-pipeline-
tagged LineItemizations. No LLM: this *is* the zero-delta compliance
analysis (spec section 5, "Determinism").
"""
from __future__ import annotations

from agent.layer2.classify import UNCLASSIFIABLE
from agent.layer2.models import DeltaReport, DeltaRow, LineItemization


def _norm_unit(unit: str) -> str:
    return (unit or "").strip().lower()


def _summarize(items: list) -> dict:
    return {
        "quantity": sum(i.quantity for i in items),
        "unit": items[0].unit,
        "source_refs": [i.source_ref for i in items],
    }


def _group_by_code(items: list) -> dict:
    grouped: dict = {}
    for item in items:
        grouped.setdefault(item.classification_code, []).append(item)
    return grouped


def _has_mixed_units(items: list) -> bool:
    return len({_norm_unit(i.unit) for i in items}) > 1


def _summarize_mixed(items: list) -> dict:
    # Never sum across differing units -- report the per-unit breakdown instead.
    by_unit: dict = {}
    for item in items:
        by_unit[_norm_unit(item.unit)] = by_unit.get(_norm_unit(item.unit), 0) + item.quantity
    return {"by_unit": by_unit, "source_refs": [i.source_ref for i in items]}


def reconcile(itemization_a: LineItemization, itemization_b: LineItemization) -> DeltaReport:
    """Join both itemizations on classification_code and diff each group."""
    by_a = _group_by_code(itemization_a.items)
    by_b = _group_by_code(itemization_b.items)

    rows: list = []

    unclassifiable_a = by_a.pop(UNCLASSIFIABLE, [])
    unclassifiable_b = by_b.pop(UNCLASSIFIABLE, [])
    for item in unclassifiable_a:
        rows.append(DeltaRow(UNCLASSIFIABLE, "unclassifiable", _summarize([item]), None, "high"))
    for item in unclassifiable_b:
        rows.append(DeltaRow(UNCLASSIFIABLE, "unclassifiable", None, _summarize([item]), "high"))

    for code in sorted(set(by_a) | set(by_b)):
        a_items = by_a.get(code, [])
        b_items = by_b.get(code, [])

        if (a_items and _has_mixed_units(a_items)) or (b_items and _has_mixed_units(b_items)):
            a_val = _summarize_mixed(a_items) if a_items else None
            b_val = _summarize_mixed(b_items) if b_items else None
            rows.append(DeltaRow(code, "mixed_units", a_val, b_val, "high"))
            continue

        if not a_items:
            rows.append(DeltaRow(code, "missing_in_A", None, _summarize(b_items), "high"))
            continue
        if not b_items:
            rows.append(DeltaRow(code, "missing_in_B", _summarize(a_items), None, "high"))
            continue

        a_summary = _summarize(a_items)
        b_summary = _summarize(b_items)
        if _norm_unit(a_summary["unit"]) != _norm_unit(b_summary["unit"]):
            rows.append(DeltaRow(code, "unit_mismatch", a_summary, b_summary, "medium"))
        elif a_summary["quantity"] != b_summary["quantity"]:
            rows.append(DeltaRow(code, "quantity_mismatch", a_summary, b_summary, "high"))
        else:
            rows.append(DeltaRow(code, "match", a_summary, b_summary, "none"))

    delta_count = sum(1 for r in rows if r.status != "match")
    matched = len(rows) - delta_count
    summary = {
        "codes": len(rows),
        "matched": matched,
        "delta_count": delta_count,
        # fail-closed: zero delta rows with no matched evidence (e.g. both
        # itemizations empty) must not read as convergence — see spec section 5.
        "zero_delta": delta_count == 0 and matched > 0,
    }
    return DeltaReport(rows=rows, summary=summary)
