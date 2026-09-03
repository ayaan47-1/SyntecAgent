"""Unit tests for the Layer 3 Trusted-Data gate (agent/layer2/trusted_data.py).

Promotes iff zero_delta; else GateBlocked carrying the report. Spec section 6.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from agent.layer2 import trusted_data
from agent.layer2.classify import UNCLASSIFIABLE
from agent.layer2.models import DeltaReport, DeltaRow, LineItem, LineItemization
from agent.layer2.reconcile import reconcile


def _report(zero_delta, rows=None):
    delta_count = 0 if zero_delta else 1
    return DeltaReport(
        rows=rows or [],
        summary={"codes": 1, "matched": 1 - delta_count, "delta_count": delta_count, "zero_delta": zero_delta},
    )


@pytest.fixture(autouse=True)
def _clean_store():
    trusted_data.reset()
    yield
    trusted_data.reset()


class TestGate:
    def test_promotes_when_zero_delta(self):
        report = _report(zero_delta=True)
        result = trusted_data.promote_to_trusted(report, key="demo")
        assert result == {"promoted": True, "key": "demo"}
        assert trusted_data.get_trusted("demo") == report.to_dict()

    def test_blocks_when_not_zero_delta(self):
        row = DeltaRow("C1010", "quantity_mismatch", {"quantity": 380}, {"quantity": 340}, "high")
        report = _report(zero_delta=False, rows=[row])
        with pytest.raises(trusted_data.GateBlocked) as exc_info:
            trusted_data.promote_to_trusted(report, key="demo")
        assert exc_info.value.report is report
        assert trusted_data.get_trusted("demo") is None

    def test_get_trusted_returns_none_when_never_promoted(self):
        assert trusted_data.get_trusted("never-promoted") is None

    def test_reset_clears_one_key(self):
        trusted_data.promote_to_trusted(_report(zero_delta=True), key="a")
        trusted_data.promote_to_trusted(_report(zero_delta=True), key="b")
        trusted_data.reset(key="a")
        assert trusted_data.get_trusted("a") is None
        assert trusted_data.get_trusted("b") is not None

    def test_reset_clears_all_keys(self):
        trusted_data.promote_to_trusted(_report(zero_delta=True), key="a")
        trusted_data.promote_to_trusted(_report(zero_delta=True), key="b")
        trusted_data.reset()
        assert trusted_data.get_trusted("a") is None
        assert trusted_data.get_trusted("b") is None

    def test_default_key(self):
        trusted_data.promote_to_trusted(_report(zero_delta=True))
        assert trusted_data.get_trusted() is not None

    def test_gate_blocked_message_names_delta_count(self):
        report = _report(zero_delta=False)
        try:
            trusted_data.promote_to_trusted(report)
        except trusted_data.GateBlocked as e:
            assert "1" in str(e)
        else:
            pytest.fail("GateBlocked not raised")


class TestGateFailsClosedOnEmptyEvidence:
    """Reconciling two empty (or all-UNCLASSIFIABLE) itemizations must never
    reach the gate as zero_delta=True — nothing-as-converged must not promote."""

    def test_both_empty_itemizations_does_not_promote(self):
        report = reconcile(
            LineItemization(pipeline_id="p2", source_id="a", items=[]),
            LineItemization(pipeline_id="p3", source_id="b", items=[]),
        )
        assert report.summary["zero_delta"] is False
        with pytest.raises(trusted_data.GateBlocked):
            trusted_data.promote_to_trusted(report, key="empty")
        assert trusted_data.get_trusted("empty") is None

    def test_all_unclassifiable_does_not_promote(self):
        item = LineItem(
            classification_code=UNCLASSIFIABLE,
            description="mystery widget",
            quantity=1,
            unit="EA",
            source_ref="r1",
            source_pipeline="pdf",
        )
        report = reconcile(
            LineItemization(pipeline_id="p2", source_id="a", items=[item]),
            LineItemization(pipeline_id="p3", source_id="b", items=[]),
        )
        assert report.summary["zero_delta"] is False
        with pytest.raises(trusted_data.GateBlocked):
            trusted_data.promote_to_trusted(report, key="unclassifiable")
        assert trusted_data.get_trusted("unclassifiable") is None
