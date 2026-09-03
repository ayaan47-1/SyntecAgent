"""Unit tests for the Agent-1 classification adapter (agent/layer2/classify.py).

Word-boundary matching must be deterministic and order-independent: a short
keyword (e.g. "door") must never hijack an unrelated longer description
(e.g. "outdoor lighting"), and the longest matching keyword wins regardless
of vocabulary dict-iteration order. Spec section 5, "Determinism".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.layer2 import classify
from agent.layer2.classify import UNCLASSIFIABLE, classify_component

FAKE_VOCAB_PATH = "fake-vocab.xlsx"


def _patch_index(monkeypatch, index: dict):
    monkeypatch.setattr(classify, "_index_cache", {FAKE_VOCAB_PATH: index})


class TestWordBoundaryMatching:
    def test_short_keyword_does_not_hijack_unrelated_description(self, monkeypatch):
        _patch_index(monkeypatch, {"door": "C1010", "outdoor lighting": "E2010"})
        code = classify_component("outdoor lighting fixture", vocab_path=FAKE_VOCAB_PATH)
        assert code == "E2010"

    def test_short_keyword_still_matches_on_its_own(self, monkeypatch):
        _patch_index(monkeypatch, {"door": "C1010", "outdoor lighting": "E2010"})
        code = classify_component("interior door assembly", vocab_path=FAKE_VOCAB_PATH)
        assert code == "C1010"

    def test_no_partial_word_match(self, monkeypatch):
        # "door" must not match inside "doorbell" (not a word-boundary hit).
        _patch_index(monkeypatch, {"door": "C1010"})
        code = classify_component("doorbell wiring", vocab_path=FAKE_VOCAB_PATH)
        assert code == UNCLASSIFIABLE

    def test_result_independent_of_vocabulary_insertion_order(self, monkeypatch):
        text = "outdoor lighting fixture"
        _patch_index(monkeypatch, {"door": "C1010", "outdoor lighting": "E2010"})
        code_a = classify_component(text, vocab_path=FAKE_VOCAB_PATH)

        _patch_index(monkeypatch, {"outdoor lighting": "E2010", "door": "C1010"})
        code_b = classify_component(text, vocab_path=FAKE_VOCAB_PATH)

        assert code_a == code_b == "E2010"

    def test_longest_match_wins_among_multiple_hits(self, monkeypatch):
        _patch_index(monkeypatch, {
            "concrete": "A1010",
            "concrete slab": "A1030",
            "concrete slab foundation": "A1035",
        })
        code = classify_component("cast-in-place concrete slab foundation work", vocab_path=FAKE_VOCAB_PATH)
        assert code == "A1035"

    def test_no_match_returns_unclassifiable(self, monkeypatch):
        _patch_index(monkeypatch, {"door": "C1010"})
        code = classify_component("something entirely unrelated", vocab_path=FAKE_VOCAB_PATH)
        assert code == UNCLASSIFIABLE
