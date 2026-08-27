# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Released: `v0.3.1` is tagged on `master` and the GitHub Release is live with a curated summary:
  https://github.com/SHcommit/youtube-summerizer-kit/releases/tag/v0.3.1
- `master` and `develop` are in sync.
- PyPI publish remains intentionally skipped — no `PYPI_API_TOKEN` secret is configured. GitHub
  Release download is the current distribution channel.
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md) — currently empty; the repository-governance
  P0/P1/P2 queue is complete or steady-state as of v0.3.1.
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work (including `intent-analysis` and `research-engine`/agent-runtime
  activation preconditions): [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decisions: [`interface and agent boundaries`](docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md), [`Grounded Knowledge Compiler modules`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)

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

No active release in flight and no open `IMPROVEMENTS.md` items. Before adding more product
surface, activating `intent-analysis` or `research-engine` requires one selected end-to-end user
flow and a versioned, typed, read-only `KnowledgeGateway` first — see the preconditions in
`PRODUCT_ROADMAP.md`. GitHub Projects are intentionally not used; execution tracking lives in
Linear plus repo-native Issues/PRs/labels/milestones.

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

- v0.3.1 released: no `src/chew` package/CLI behavior change this cycle — docs and CI tooling only.
- Latest full verification (v0.3.1, `release/v0.3.1`): `337 passed, 2 skipped`, Ruff clean, mypy
  clean (86 source files). No live provider or Frontier benchmark ran.
- This session's changes since v0.3.1 are documentation-only (`IMPROVEMENTS.md`,
  `PRODUCT_ROADMAP.md`, `handoff.md`, `docs/agent-index.md`); re-verify with
  `uv run python scripts/check_docs_sync.py` before merging.
