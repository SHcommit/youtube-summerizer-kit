# Grounded Knowledge Tree Compiler and Agent Orchestration Design

## Status

Approved product direction. This document supersedes the narrower bounded-Frontier design and is the implementation contract to review before writing the execution plan.

## Goal

Replace topic/chapter/compose Frontier fan-out with a checkpointed knowledge-compilation workflow that normally uses one Frontier generation. Produce a reusable, evidence-grounded `GroundedKnowledgeTree` (GKT), then render every default output locally. Add LangGraph only as an optional orchestration layer for future Research, Style, Conversation, and Publishing agents.

## Architecture Decision

The product has two planes with a one-way dependency:

```text
Agent Orchestration Plane (optional `agents` extra)
  LangGraph session graph and bounded agent subgraphs
  -> calls typed Application Service tools

Knowledge Compilation Plane (core)
  transcript -> prepared input -> KnowledgeTreeDraft
  -> deterministic grounding -> GroundedKnowledgeTree
  -> KnowledgePack compatibility projection -> local renderers
```

The GKT compiler does not import LangGraph. Agents consume a completed GKT through application ports and cannot mutate raw transcript evidence or the compiler's immutable execution policy.

## Model Call Contract

| Workflow | Ollama calls | Frontier calls |
|---|---:|---:|
| Default, Ollama unavailable or disabled | 0 | 1 |
| Default, Ollama cleanup available | at most 1 | 1 |
| Explicit custom local style | at most 2 total: cleanup + style | 1 |
| Input exceeds the configured Frontier budget | 0-1 | at most 2 |

The optional Ollama calls use one configured model. The compiler never installs Ollama or downloads a model. Default digest, study, blog, JSON, and Obsidian rendering makes no model call. A future agent run has a separate, visible budget and cannot consume the compiler's Frontier allowance.

## Core Types

`KnowledgeTreeDraft` is untrusted Frontier output. `GroundedKnowledgeTree` contains only locally resolved source references. `KnowledgePack` remains the persisted compatibility envelope during migration.

```text
GroundedKnowledgeTree
├── thesis_claim_id
├── summary_claim_ids[]
├── concepts[]
│   ├── concept_id, title, definition
│   ├── claim_ids[]
│   └── occurrence_ids[]
├── claims[]
│   ├── claim_id, text, provenance
│   └── evidence_refs[]
├── occurrences[]
│   ├── occurrence_id, raw_segment_ids[]
│   ├── quote, start_ms, end_ms
│   └── context_type
├── timeline_sections[]
│   ├── section_id, title
│   ├── claim_ids[]
│   └── anchor_occurrence_ids[]
├── relations[]
└── diagnostics
```

Timeline and renderer views reference canonical nodes by ID rather than duplicating prose. The local compatibility projector derives current topics, chapters, claims, and evidence refs so existing CLI outputs and integrations can migrate incrementally.

## Stage 1: Deterministic Input Compiler

Raw transcript text, timestamps, and fingerprint remain immutable. The compiler creates `PreparedTranscript` and a reversible mapping to stable raw segment IDs.

In a fixed, versioned order it validates and sorts ranges, removes overlapping automatic-caption prefix/suffix duplication, separates allowlisted non-speech markers, removes standalone fillers, normalizes whitespace and Unicode, groups short segments into bounded paragraphs, and estimates prompt plus schema plus output-reserve tokens. It does not delete spans containing protected numbers, units, negation, proper-name candidates, or code-like content.

Every prepared paragraph carries its raw segment IDs. The raw and prepared transcript are stored as separate content-addressed artifacts, but only the prepared representation is sent to Frontier.

## Stage 2: Optional Local Annotation

The deterministic compiler first identifies uncertain filler, repetition, noise, and boundary candidates. It sends one bounded candidate batch to the configured Ollama model. Candidate overflow remains deterministic rather than causing more local calls.

The structured sidecar permits only `DROP_FILLER`, `DROP_DUPLICATE`, `MARK_BOUNDARY`, and `MARK_LOW_CONFIDENCE`, with raw segment IDs, confidence, and a reason code. It cannot return replacement words, summaries, claims, chapters, or prose.

Unknown IDs, protected-span changes, schema errors, timeout, policy-limit violations, excessive deletion, or more than 5% token growth reject the whole assisted candidate and immediately restore the deterministic baseline. No repair call or local retry loop is allowed.

