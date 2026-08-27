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

## Engineering System Audit Track (active on `feat/engineering-knowledge`)

An engineering-system audit (v2, superseding an earlier v1 draft) found the repository-governance
work below already covered most of Phase 1/3, and narrowed the real remaining gaps to four items.
Committed as `31918fd` on this branch:

1. **Done** — Documentation truth pass: `AGENTS.md`'s `pipeline/` layer listing, `README.md` /
   `README.ko.md`, `docs/wiki/Feature-Flow.md`, and `reports/BENCHMARK.md` no longer describe the
   legacy hierarchical topic/chapter flow as the default path. Added
   `docs/wiki/Current-System.md` (Default/Compatibility/Deferred table, auto-synced to the GitHub
   Wiki via `wiki-sync.yml`).
2. **Done** — `RunManifest` v1 (`pipeline/provenance.py`, `core/models.py`): a per-run
   code/prompt/schema/model provenance snapshot, linked from `KnowledgePack.manifest_hash` and
   `runs.manifest_hash` (schema v9). See [`ADR-003`](docs/decisions/0003-run-manifest-provenance.md).
3. **Done** — Prompt bundle logical ID: `chew.core.prompts.GKT_PROMPT_BUNDLE_ID` /
   `GKT_PROMPT_FINGERPRINT`, derived from the actual live-path prompt content
   (`harness/builtin.py: request_prompt()`'s instruction, moved to
   `core.prompts.HARNESS_JSON_INSTRUCTION`) rather than the legacy `PROMPT_FINGERPRINT`. Found and
   fixed in the same pass: `RunManifest.pack_schema` was fingerprinting `KnowledgePack` instead of
   `KnowledgeTreeDraft` (the schema actually enforced on Frontier output). See ADR-003's updated
   Decision section.
4. **Done** — `pipeline/provenance.py: benchmark_metadata()` adds `compiler_strategy`,
   `package_version`, `git_sha` (and `prompt_bundle` for `"gkt"`) to the `hierarchical` and
   `gkt-deterministic` conditions in `benchmark/runner.py`. `direct()`/`single_pass()` conditions
   call the harness directly (no `compiler_strategy` applies) and are intentionally left out.
5. **Done** — PR template gained an `ADR / Decision:` field and a
   behavior-preserving/behavior-changing/migration-required checklist for prompt bundle changes.
   Considered adding `risk:schema` / `risk:release` / `risk:provider` labels but decided against it:
   the existing label taxonomy (`impact:breaking`, `impact:security`, `area:release`,
   `area:harness`) already signals the same risk categories, and
   `docs/decisions/0002-repository-governance.md` itself warns against decorative labels. No
   `.github/labeler.yml` change needed.
6. **Deliberately skipped for now** — Re-measuring `reports/BENCHMARK.md`'s "미측정" rows
   (v0.2.0+ actual timing): the pipeline hasn't changed since GKT shipped in v0.2.0, so there is
   nothing new to measure yet. Revisit when `pipeline`/`scheduler` logic next changes.

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

Items 1-5 of the Engineering System Audit Track are done. Item 6 (diagnostics/incident tooling,
`chew diagnostics export`) remains explicitly deferred per the audit's own judgment — no active
user-reported incident motivates it yet. Recorded in `PRODUCT_ROADMAP.md` (not `README.md`, which
only documents shipped behavior) so the idea and its precondition aren't lost. No active release is
in flight and `IMPROVEMENTS.md` has no open items. GitHub Projects are intentionally not used;
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

- v0.3.1 released: no `src/chew` package/CLI behavior change in that cycle — docs and CI tooling
  only. Verification at release time (`release/v0.3.1`): `337 passed, 2 skipped`, Ruff clean, mypy
  clean (86 source files).
- `feat/engineering-knowledge` (commit `31918fd`, merged with `origin/develop` after v0.3.1): the
  Engineering System Audit Track work above (RunManifest v1 + prompt bundle ID/fingerprint fix +
  benchmark provenance metadata + documentation truth pass). Re-verified after the merge:
  `351 passed, 2 skipped`, Ruff clean, mypy clean (87 source files), plus
  `scripts/check_architecture.py`, `scripts/check_docs_sync.py`, and
  `scripts/check_release_consistency.py` all passing. No live provider or Frontier benchmark ran.
