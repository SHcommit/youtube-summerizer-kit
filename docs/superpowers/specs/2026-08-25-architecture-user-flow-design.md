# Architecture and README User-Flow Design

## Goal

Make the project understandable in three progressive views without exposing
every implementation detail:

1. what a user does and receives;
2. which external systems are connected at the product boundary; and
3. how the core pipeline turns validated source material into reusable output.

The English and Korean views must have the same nodes, edges, filenames, and
ordering. Only the visible language differs.

## Scope

Update the existing bilingual Mermaid source and rendered PNG assets, add one
bilingual external-boundary diagram, and rewrite the README architecture
section around the three views. The work documents the current behavior; it
does not introduce a new runtime, storage backend, telemetry product, or
benchmark workflow.

## Views

### 1. User flow

`user-flow.mmd` remains the first diagram. It shows the visible happy path and
the only meaningful recovery paths:

```text
YouTube URL / local media / supplied transcript
  -> public caption acquisition or supplied transcript validation
  -> prepare and analyze once
  -> saved Knowledge Pack
  -> Digest / Blog / Study / Obsidian

interrupted or authentication-required run -> status -> resume
existing compatible pack -> reassemble without analysis
```

It must not mention worker counts, speed multipliers, individual transcript
providers, prompt internals, or benchmark claims.

### 2. External boundaries

Add `external-boundaries.mmd` and `external-boundaries.png` in both language
directories. Place `chew` as a single application boundary and draw only these
meaningful adapters around it:

- CLI user and local input files;
- public YouTube captions and optional local Whisper transcription;
- Frontier runtimes (Codex, Gemini, Claude) for reasoning;
- optional installed Ollama model for bounded transcript annotation only;
- SQLite state and content-addressed artifact storage; and
- an OpenTelemetry exporter / Jaeger as an optional observation destination.

The diagram makes it explicit that the application keeps source identity,
policy, grounding, Knowledge Pack assembly, and output rendering inside its
core. It must not depict a browser profile, cookie store, external vector DB,
or Frontier benchmarking.

### 3. Core pipeline

Refresh `internal-pipeline.mmd` as a compact internal data flow:

```text
identity + raw source -> transcript validation -> prepared transcript
-> grounded extraction -> local evidence grounding -> Knowledge Pack
-> deterministic output rendering
```

Show three cross-cutting modules as side bands, not repeated nodes:

- **Run control:** policy, immutable checkpoints, pause/resume, unknown
  external outcome handling;
- **State:** SQLite job state and content-addressed raw/derived artifacts; and
- **Observability:** structured logging, OpenTelemetry spans, and optional
  Jaeger export.

This is a logical map, not a claim that every node is a package. It should use
the real abstractions (`ApplicationService`, ports/adapters, Grounded Knowledge
Tree, Knowledge Pack) rather than the former topic/chapter fan-out or stale
performance figures.

## README Structure

Both README files will use the same section order:

1. short product promise and quick-start;
2. **How a run works** with the user-flow diagram, including cache reuse and
   resume in prose;
3. **Architecture at a glance** with the external-boundary diagram and a short
   statement of which external adapters are optional;
4. **Inside the pipeline** with the core-pipeline diagram and concise notes on
   grounding, durable state, logging, and tracing; and
5. links to the agent index for module-level details and the operational docs
   for configuration and troubleshooting.

The README should not reproduce the complete package tree, runtime setup table,
or benchmark history in these sections. Those remain in `docs/agent-index.md`,
`CHEW.md`, and maintainer reports.

## Error and Operations Language

Document only observable guarantees:

- public acquisition failure can be recovered with a user-supplied transcript;
- interrupted work retains durable completed checkpoints and can be inspected
  with `status` then continued with `resume` where allowed;
- authentication is an explicit user action; and
- structured logs and traces explain an execution but are not required to run
  a summary.

Avoid promising a particular runtime, latency, model quality, caption
availability, or automatic retry of an uncertain provider request.

## Verification

- Render all six Mermaid sources (three English and three Korean) to their
  matching PNG paths using the repository's established Mermaid renderer.
- Inspect each rendered PNG for labels, edge direction, and clipping.
- Confirm the README references only existing assets and no removed Frontier
  benchmark fixtures.
- Run `uv run --extra dev pytest`, `uv run --extra dev ruff check .`, and
  `uv run --extra dev mypy src/chew` because documentation names current
  product behavior and the project verification policy requires the full suite.

## Self-Review

- No placeholder, obsolete performance claim, or Frontier benchmark workflow
  appears in the planned diagrams or README structure.
- The three views have distinct audiences and do not duplicate each other.
- Logging, tracing, and durable run state are visible as cross-cutting concerns
  without turning the architecture diagram into a package inventory.
