# Current System State

This page is the single source of truth for "what actually runs today" versus what is kept for
comparison or is only designed. When this page disagrees with another document, this page wins;
fix the other document instead of reverting this one. It is auto-synced from
`docs/wiki/Current-System.md` in the main repository.

## Status Legend

| Status | Meaning |
|---|---|
| **Default** | The current runtime analysis path for a normal user request. |
| **Compatibility** | Exists in code for comparison, benchmarking, or legacy Pack support. Not the live user-facing path. |
| **Deferred** | Designed or documented only. No runtime, no adapter, not wired into any command. |

## Pipeline Strategy

| Status | Target | Notes |
|---|---|---|
| **Default** | GKT compiler (`pipeline/engine.py: AnalysisPipeline.analyze()`) | `Input Compile → Frontier Generate → Evidence Ground → Tree Assemble → Knowledge Pack → Deterministic Output Rendering`. `app/service.py` hardcodes `compiler_strategy="gkt"` — there is currently no other live strategy. See [`Feature-Flow.md`](Feature-Flow.md) for the full stage diagram. |
| **Compatibility** | Hierarchical topic → chapter → compose flow | Lives only as the `hierarchical()` comparison condition in `src/chew/benchmark/runner.py`, alongside `single_pass()` and `gkt_deterministic()`. Not reachable from any CLI command or `ApplicationService` path. |
| **Deferred** | MCP server, LangGraph agent runtime, RAG / vector DB, public HTTP/web API | Designed in `docs/decisions/`, `modules/*/README.md`, and `PRODUCT_ROADMAP.md` only. No package, no runtime, no adapter under `agents/adapters/`. |

## Why This Page Exists

An earlier audit found that `AGENTS.md` (the project's architecture single source of truth,
symlinked as `CLAUDE.md` / `GEMINI.md`) still listed `src/chew/pipeline/` as five files
(`segmentation.py`, `scheduler.py`, `engine.py`, `knowledge.py`, `outputs.py`) after
`input_compiler.py`, `extraction.py`, `evidence.py`, `tree.py`, `annotation.py`, `policy.py`, and
`preprocessing.py` had already been added and wired into the only live execution path. At the same
time, `docs/wiki/Feature-Flow.md` described the pipeline's fourth stage as
`topic jobs → chapter jobs → Knowledge Pack job`, omitting the Input Compile and Evidence Ground
stages entirely. Both were corrected against a direct read of `pipeline/engine.py` and
`app/service.py`, not against each other.

## Keeping This Page in Sync

Update this page, `AGENTS.md`'s pipeline layer listing, `docs/wiki/Feature-Flow.md`, and
`reports/BENCHMARK.md` together whenever:

- the default `compiler_strategy` changes,
- a pipeline module is added, removed, or renamed under `src/chew/pipeline/`,
- a benchmark comparison condition is added or removed in `src/chew/benchmark/runner.py`, or
- an item moves from Deferred to an active adapter under `agents/adapters/`, `interfaces/`, or a
  new optional extras group.

This page ships to the GitHub Wiki automatically on push to `develop`/`master` via
`.github/workflows/wiki-sync.yml` — no separate wiki edit is needed.

*Last verified against source: 2026-08-27.*
