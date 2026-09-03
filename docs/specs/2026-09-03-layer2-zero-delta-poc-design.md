# Layer 2 Zero-Delta Verification — Proof of Concept Design

**Date:** 2026-09-03
**Status:** Approved design (brainstorm complete) — pending user review, then implementation.
**Owner:** god (orchestrator) authored; build to be dispatched to a capped worker.
**Repo/branch:** **SyntecAgent** (`github.com/ayaan47-1/SyntecAgent`), branch `feat/poc-layer2-zero-delta`
off the CCN tip `8d11ab5`. **Not merged.**

> **Home correction (2026-09-03):** an earlier draft of this spec targeted VeritasLayer (FastAPI). That
> was the wrong repo. Per the BUSA "Description of BUSAai Agents" doc (V2.01), the BCE stack is
> **SyntecAgent** (Flask + ChromaDB), which already hosts **Agent 1 (CCN)**. Veritas is a *separate*
> product — Agent A (Document Review / Obligations & Risks) at Layer 4; its extract→verify→reconcile
> is reused only as a *pattern*, not as a dependency or home.

---

## 1. Purpose & Thesis

BuildUSA's promises of speed, cost, and quality must be **verifiable, not aspirational**. The mechanism
is **Layer 2 — the zero-delta Verification Engine**: independent pipelines derive the *same* deliverable
from *different* source formats, and **convergence across independently-derived outputs is evidence of
accuracy** (an error specific to one extraction method is unlikely to correlate with the others).

This PoC proves that thesis on a small synthetic building-type slice, inside the SyntecAgent stack,
building on the existing Agent 1 (CCN) classification work.

**Success criterion:** two independent pipelines each produce a Line Itemization from two different
synthetic sources; the `Agent 4a` reconciler detects a *deliberately planted* discrepancy (non-zero
delta), the Layer 3 Trusted-Data gate refuses promotion while the delta stands, and after the source is
corrected the pipelines converge to **zero delta** and the gate promotes. All asserted by tests.

## 2. Scope

