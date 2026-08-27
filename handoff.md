# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Released: `v0.3.1` is tagged on `master` and the GitHub Release is live with a curated summary:
  https://github.com/SHcommit/youtube-summerizer-kit/releases/tag/v0.3.1
- Open PR: [#25](https://github.com/SHcommit/youtube-summerizer-kit/pull/25)
  `feat/engineering-knowledge` → `develop` (RunManifest v1, GKT docs truth pass, prompt bundle ID,
  benchmark provenance metadata — see `CHANGELOG.md` `[Unreleased]` for the full list). All
  required checks pass; not yet merged.
- PyPI publish remains intentionally skipped — no `PYPI_API_TOKEN` secret is configured. GitHub
  Release download is the current distribution channel.
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md) — currently empty.
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work (including `intent-analysis`/`research-engine` activation preconditions
  and `chew diagnostics export`): [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decisions: [`local LLM runtime`](docs/decisions/local-llm-runtime.md),
  [`repository governance`](docs/decisions/0002-repository-governance.md),
  [`RunManifest provenance`](docs/decisions/0003-run-manifest-provenance.md)

## Current Architecture Decision

- `core` is the domain; do not add a duplicate `domain` layer. `pipeline` remains the cohesive
  knowledge-compilation package and is not split pre-emptively.
- `app` is the product-use-case boundary. It is not an `examples` package.
- `pipeline.outputs` creates reusable product artifacts. `interfaces` presents operation results to
  CLI now and to future HTTP/MCP consumers later; it does not implement product rendering.
- `chew` is the Grounded Knowledge Compiler: it owns source acquisition, evidence validation, GKT
  synthesis, Knowledge Pack persistence, and deterministic output compilation.
- `modules/intent-analysis/` and `modules/research-engine/` are documentation-only, separately
  extractable boundaries. They are not Python packages or runtime dependencies.
- The `agents` package supplies dependency-free budget, grant, tool, and policy contracts only.
  There is no LangGraph runtime, MCP server, public HTTP API, authentication scheme, or web UI yet.
  A future web client consumes only a versioned HTTP contract and can live as a separately
  deployable `apps/web` project when that API exists.

## Next Decision

Merge PR #25 (or request changes) — all required checks pass. After that, no active release is in
flight and `IMPROVEMENTS.md` has no open items. GitHub Projects are intentionally not used;
execution tracking lives in Linear plus repo-native Issues/PRs/labels/milestones.

Before adding more product surface, activating `intent-analysis` or `research-engine` requires one
selected end-to-end user flow and a versioned, typed, read-only `KnowledgeGateway` from
`research-engine` to `chew` — see the preconditions in `PRODUCT_ROADMAP.md`. Do not add
ApplicationService agent tools, LangGraph, MCP, HTTP endpoints, web UI code, model dependencies, or
a public package automatically.

Transcript preprocessing remains opt-in; its reviewed seven-fixture metrics-only conclusion is in
`reports/performance-comparisons/transcript-preprocessing/latest.md`.

## Active Constraints

- Do not run, retain, or interpret end-to-end Frontier benchmark comparisons. `--live` remains only
  as an explicit backward-compatible diagnostic.
- Frontier remains responsible for final reasoning; Ollama is an optional, already-installed,
  bounded transcript-annotation helper only.
- Agents never receive direct DB, artifact-path, shell, browser-session, cookie, Keychain, or vendor
  credential access. External writes require explicit approval.
- `reports/performance-comparisons/transcript-preprocessing/baseline-20260825T052411Z/` and
  `reports/performance-comparisons/transcript-preprocessing/current-20260825T052533Z/` are known
  untracked metrics artifacts. Review them separately before staging.

## Verification and Working Tree

- `feat/engineering-knowledge` (PR #25, commit `d4f60dd`): `351 passed, 2 skipped`, Ruff clean,
  mypy clean (87 source files), plus `scripts/check_architecture.py`,
  `scripts/check_docs_sync.py`, and `scripts/check_release_consistency.py` all passing. No live
  provider or Frontier benchmark ran.