## Stage 3: Frontier Extraction

The Frontier request receives one prepared transcript with stable segment IDs, the analysis intent, and a strict `KnowledgeTreeDraft` schema. It returns thesis and summary claims, concepts, claims and counterpoints, occurrences, timeline references, relations, and further-study candidates in one generation.

An `AnalysisSpec` changes semantic focus and participates in the analysis fingerprint. A `RenderSpec` changes presentation only and cannot trigger a new analysis. If the configured static runtime/model budget cannot fit one generation, the previously approved two-pass refine is the only fallback; there is no third semantic call or topic/chapter fan-out.

Provider-native structured output is required. Local syntax normalization may recover a parseable response, but invalid semantics or schema do not trigger an automatic Frontier repair call. An outcome that may have reached the provider is recorded for explicit user-approved resume rather than silently duplicated.

## Stage 4: Deterministic Grounding

The grounder validates raw segment IDs first, then verifies that normalized anchor text occurs within the referenced raw segment neighborhood. It derives timestamps from the first and last accepted raw segments. Fuzzy matching may locate a recovery candidate, but cannot establish trust by itself; ambiguous or non-unique matches are rejected.

Grounding guarantees source-location binding, not factual truth or entailment. Unsupported source claims are excluded from trusted output and recorded in diagnostics. AI explanation and future external research retain separate provenance.

## Stage 5: Tree Assembly and Compatibility

`TreeAssembler` removes dangling references, aggregates occurrences under canonical concepts, sorts timeline sections by grounded source time, merges only deterministically identical claim/evidence pairs, computes completion and coverage diagnostics, and fingerprints the result. It does not use a model for semantic deduplication.

A versioned `KnowledgePackProjector` derives the legacy topic/chapter representation during migration. Cache identity includes raw and prepared fingerprints, compiler and schema versions, analysis intent, runtime/model profile, call strategy, optional local model identity, and accepted sidecar fingerprint.

## Stage 6: Rendering and Skills

Typed renderer ports produce digest, study, blog, JSON, and Obsidian output directly from GKT. Default renderers are deterministic Python components; a template engine is not required by the domain.

External instructions are normalized into separate inputs:

- `AnalysisSpec`: focus, audience, depth, and semantic exclusions. It is included in the single Frontier call.
- `RenderSpec`: output profile, preset tone, layout, language, and installed render skill. It reuses the existing GKT.

Installed `RenderSkill` manifests declare ID, version, required fields, execution kind, side effects, and call budget. Deterministic skills make no model call. An explicitly requested arbitrary prose style may use one additional local Ollama style call over grounded claim IDs and citation placeholders, followed by reference validation. Skills cannot invoke Frontier, access credentials, delete files, or perform external writes unless a separate policy explicitly grants that capability.

## Harness and Role Ports

Harness remains the vendor execution adapter: availability, authentication, structured generation, timeout, cancellation, usage, model identity, and error normalization. It is not an agent and does not choose workflow transitions.

Core code depends on role-specific ports rather than task strings or vendor IDs:

```text
KnowledgeExtractor  -> Frontier harness adapter
TranscriptAnnotator -> Ollama harness adapter
StyleRenderer       -> optional Ollama harness adapter
```

Policy maps a role to an allowlisted harness capability and immutable budget. A local runtime cannot perform knowledge extraction, and a Frontier runtime cannot be selected for default rendering.

## Durable Workflow and Session State

The compilation state machine is `created -> acquiring -> compiling -> local_optimizing -> ready_for_frontier -> frontier_running -> grounding -> assembling -> rendering -> completed`. Each completed stage stores an immutable artifact and measurement before the next transition.

`Session` stores user messages, normalized intent, parent session node, preferred render settings, and linked run IDs. `CompilationRun` stores compiler state and immutable execution policy. `AgentRun` stores agent graph state and tool results. Session state may select a new run but cannot mutate a running compiler plan.

Pause is cooperative at stage boundaries. A running external request is cancelled only through its adapter; if provider acceptance is uncertain the state becomes `external_outcome_unknown`. Resume starts after the latest validated checkpoint. Explicit retry creates a recorded new attempt rather than overwriting history.

## Optional LangGraph Agent Plane

LangGraph is installed only through an `agents` optional extra. The top-level `SessionGraph` interprets an already-normalized request, invokes the GKT compiler through a typed application tool, then conditionally dispatches bounded Research, Style, Conversation, or Publishing subgraphs.

