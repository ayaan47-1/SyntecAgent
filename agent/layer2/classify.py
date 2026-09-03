"""Agent-1 adapter: the shared classification join key for Layer 2.

Thin wrapper over ``agent.ccn.parse`` (Agent 1). Builds a keyword index from
the CCN vocabulary's Uniformat block and returns the canonical
``classification_code`` for a component description, or ``UNCLASSIFIABLE``
when the vocabulary has no match (surfaced honestly, never silently dropped
— see spec section 5).
"""
from __future__ import annotations

import os
import threading

from agent.ccn.parse import parse_workbook

UNCLASSIFIABLE = "UNCLASSIFIABLE"

DEFAULT_VOCAB_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "ccn_vocabulary.xlsx")

_lock = threading.Lock()
_index_cache: dict = {}


def _build_index(vocab_path: str) -> dict:
    """keyword (lowercased description) -> classification_code."""
    result = parse_workbook(vocab_path)
    index: dict = {}
    for vocab in result.vocabularies:
        if vocab.name != "Uniformat":
            continue
        for entry in vocab.entries:
            code = entry.code
            if not code:
                continue
            desc = entry.value
            if desc.startswith(code):
                desc = desc[len(code):]
            keyword = desc.strip().lower()
            if keyword:
                index[keyword] = code
    return index


def _index_for(vocab_path: str) -> dict:
    with _lock:
        if vocab_path not in _index_cache:
            _index_cache[vocab_path] = _build_index(vocab_path)
        return _index_cache[vocab_path]


def classify_component(description: str, vocab_path: str = DEFAULT_VOCAB_PATH) -> str:
    """Return the CCN classification_code for a component description.

    Matches by keyword substring against the Agent-1 Uniformat vocabulary.
    Returns UNCLASSIFIABLE when no vocabulary entry's description appears in
    the given text.
    """
    text = (description or "").lower()
    if not text:
        return UNCLASSIFIABLE
    index = _index_for(vocab_path)
    for keyword, code in index.items():
        if keyword in text:
            return code
    return UNCLASSIFIABLE