**In scope (PoC):**
- ONE building-type slice (a residential unit, ~15–25 components).
- ONE deliverable: **Line Itemization** (the foundational deliverable; Concept Budget & Bid Packages derive from it).
- **TWO** independent pipelines: **Agent 2** (PDF) and **Agent 3** (Foundation table). (Confirmed with user; the Notes-DB pipeline is the named fast-follow to reach the doc's full three-way triangulation.)
- **Agent 4a** reconciler + Layer 3 Trusted-Data gate.
- Line items tagged by `source_pipeline` and stored in **ChromaDB** (per the doc) so `Agent 4a` compares the two tagged sets.
- ONE planted discrepancy: detect → block → resolve → zero-delta → promote.
- Surface: a Flask endpoint `POST /api/reconcile` on `app2.py`, matching the existing 3-endpoint pattern (`/api/health`, `/api/ingest`, `/api/chat`).

**Out of scope (named fast-follows):**
- Concept Budget & Bid Package deliverables.
- The **third (Notes-DB) pipeline** — the full three-way triangulation.
- Real `Agent 5a` tuning workflow (PoC only *flags* a delta for tuning; no human-loop UI).
- Agents 4b–e / 5b–e, Agent A, Agent B; Layers 4/6/7.
- Real (non-synthetic) source data. A source-loader seam keeps real workbook/PDF/BIM data a drop-in later.

## 3. Architecture

### 3.1 The shared contract (the crux)

Zero-delta is only possible if every line item across both pipelines carries a **shared join key**: the
**Agent-1 classification code**. Without a shared coding scheme, two independently-derived itemizations
cannot be compared. This makes **Agent 1 the enabler** of Layer 2, not a separate track.

**Agent 1 today** (`agent/ccn/`): `parse.py:parse_workbook(path) -> ParseResult` yields the canonical
classification **vocabulary** (Construction Nature, Disciplines, Uniformat, Revit categories, Orgs, etc.);
`rules.py` validates naming. The PoC uses this parsed vocabulary as the **authoritative code set** both
pipelines map their items to. (The doc's future `/classify` free-text endpoint is out of PoC scope — we
consume the vocabulary directly.)

```
LineItem        = { classification_code, description, quantity, unit, source_ref, source_pipeline }
LineItemization = { pipeline_id, source_id, items: [LineItem, ...] }
DeltaRow        = { classification_code, status, a_value, b_value, severity }
DeltaReport     = { rows: [...], summary: { codes, matched, delta_count, zero_delta: bool } }
```
`status ∈ { match, quantity_mismatch, unit_mismatch, missing_in_A, missing_in_B, unclassifiable }`.
`classification_code` is the authoritative join key; `source_ref` anchors each item to its origin
(PDF page/line or table row).

### 3.2 Components

1. **Synthetic fixtures** (`agent/layer2/fixtures/`): one residential-unit slice as two sources that agree on
   every component *except one planted delta*, both authored using **real codes from the CCN vocabulary**:
   - `residential-unit.sourceA.pdf` — synthetic drawings/specs PDF (a few pages).
   - `residential-unit.sourceB.json` — structured Foundation table (classification-table shape).
   - `residential-unit.corrected.sourceB.json` — the aligned variant.
   - `expected_delta_report.json` — golden output.

2. **Pipeline P2 — `Agent 2` (PDF path)** (`agent/layer2/pipelines/pdf_pipeline.py`): extracts line items
   from the PDF using SyntecAgent's existing **OpenAI GPT-4o** wiring; each extracted item is **anchored**
   to the PDF text (borrowing Veritas's quote-anchor idea — an item that does not anchor is dropped, never
   counted) and classified to a CCN code → `LineItemization_A`.

3. **Pipeline P3 — `Agent 3` (Foundation path)** (`agent/layer2/pipelines/foundation_pipeline.py`):
   deterministic map of table rows → `LineItem`s with CCN codes → `LineItemization_B`. Minimal/no LLM —
   a genuinely independent method from P2.

4. **Classification adapter** (`agent/layer2/classify.py`): thin wrapper over `agent/ccn` returning the
   canonical `classification_code` for a component (and `unclassifiable` when the vocabulary has no match).

5. **`Agent 4a` reconciler** (`agent/layer2/reconcile.py`): deterministic join by `classification_code` over
   the two `source_pipeline`-tagged sets; computes each `DeltaRow`; `zero_delta = (delta_count == 0)`.
   No LLM — this *is* the zero-delta compliance analysis.

6. **Layer 3 Trusted-Data gate** (`agent/layer2/trusted_data.py`): `promote_to_trusted(report)` writes the
   reconciled itemization into the Trusted-Data store **iff** `zero_delta`, else returns `GateBlocked(report)`.
   (PoC Trusted-Data store = a dedicated ChromaDB collection / SQLite table, reusing existing infra.)

7. **Storage** — pipeline outputs written to ChromaDB tagged by `source_pipeline` (per the doc), reusing
   `agent/chromadb_sync.py` patterns; `Agent 4a` reads both tags and diffs.

8. **Surface** (`app2.py`): `POST /api/reconcile` runs fixtures → P2 + P3 → `Agent 4a` → gate and returns
   the DeltaReport (+ gate outcome), matching the existing Flask route/limiter/error pattern.

### 3.3 Module layout (in SyntecAgent)

```
agent/layer2/
  __init__.py
  models.py            # LineItem, LineItemization, DeltaRow, DeltaReport
  classify.py          # Agent-1 adapter over agent/ccn
  pipelines/
    pdf_pipeline.py    # Agent 2 (GPT-4o extract + anchor)
    foundation_pipeline.py  # Agent 3 (deterministic)
  reconcile.py         # Agent 4a
  trusted_data.py      # Layer 3 gate + Trusted-Data store
  fixtures/            # synthetic sources + golden report
app2.py                # + POST /api/reconcile
tests/
  test_layer2_reconcile.py
  test_layer2_pipelines.py
  test_layer2_gate.py
  test_layer2_end_to_end.py
```

## 4. Data Flow

```
sourceA.pdf   ─→ P2 (Agent 2): GPT-4o extract + anchor + classify ─→ items[source=pdf] ┐
                                                                                        ├→ Agent 4a reconcile → DeltaReport → Layer 3 gate
sourceB.json  ─→ P3 (Agent 3): map + classify ────────────────────→ items[source=foundation] ┘   promote iff zero_delta
                                        (both tagged by source_pipeline in ChromaDB)
```

**Demo arc:** run `delta` variant → `delta_count > 0` → gate **blocks**, returns the DeltaReport naming the
discrepancy → correct the source (swap to `corrected`, or an `Agent 5a` tuning flag) → re-run →
`zero_delta = true` → gate **opens**, itemization promoted to Trusted Data.

## 5. Error Handling (honesty guards)

- **Anti-hallucination:** every P2 item must anchor to PDF text; unanchored items are dropped and never counted.
- **Unclassifiable:** an item the CCN vocabulary cannot code is emitted with `status = unclassifiable`, not silently dropped — surfaces the Agent-1 dependency honestly.
- **Reconciler keys on the code**, not fuzzy description matching; units normalized before compare.
- **Determinism:** `Agent 4a`, P3, `classify`, and the gate are deterministic and unit-testable; only P2's extraction is LLM-backed and is constrained by the anchor.

## 6. Testing (TDD — mandatory)

Tests first (RED) → minimal impl (GREEN) → refactor. Repo already uses `pytest` (`tests/test_ccn_*`).

- **Unit — `reconcile.py`:** truth table — `zero_delta` true *iff* all codes match; each mismatch type; `unclassifiable` handling.
- **Unit — pipelines:** P3 row→LineItem mapping + classification; P2 classification + that an unanchored item is excluded (mock the LLM).
- **Unit — `trusted_data.py`:** promotes iff `zero_delta`; else `GateBlocked` with report.
- **Integration — `test_layer2_end_to_end.py`:** run both pipelines on `delta` fixtures → DeltaReport contains **exactly** the one planted discrepancy and matches golden `expected_delta_report.json`; `corrected` fixtures → `zero_delta` true + gate opens. Mock the P2 LLM for determinism.
- **Golden fixtures** committed.

## 7. Reuse & Seams

- **Agent 1** (`agent/ccn`) supplies the canonical code set — the real join key.
- **Existing SyntecAgent infra**: Flask app + routing/limiter, ChromaDB (`chromadb_sync.py`), SQLite, GPT-4o client.
- **Veritas** is a *pattern* only: the quote-anchor discipline for P2's PDF extraction. No code dependency.
- Each pipeline reads its source through a small loader interface, so synthetic sources swap for real drawings PDF + real CCN workbook / BIM export later without touching the reconciler, gate, or models.

## 8. Definition of Done

- `agent/layer2/` + tests exist on `feat/poc-layer2-zero-delta`, tests green locally, **not merged**.
- `POST /api/reconcile` on the `delta` fixtures returns a DeltaReport naming the planted discrepancy and the gate blocks; on `corrected` fixtures returns `zero_delta` and the gate promotes.
- A short `agent/layer2/README.md` explains the demo arc and how to run it.
- The worker reports branch + SHA + a 5-line summary to god; god integrates/QA and demos to the user.

## 9. Consistency With the BUSA V2.01 Doc

- Matches the doc's declared PoC scope (Phase 3: Agents 2, 3, 4a) and stack (Flask + ChromaDB, `source_pipeline`-tagged).
- **Known deliberate divergences:** (a) **two** pipelines vs the doc's canonical **three** (Notes-DB path is the fast-follow); (b) code-first vs the doc's Cowork-first prototyping; (c) the PoC consumes Agent 1's parsed vocabulary directly rather than the doc's future `/classify` endpoint. None block the thesis; all are on the documented upgrade path.
