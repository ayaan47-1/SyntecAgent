"""Unit tests for Agent 3 (foundation_pipeline.py) and Agent 2 (pdf_pipeline.py).

P3: row -> LineItem mapping + classification.
P2: classification + that an unanchored item is excluded (mock the LLM).
Spec section 6.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.layer2.classify import UNCLASSIFIABLE
from agent.layer2.pipelines import foundation_pipeline, pdf_pipeline

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent", "layer2", "fixtures"
)
SOURCE_B = os.path.join(FIXTURES_DIR, "residential-unit.sourceB.json")
SOURCE_A_PDF = os.path.join(FIXTURES_DIR, "residential-unit.sourceA.pdf")


class TestFoundationPipeline:
    def test_run_maps_rows_to_line_items(self):
        result = foundation_pipeline.run(SOURCE_B)
        assert result.pipeline_id == "agent3-foundation"
        assert result.source_id == SOURCE_B
        assert len(result.items) == 16

    def test_classifies_known_component(self):
        result = foundation_pipeline.run(SOURCE_B)
        first = result.items[0]
        assert first.classification_code == "A1010"
        assert first.quantity == 120
        assert first.unit == "LF"
        assert first.source_ref == "B2"
        assert first.source_pipeline == "foundation"

    def test_all_rows_classify_against_ccn_vocab(self):
        # The sourceB fixture is crafted to match the CCN vocabulary; none
        # should fall through to UNCLASSIFIABLE.
        result = foundation_pipeline.run(SOURCE_B)
        codes = [i.classification_code for i in result.items]
        assert UNCLASSIFIABLE not in codes

    def test_unknown_component_is_unclassifiable(self, tmp_path):
        import json

        src = tmp_path / "unknown.json"
        src.write_text(json.dumps([
            {"component": "Something not in any vocabulary at all", "quantity": 1, "unit": "EA", "row_ref": "X1"}
        ]))
        result = foundation_pipeline.run(str(src))
        assert result.items[0].classification_code == UNCLASSIFIABLE


def _mock_llm_extract_full(openai_client, text):
    """Every PDF line becomes a candidate, anchored by its own verbatim text."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if ":" not in line or "," not in line:
            continue
        desc_part, rest = line.split(":", 1)
        pieces = rest.rsplit(",", 2)
        # "<detail>, <qty> <unit>" -> pieces = [detail, ' qty unit'] when only one comma
        qty_unit = pieces[-1].strip()
        qty_str, unit = qty_unit.split()
        items.append({
            "description": line.split(",")[0].strip(),
            "quantity": float(qty_str),
            "unit": unit,
            "quote": line,
        })
    return items


class TestPdfPipeline:
    def test_run_extracts_and_classifies(self):
        result = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=_mock_llm_extract_full)
        assert result.pipeline_id == "agent2-pdf"
        assert len(result.items) == 16
        first = result.items[0]
        assert first.classification_code == "A1010"
        assert first.quantity == 120
        assert first.unit == "LF"
        assert first.source_pipeline == "pdf"
        assert first.source_ref == f"pdf:{SOURCE_A_PDF}#0"

    def test_unanchored_candidate_is_dropped(self):
        def mock_extract(openai_client, text):
            return [
                {"description": "Standard Foundations", "quantity": 120, "unit": "LF",
                 "quote": "this text does not appear in the pdf anywhere"},
            ]
        result = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=mock_extract)
        assert result.items == []

    def test_missing_quote_is_dropped(self):
        def mock_extract(openai_client, text):
            return [{"description": "Standard Foundations", "quantity": 120, "unit": "LF"}]
        result = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=mock_extract)
        assert result.items == []

    def test_anchored_candidate_is_kept(self):
        def mock_extract(openai_client, text):
            return [{
                "description": "Standard Foundations: continuous concrete footing",
                "quantity": 120,
                "unit": "LF",
                "quote": "Standard Foundations: continuous concrete footing, 16in x 8in, 120 LF",
            }]
        result = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=mock_extract)
        assert len(result.items) == 1
        assert result.items[0].classification_code == "A1010"

    def test_mixed_anchored_and_unanchored(self):
        def mock_extract(openai_client, text):
            return [
                {
                    "description": "Standard Foundations: continuous concrete footing",
                    "quantity": 120,
                    "unit": "LF",
                    "quote": "Standard Foundations: continuous concrete footing, 16in x 8in, 120 LF",
                },
                {
                    "description": "Hallucinated Item",
                    "quantity": 999,
                    "unit": "EA",
                    "quote": "not in the pdf",
                },
            ]
        result = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=mock_extract)
        assert len(result.items) == 1
        assert result.items[0].description == "Standard Foundations: continuous concrete footing"

    def test_default_llm_extract_never_called_in_tests(self):
        # Sanity: the injected llm_extract is what's exercised, never the
        # real GPT-4o path, so these tests need no network / no OpenAI key.
        called = {"default": False}

        def mock_extract(openai_client, text):
            return []

        result = pdf_pipeline.run(SOURCE_A_PDF, llm_extract=mock_extract)
        assert result.items == []
        assert called["default"] is False
