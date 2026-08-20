# Handoff Index

`IMPROVEMENTS.md` is the single source of truth for roadmap requirements,
acceptance gates, fixture definitions, and implementation order. This document
is only a short index for the currently active work.

## Active Order

1. Phase 1 Spike: use the locked-fixture reports to decide whether each
   preprocessing strategy can leave opt-in status.
2. Phase 1 / F1: retain raw transcript evidence and record per-request Ollama
   usage, duration, repair, and cache information.
3. Phase 1 / F2: compare opt-in token-budget segmentation and safe transcript
   preprocessing against that baseline.
4. Phase 1 / F3-F4: measure repair routing and optional output verification;
   do not promote either without the Phase 1 acceptance gate.
5. Additional D-E: keep partial results, cache provenance, and quality gates
   correct before changing defaults.

## Current State

- `reports/token-baseline.md` and `reports/token-comparison.md` now exist for
  the locked five-video English set. Conservative filler removal saved only
  1.92%–4.94% by `cl100k_base`, below the 10% adoption gate; it stays opt-in.
- Phase 1 code support now includes raw/processed artifact separation,
  composable local preprocessing, optional punctuation/semantic stages,
  token-budget segmentation, partial-result signaling, and opt-in output
  verification.
- The locked 39-minute and 55-minute Ollama fixtures still need live baseline,
  repair-rate, and quality-reference comparison runs before model-routing or
  preprocessing defaults change.
- F1 measurement records now include provider usage/duration plus request
  structure (`input_chars`, segment count, schema size, repair and retry flags)
  in SQLite schema v6. `scripts/report_job_measurements.py` renders a read-only
  per-run report. Next is live Ollama fixture collection.
- Knowledge Graph is explicitly on hold. Notion, public APIs, MCP, automation,
  content-source expansion (news/RSS/PDF/VAD), and visual analysis are not
  active work.

## Product Decisions

- Local LLM/Ollama is an optional user choice. See
  `docs/decisions/local-llm-runtime.md`.
- Keep the existing BYOK and harness architecture defined in
  `IMPROVEMENTS.md`; do not introduce a new routing architecture unless that
  document is updated and approved first.