Research, Style, and Publishing default to per-invocation state. Conversation may use per-thread memory. LangGraph `thread_id` maps to Chew `session_id`; graph checkpoints live separately from the canonical Chew database and reference `run_id`, `tree_id`, and artifact digests.

Agents do not access the database, artifact paths, shell, browser sessions, cookies, or Keychain directly. They receive allowlisted typed tools such as `read_tree`, `search_evidence`, `render_tree`, `add_external_research`, `preview_publish`, and `publish_approved`. External writes require an interrupt and explicit approval. Recursive agent dispatch is disabled initially.

The initial orchestration pattern is supervisor-controlled bounded dispatch, not peer-to-peer agent conversation. Independent read-only research tasks may run in parallel under a fixed DAG. Each agent declares maximum steps, model calls, deadline, readable/writable artifacts, tools, and approval requirements before execution.

## Policy Contract

The policy compiler must express role allowlists, one-shot and two-pass Frontier budgets, one local cleanup call, explicit-only local style, zero automatic schema repair calls, bounded rejected-rate-limit attempts, unknown-outcome handling, agent tool scopes, agent step/model/time limits, recursive-dispatch denial, and external-write approval.

LangGraph manages graph state and interrupts; it does not own cost, credential, evidence, retry, or provenance policy. Harnesses consume policy decisions but cannot expand them.

## Persistence, Trace, and Benchmark Compatibility

The current SQLite run/job/measurement database and content-addressed artifact store remain canonical for compiler work. LangGraph uses a separate checkpointer so graph checkpoint schema does not leak into domain storage. The integration records durable correlation IDs between session, compilation run, agent run, and traces.

OpenTelemetry spans become `workflow.run`, `transcript.acquire`, `input.compile`, `local.optimize`, `frontier.generate`, `evidence.ground`, `tree.assemble`, `output.render`, and optional `agent.*` spans. Attributes contain fingerprints, counts, budgets, call strategy, fallback reasons, and provenance, never transcript or credential content. A resumed process creates linked spans rather than pretending that an in-memory parent span survived.

Existing locked benchmark URLs, human references, baseline reports, and renderers remain unchanged. New conditions compare legacy hierarchical, GKT deterministic, and GKT Ollama-assisted paths. Metrics include provider usage, successful and rejected attempts, stage latency, grounding coverage, timestamp binding, ambiguous anchors, unsupported claims, duplicate candidates, GKT coverage, output fidelity, memory, and pause/resume correctness. End-to-end Frontier runs remain the final pre-release gate.

## Implementation Order

1. Add versioned GKT draft/trusted models, compatibility projector, and pure grounding/assembly tests.
2. Add deterministic prepared-transcript artifacts and token-budget profiles.
3. Add bounded optional Ollama annotation behind a role port and policy.
4. Replace the default semantic DAG with one-shot/two-pass GKT extraction while retaining the legacy path behind a benchmark-only strategy.
5. Replace default model-backed output composition with deterministic GKT renderers and render-skill contracts.
6. Add durable compiler stage checkpoints, pause/resume states, and the revised trace vocabulary.
7. Add LangGraph as an optional extra with a minimal SessionGraph and one bounded agent subgraph before expanding to additional agents.
8. Repair benchmark reference comparability and run the integrated pre-release benchmark only after behavior and policy are complete.

## Acceptance Gates

- A normal compilation makes exactly one successful Frontier generation and no output-profile Frontier calls.
- Ollama absence or failure does not change the Frontier call count or prevent compilation.
- An over-budget compilation makes at most two successful Frontier generations and never fans out by topic or chapter.
- Every trusted source occurrence resolves to immutable raw segment IDs and locally derived timestamps.
- All default profiles render from one GKT without a model call.
- Pause/resume never silently duplicates an uncertain provider request or external write.
- Agent runs cannot alter raw evidence, compiler policy, or trusted source provenance.
- Legacy benchmarks remain runnable, and the new paths report separately comparable measurements.

## Explicit Non-Goals

- No vector database, embeddings, or general Knowledge Graph database in the default compilation path.
- No full-transcript Ollama rewrite and no three-model layered Ollama pipeline.
- No unrestricted autonomous loops, recursive agent dispatch, silent model downloads, credential-store access, or browser-session recovery.
- No claim of factual truth, zero semantic duplication, or perfect source-caption timing from lexical grounding alone.
