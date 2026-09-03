"""Layer 2 — zero-delta Verification Engine (PoC).

Two independent pipelines (Agent 2 / PDF, Agent 3 / Foundation table) derive
line itemizations from different synthetic sources; Agent 4a reconciles them
on the shared Agent-1 classification code; the Layer 3 Trusted-Data gate
promotes only on zero delta. See docs/specs/2026-09-03-layer2-zero-delta-poc-design.md.
"""
