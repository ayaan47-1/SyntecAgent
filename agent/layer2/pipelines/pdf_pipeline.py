"""Agent 2 — PDF pipeline.

Extracts candidate line items from a drawings/specs PDF using SyntecAgent's
existing OpenAI GPT-4o wiring, then anchors each candidate to the PDF's own
text (Veritas's quote-anchor discipline, borrowed as a pattern only): a
candidate whose ``quote`` does not appear verbatim in the extracted text is
dropped and never counted (spec section 5, "Anti-hallucination").

``llm_extract`` is an injected callable so tests (and the anchor-drop path)
never need a live OpenAI call — only ``_default_llm_extract`` talks to the
network, and it is never invoked in this repo's test suite.
"""
from __future__ import annotations

from PyPDF2 import PdfReader

from agent.layer2.classify import classify_component
from agent.layer2.models import LineItem, LineItemization

SOURCE_PIPELINE = "pdf"

_EXTRACTION_SYSTEM_PROMPT = (
    "You extract construction line items from a drawings/specs document. "
    "For each item return description, quantity, unit, and quote — quote "
    "must be an exact, verbatim substring of the source text that supports "
    "the item. Respond as JSON: {\"items\": [...]}."
)


def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _default_llm_extract(openai_client, text: str) -> list:
    """Real GPT-4o extraction. Never called in tests — always inject `llm_extract`."""
    import json

    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        response_format={"type": "json_object"},
    )
    payload = json.loads(response.choices[0].message.content)
    return payload.get("items", [])


def run(pdf_path: str, openai_client=None, llm_extract=None) -> LineItemization:
    """Extract, anchor, and classify line items from the PDF into a LineItemization."""
    text = extract_pdf_text(pdf_path)
    extract_fn = llm_extract or _default_llm_extract
    candidates = extract_fn(openai_client, text)

    items = []
    for i, candidate in enumerate(candidates):
        quote = candidate.get("quote", "")
        if not quote or quote not in text:
            continue  # unanchored: dropped, never counted
        code = classify_component(candidate["description"])
        items.append(LineItem(
            classification_code=code,
            description=candidate["description"],
            quantity=candidate["quantity"],
            unit=candidate["unit"],
            source_ref=f"pdf:{pdf_path}#{i}",
            source_pipeline=SOURCE_PIPELINE,
        ))
    return LineItemization(pipeline_id="agent2-pdf", source_id=pdf_path, items=items)
