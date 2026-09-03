# Layer 2 — Zero-Delta Reconciliation PoC

Proves that two independently-sourced line-item lists for the same
BuildUSA project — a PDF drawings/specs extraction (Agent 2, "P2") and a
Foundation JSON export (Agent 3, "P3") — can be deterministically joined
on `classification_code` and diffed, so a mismatch is *surfaced*
(`quantity_mismatch`, `unit_mismatch`, `mixed_units`, `missing_in_A/B`,
`unclassifiable`) rather than silently blended or dropped. Only a report
with zero deltas and at least one matched code is allowed to promote to
the Layer 3 trusted-data store (`agent/layer2/trusted_data.py`) — the
gate fails closed.

## Demo arc

1. **Block** — run the `delta` fixtures: one planted quantity mismatch
   (`C1010`) trips the gate. `gate: "BLOCKED"`.
2. **Correct** — swap in the `corrected` fixtures: the discrepancy is
   fixed at the source.
3. **Zero-delta** — reconciling the corrected pair yields no deltas.
4. **Promote** — the gate opens and the report is written to trusted
   data. `gate: "PROMOTED"`.

Both fixture pairs live under `agent/layer2/fixtures/` and are selected
server-side by name only (see Fix 4 below) — never by a client-supplied
path.

## Running the tests

```bash
python3 -m pytest tests/test_layer2_*.py -q
```

The PDF-extraction LLM call is always mocked in tests (`llm_extract` /
`_default_llm_extract` patched) — no live OpenAI call, no network.

## Running the demo via the API

```bash
curl -X POST http://localhost:5000/api/reconcile \
  -H 'Content-Type: application/json' \
  -d '{"variant": "delta"}'
# -> {"gate": "BLOCKED", "delta_report": {... one quantity_mismatch on C1010 ...}}

curl -X POST http://localhost:5000/api/reconcile \
  -H 'Content-Type: application/json' \
  -d '{"variant": "corrected"}'
# -> {"gate": "PROMOTED", "delta_report": {... zero_delta: true ...}}
```

`variant` must be `"delta"` or `"corrected"` (default `"delta"`); any
other value is rejected with 400. There is no way to point the endpoint
at an arbitrary filesystem path.
