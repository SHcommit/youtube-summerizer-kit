# Bounded Frontier Synthesis With Optional Local Input Cleanup

> Superseded by [`2026-08-25-grounded-knowledge-tree-hybrid-design.md`](2026-08-25-grounded-knowledge-tree-hybrid-design.md), which retains this call budget and adds the approved GKT, rendering, persistence, and optional LangGraph agent boundaries.

## Goal

Use one Frontier generation call whenever a prepared transcript fits the selected runtime's configured input budget, while retaining the existing local transcript, evidence-validation, persistence, export, and resume boundaries. An already-installed single Ollama model may improve input cleanup, but it never summarizes, judges evidence, or adds another Frontier call.

## Decision

Each runtime/model profile declares a static usable input budget. The pipeline estimates prepared transcript tokens locally and selects one of two immutable strategies:

- `one_shot_v1` when the complete transcript plus schema/output reserve fits.
- `two_pass_refine_v1` only when the full transcript does not fit but a left-half result plus the right-half raw transcript fits.

Video duration alone never selects a strategy. The strategy, runtime/model budget, and token estimate are included in the request/cache identity and run metadata. No automatic third or later semantic call is permitted.

## One-Shot Flow

```text
public or user-provided transcript
-> immutable raw transcript spans
-> deterministic normalization and cleanup
-> optional single-model Ollama annotation sidecar
-> one locally materialized prepared transcript
-> one `frontier_summary` request over the prepared transcript
-> local candidate-evidence validation against immutable raw spans
-> deterministic Knowledge Pack construction
-> deterministic output rendering and artifact persistence
```

The response schema contains overview, chapters/topics, claim candidates, concepts, examples, and further-study items. Local code materializes raw-evidence references and constructs the Knowledge Pack without an additional semantic compose call.

## Optional Local Cleanup Contract

Local cleanup has three modes: `auto`, `on`, and `off`, with `auto` as the default. `auto` uses Ollama only when its loopback service and the configured single model are already available. `on` treats unavailability as an explicit configuration error. `off` always uses deterministic cleanup. No mode installs Ollama or downloads a model during analysis.

Ollama returns a compact annotation sidecar rather than a rewritten transcript. The schema is limited to raw span identifiers, boundary hints, repetition or filler candidates, low-confidence ranges, confidence values, and short reason codes. It cannot return replacement words, summaries, chapters, claims, or final prose. Raw text and timestamps remain immutable; local code may only omit validated filler/repetition spans or insert structural separators. It sends exactly one prepared transcript to Frontier, so raw and prepared copies are never both included in the prompt.

Before a Frontier request, the pipeline estimates tokens for both the deterministic baseline and the locally assisted candidate. If the assisted candidate exceeds the baseline by more than 5%, violates the annotation schema, changes protected content, or times out, it is discarded and the deterministic baseline is used immediately. This fallback does not trigger a model download, a local retry loop, or an additional Frontier call.

## Two-Pass Refine Flow

```text
left raw transcript -> `frontier_summary` -> validated left result
validated left result + right raw transcript -> `frontier_refine` -> final result
local assembly retains left evidence refs and validates right evidence against raw spans
```

This is an explicit maximum, not a fan-out. If the transcript does not fit either one-shot or two-pass refine for the selected runtime/model, the run stops before any Frontier call with a message to choose a larger-context runtime or explicitly approve a future high-cost mode.

## Boundaries

- Frontier remains the sole semantic reasoning and summary runtime, with at most two calls per analysis.
- The optional single local model only proposes bounded input-cleanup annotations. Local code validates and applies them deterministically.
- `task_runtimes` cannot route `frontier_summary` or `frontier_refine` to a local runtime because the Frontier-first execution plan rejects local summary routes.
- Existing topic -> chapter -> compose fan-out is retired from the default analysis path.
- Default digest, blog, study, and Obsidian rendering does not make outline, compose, or verify model calls after the Knowledge Pack exists.
- A failed one-shot or refine request produces no Knowledge Pack and remains resumable through the existing scheduler state machine.

## Data and Observability

- Persist one or two durable jobs, with task names `frontier_summary` and `frontier_refine`.
- Keep standard generation measurement and add the existing validator measurement when claims include evidence candidates.
- Record strategy, static runtime budget, and local token estimate in cache/run metadata and telemetry attributes.
- Record cleanup mode, deterministic preprocessing version, optional local model identity, sidecar fingerprint, acceptance or fallback reason, and before/after token estimates.
- Construct a normal `KnowledgePack` with validated evidence refs, model/runtime provenance, and further-study items.

## Verification

- A fitting transcript creates one Frontier request and no topic/chapter/compose calls.
- An over-budget transcript creates at most two Frontier requests, with no fan-out.
- An input that cannot fit the two-pass refine budget fails before a provider call.
- Ollama absence, timeout, invalid annotations, or token growth falls back to deterministic cleanup without a Frontier call increase.
- The Frontier prompt contains one prepared transcript, never both raw and prepared copies.
- Assisted cleanup cannot increase the prepared transcript token estimate by more than 5% over the deterministic baseline.
- Invalid evidence candidates are excluded on the single path.
- Cache identities differ between the two strategies.
- Every default output profile compiles from the Knowledge Pack without further model calls.
- Update README, Korean README, agent index, CHANGELOG, IMPROVEMENTS, and handoff.
