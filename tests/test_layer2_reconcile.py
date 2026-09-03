"""Unit tests for Agent 4a's reconciler (agent/layer2/reconcile.py).

Truth table: zero_delta true iff every code matches; each mismatch type;
unclassifiable handling. Spec section 6.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.layer2.classify import UNCLASSIFIABLE
from agent.layer2.models import LineItem, LineItemization
from agent.layer2.reconcile import reconcile


def _item(code, qty, unit="SF", ref="ref", pipeline="pdf"):
    return LineItem(
        classification_code=code,
        description=f"desc-{code}",
        quantity=qty,
        unit=unit,
        source_ref=ref,
        source_pipeline=pipeline,
    )


def _itemization(pipeline_id, source_id, items):
    return LineItemization(pipeline_id=pipeline_id, source_id=source_id, items=items)


class TestZeroDelta:
    def test_all_codes_match_is_zero_delta(self):
        a = _itemization("p2", "a", [_item("A1010", 120, "LF")])
        b = _itemization("p3", "b", [_item("A1010", 120, "LF")])
        report = reconcile(a, b)
        assert report.summary["zero_delta"] is True
        assert report.summary["delta_count"] == 0
        assert report.rows[0].status == "match"
        assert report.rows[0].severity == "none"

    def test_single_mismatch_is_not_zero_delta(self):
        a = _itemization("p2", "a", [_item("A1010", 120, "LF"), _item("B1010", 950, "SF")])
        b = _itemization("p3", "b", [_item("A1010", 120, "LF"), _item("B1010", 900, "SF")])
        report = reconcile(a, b)
        assert report.summary["zero_delta"] is False
        assert report.summary["delta_count"] == 1


class TestMismatchTypes:
    def test_quantity_mismatch(self):
        a = _itemization("p2", "a", [_item("C1010", 380, "SF")])
        b = _itemization("p3", "b", [_item("C1010", 340, "SF")])
        report = reconcile(a, b)
        row = report.rows[0]
        assert row.status == "quantity_mismatch"
        assert row.severity == "high"
        assert row.a_value["quantity"] == 380
        assert row.b_value["quantity"] == 340

    def test_unit_mismatch(self):
        a = _itemization("p2", "a", [_item("C1010", 100, "SF")])
        b = _itemization("p3", "b", [_item("C1010", 100, "LF")])
        report = reconcile(a, b)
        row = report.rows[0]
        assert row.status == "unit_mismatch"
        assert row.severity == "medium"

    def test_unit_mismatch_is_case_and_whitespace_insensitive(self):
        a = _itemization("p2", "a", [_item("C1010", 100, " SF ")])
        b = _itemization("p3", "b", [_item("C1010", 100, "sf")])
        report = reconcile(a, b)
        assert report.rows[0].status == "match"

    def test_missing_in_a(self):
        a = _itemization("p2", "a", [])
        b = _itemization("p3", "b", [_item("A1010", 120, "LF")])
        report = reconcile(a, b)
        row = report.rows[0]
        assert row.status == "missing_in_A"
        assert row.severity == "high"
        assert row.a_value is None
        assert row.b_value is not None

    def test_missing_in_b(self):
        a = _itemization("p2", "a", [_item("A1010", 120, "LF")])
        b = _itemization("p3", "b", [])
        report = reconcile(a, b)
        row = report.rows[0]
        assert row.status == "missing_in_B"
        assert row.severity == "high"
        assert row.a_value is not None
        assert row.b_value is None


class TestUnclassifiable:
    def test_unclassifiable_in_a_is_not_silently_dropped(self):
        a = _itemization("p2", "a", [_item(UNCLASSIFIABLE, 10, "EA")])
        b = _itemization("p3", "b", [])
        report = reconcile(a, b)
        assert len(report.rows) == 1
        row = report.rows[0]
        assert row.status == "unclassifiable"
        assert row.classification_code == UNCLASSIFIABLE
        assert row.severity == "high"
        assert row.a_value is not None
        assert row.b_value is None

    def test_unclassifiable_in_b_is_not_silently_dropped(self):
        a = _itemization("p2", "a", [])
        b = _itemization("p3", "b", [_item(UNCLASSIFIABLE, 10, "EA")])
        report = reconcile(a, b)
        assert len(report.rows) == 1
        row = report.rows[0]
        assert row.status == "unclassifiable"
        assert row.a_value is None
        assert row.b_value is not None

    def test_unclassifiable_does_not_block_other_codes_matching(self):
        a = _itemization("p2", "a", [_item(UNCLASSIFIABLE, 10, "EA"), _item("A1010", 120, "LF")])
        b = _itemization("p3", "b", [_item("A1010", 120, "LF")])
        report = reconcile(a, b)
        statuses = {r.classification_code: r.status for r in report.rows}
        assert statuses[UNCLASSIFIABLE] == "unclassifiable"
        assert statuses["A1010"] == "match"
        # unclassifiable rows count toward delta_count (not zero_delta)
        assert report.summary["zero_delta"] is False


class TestGroupingAndSummary:
    def test_multiple_items_same_code_are_summed(self):
        a = _itemization("p2", "a", [_item("A1010", 60, "LF", "r1"), _item("A1010", 60, "LF", "r2")])
        b = _itemization("p3", "b", [_item("A1010", 120, "LF", "r3")])
        report = reconcile(a, b)
        row = report.rows[0]
        assert row.status == "match"
        assert row.a_value["quantity"] == 120
        assert row.a_value["source_refs"] == ["r1", "r2"]

    def test_summary_counts(self):
        a = _itemization("p2", "a", [_item("A1010", 120, "LF"), _item("B1010", 100, "SF")])
        b = _itemization("p3", "b", [_item("A1010", 120, "LF"), _item("B1010", 999, "SF")])
        report = reconcile(a, b)
        assert report.summary["codes"] == 2
        assert report.summary["matched"] == 1
        assert report.summary["delta_count"] == 1
        assert report.summary["zero_delta"] is False
