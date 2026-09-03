"""Integration tests for the Layer 2 demo arc (spec section 6, "Demo arc").

Run both pipelines on the `delta` fixtures -> DeltaReport contains exactly
the one planted discrepancy and matches golden expected_delta_report.json.
`corrected` fixtures -> zero_delta true + gate opens. The P2 LLM is mocked
throughout for determinism (no network).
"""
import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")

from agent.layer2 import trusted_data
from agent.layer2.pipelines import foundation_pipeline, pdf_pipeline
from agent.layer2.reconcile import reconcile

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent", "layer2", "fixtures"
)
# The golden fixture's source_refs embed this exact repo-root-relative path
# (spec/tests are run as `python3 -m pytest tests/test_layer2_*.py -q` from
# repo root), so the PDF path passed to pdf_pipeline.run must match verbatim.
SOURCE_A_PDF = "agent/layer2/fixtures/residential-unit.sourceA.pdf"
SOURCE_B_DELTA = os.path.join(FIXTURES_DIR, "residential-unit.sourceB.json")
SOURCE_B_CORRECTED = os.path.join(FIXTURES_DIR, "residential-unit.corrected.sourceB.json")
GOLDEN_PATH = os.path.join(FIXTURES_DIR, "expected_delta_report.json")

with open(GOLDEN_PATH) as f:
    GOLDEN_DELTA_REPORT = json.load(f)


def _mock_llm_extract_full(openai_client, text):
    """Every PDF line becomes an anchored candidate (mirrors test_layer2_pipelines.py)."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if ":" not in line or "," not in line:
            continue
        rest = line.split(":", 1)[1]
        qty_unit = rest.rsplit(",", 1)[-1].strip()
        qty_str, unit = qty_unit.split()
        quantity = int(qty_str) if qty_str.isdigit() else float(qty_str)
        items.append({
            "description": line.split(",")[0].strip(),
            "quantity": quantity,
            "unit": unit,
            "quote": line,
        })
    return items


@pytest.fixture(autouse=True)
def _clean_gate():
    trusted_data.reset()
    yield
    trusted_data.reset()


class TestDemoArcDirect:
    """Exercise the pipelines/reconciler/gate directly (no Flask)."""

    def test_delta_fixtures_match_golden_and_block_gate(self):
        itemization_a = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=_mock_llm_extract_full)
        itemization_b = foundation_pipeline.run(SOURCE_B_DELTA)
        report = reconcile(itemization_a, itemization_b)

        assert report.to_dict() == GOLDEN_DELTA_REPORT
        assert report.summary["zero_delta"] is False
        assert report.summary["delta_count"] == 1

        mismatches = [r for r in report.rows if r.status != "match"]
        assert len(mismatches) == 1
        assert mismatches[0].classification_code == "C1010"
        assert mismatches[0].status == "quantity_mismatch"
        assert mismatches[0].a_value["quantity"] == 380
        assert mismatches[0].b_value["quantity"] == 340

        with pytest.raises(trusted_data.GateBlocked) as exc_info:
            trusted_data.promote_to_trusted(report, key="demo")
        assert exc_info.value.report is report
        assert trusted_data.get_trusted("demo") is None

    def test_corrected_fixtures_are_zero_delta_and_promote(self):
        itemization_a = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=_mock_llm_extract_full)
        itemization_b = foundation_pipeline.run(SOURCE_B_CORRECTED)
        report = reconcile(itemization_a, itemization_b)

        assert report.summary["zero_delta"] is True
        assert report.summary["delta_count"] == 0
        assert all(r.status == "match" for r in report.rows)

        result = trusted_data.promote_to_trusted(report, key="demo")
        assert result == {"promoted": True, "key": "demo"}
        assert trusted_data.get_trusted("demo") == report.to_dict()


class TestDemoArcViaApi:
    """POST /api/reconcile end to end (spec section 8, Definition of Done)."""

    @pytest.fixture
    def client(self):
        from app2 import app, limiter

        app.config["TESTING"] = True
        limiter.enabled = False
        with app.test_client() as client:
            yield client
        limiter.enabled = True

    @patch("agent.layer2.pipelines.pdf_pipeline._default_llm_extract", side_effect=_mock_llm_extract_full)
    def test_delta_fixtures_return_blocked_gate(self, mock_llm, client):
        response = client.post("/api/reconcile", json={
            "variant": "delta",
            "key": "demo",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["gate"] == "BLOCKED"
        assert data["delta_report"] == GOLDEN_DELTA_REPORT
        mismatches = [r for r in data["delta_report"]["rows"] if r["status"] != "match"]
        assert len(mismatches) == 1
        assert mismatches[0]["classification_code"] == "C1010"

    @patch("agent.layer2.pipelines.pdf_pipeline._default_llm_extract", side_effect=_mock_llm_extract_full)
    def test_corrected_fixtures_return_promoted_gate(self, mock_llm, client):
        response = client.post("/api/reconcile", json={
            "variant": "corrected",
            "key": "demo",
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data["gate"] == "PROMOTED"
        assert data["delta_report"]["summary"]["zero_delta"] is True

    def test_invalid_variant_returns_400(self, client):
        response = client.post("/api/reconcile", json={
            "variant": "/etc/passwd",
        })
        assert response.status_code == 400

    def test_missing_payload_returns_400(self, client):
        response = client.post("/api/reconcile", json={})
        assert response.status_code == 400
