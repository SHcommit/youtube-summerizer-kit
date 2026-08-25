# Bounded Frontier Synthesis Design

## Goal

Use one Frontier generation call whenever a prepared transcript fits the selected runtime's configured input budget, while retaining the existing local transcript, evidence-validation, persistence, export, and resume boundaries.

## Decision

Each runtime/model profile declares a static usable input budget. The pipeline estimates prepared transcript tokens locally and selects one of two immutable strategies:

- `one_shot_v1` when the complete transcript plus schema/output reserve fits.
- `two_pass_refine_v1` only when the full transcript does not fit but a left-half result plus the right-half raw transcript fits.

Video duration alone never selects a strategy. The strategy, runtime/model budget, and token estimate are included in the request/cache identity and run metadata. No automatic third or later semantic call is permitted.

## One-Shot Flow

```text
public or user-provided transcript
-> local normalization / optional deterministic preprocessing / segmentation
-> one `frontier_summary` request over the prepared transcript
-> local candidate-evidence validation against immutable raw spans
-> local one-topic / one-chapter Knowledge Pack construction
-> existing output compiler and artifact persistence
```

The response schema contains overview, chapters/topics, claim candidates, concepts, examples, and further-study items. Local code materializes raw-evidence references and constructs the Knowledge Pack without an additional semantic compose call.

## Two-Pass Refine Flow

```text
left raw transcript -> `frontier_summary` -> validated left result
validated left result + right raw transcript -> `frontier_refine` -> final result
local assembly retains left evidence refs and validates right evidence against raw spans
```

This is an explicit maximum, not a fan-out. If the transcript does not fit either one-shot or two-pass refine for the selected runtime/model, the run stops before any Frontier call with a message to choose a larger-context runtime or explicitly approve a future high-cost mode.

## Boundaries

- Frontier remains the sole semantic reasoning runtime, with at most two calls per analysis.
- Local code performs only deterministic preprocessing, validation, structural assembly, persistence, and export.
- `task_runtimes` cannot route `short_video_summary` to a local runtime because the existing Frontier-first execution plan rejects local summary routes.
- Existing topic -> chapter -> compose fan-out is retired from the default analysis path.
- A failed one-shot or refine request produces no Knowledge Pack and remains resumable through the existing scheduler state machine.

## Data and Observability

- Persist one or two durable jobs, with task names `frontier_summary` and `frontier_refine`.
- Keep standard generation measurement and add the existing validator measurement when claims include evidence candidates.
- Record strategy, static runtime budget, and local token estimate in cache/run metadata and telemetry attributes.
- Construct a normal `KnowledgePack` with validated evidence refs, model/runtime provenance, and further-study items.

## Verification

- A fitting transcript creates one Frontier request and no topic/chapter/compose calls.
- An over-budget transcript creates at most two Frontier requests, with no fan-out.
- An input that cannot fit the two-pass refine budget fails before a provider call.
- Invalid evidence candidates are excluded on the single path.
- Cache identities differ between the two strategies.
- Existing output compilation works from the single-path Knowledge Pack.
- Update README, Korean README, agent index, CHANGELOG, IMPROVEMENTS, and handoff.
