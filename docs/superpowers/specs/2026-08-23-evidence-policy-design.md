# Evidence Integrity and Execution Policy Design

**Status:** Approved for implementation

## Goal

Keep Frontier as the final reasoning and writing runtime while making source claims traceable to immutable transcript spans and making runtime execution decisions reproducible.

## Scope

The first release adds `EvidenceCandidate`, `ValidatedEvidenceRef`, a deterministic span validator, and a rules-based `ExecutionPlan`. It does not add embeddings, RAG, vector storage, Knowledge Graph, LangGraph, or an Ollama final-summary path.

## Evidence Boundary

`RawTranscript` is the immutable source of truth. A topic model may return an `EvidenceCandidate` containing segment indexes, a timestamp range, and a short quote. The validator alone turns it into a `ValidatedEvidenceRef` after confirming that the referenced raw segments, timestamps, quote, and raw artifact fingerprint agree.

Validation does not establish that a claim is true. It establishes only that a model-proposed citation is anchored in the source transcript. Invalid candidates are retained as validation metadata but are excluded from user-visible citations and do not fail the complete run.

## Execution Policy Boundary

The application layer creates an immutable `ExecutionPlan` before analysis. The plan records a policy version, chosen route, task limits, fallback route, and reason. Pipeline code consumes the plan; a harness executes only the request it receives. Model output cannot modify an execution plan.

Policy v1 always selects the configured Frontier runtime. It records an unavailable local accelerator as a reason but never calls Ollama or changes the route. This establishes the contract without changing output quality or cost. Future local experiments must be explicit opt-in policies and pass the benchmark criteria in `IMPROVEMENTS.md`.

## Persistence and Observability

The run record stores an immutable JSON policy snapshot. Generation measurements include the plan fingerprint and evidence validation totals, without storing credentials or prompt contents. The canonical Knowledge Pack stores validated evidence references so all output formats can reuse them.

## Failure Handling

- Candidate parse failure: existing repair path handles invalid topic output.
- Candidate span validation failure: mark only that candidate invalid and continue.
- Missing or unhealthy local runtime: record the condition and use the configured Frontier runtime.
- Invalid policy configuration: fail at settings validation before a run is created.

## Verification

Unit tests cover valid and invalid spans, raw fingerprint mismatch, deterministic policy decisions, and plan immutability. They do not make Frontier, Ollama, YouTube, or embedding calls. Real benchmark runs remain manual and only occur for performance-sensitive changes.
