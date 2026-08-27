# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Released: `v0.3.1` is tagged on `master` (merge commit `4d505d1`) and the GitHub Release is live
  with built wheel/sdist: https://github.com/SHcommit/youtube-summerizer-kit/releases/tag/v0.3.1
- `master` was merged back into `develop` right after tagging (PR #21,
  `chore/sync-master-into-develop-v0.3.1`) so both branches carry the same version/CHANGELOG state.
- PyPI publish was intentionally skipped — no `PYPI_API_TOKEN` secret is configured yet. `pip
  install youtube-summarizer-kit` does not work until that secret is added and a release re-runs
  (or a new tag is pushed). GitHub Release download is the current distribution channel.
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decisions: [`interface and agent boundaries`](docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md), [`Grounded Knowledge Compiler modules`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)

## Immediate Repository Governance Priority

- Done: v0.3.1 followed the full playbook (`docs/wiki/release-playbook.md`) cleanly —
  `release/v0.3.1` → `master` (PR #20), tag `v0.3.1` pushed, CD ran `Create GitHub Release`
  successfully, then `master` → `develop` sync (PR #21). No merge conflicts.
- Still unresolved despite the earlier "fix": `metadata-label` (`.github/workflows/labeler.yml`
  `Label PR metadata` job) failed again on PR #20 with the same
  `Resource not accessible by integration (addLabelsToLabelable)` error, even though the job
  already declares `pull-requests: write` and `issues: write`. It is **not** a required status
  check (only `test (3.12)`, `test (3.13)`, `Check PR metadata and stale instructions` are, per the
  `require-ci-status` ruleset), so it did not block merging, but the underlying cause is still
  open — likely an org/repo Actions default-permission or `pull_request_target` restriction not
  visible from the workflow YAML alone. Worth a dedicated investigation before relying on this
  label automation.
- Still open, not release-gated:
  - Decide whether to configure `PYPI_API_TOKEN` for PyPI publishing. GitHub Release download is the
    current distribution channel until this is configured.
  - Whether to retroactively split the large `[0.2.0]` CHANGELOG section into ADR/report entries.
  - Documentation drift is now checked by `scripts/check_docs_sync.py` in PR Governance. Architecture
    diagram PNGs can be regenerated with `uv run python scripts/render_architecture_assets.py`.

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
- The initial `agents` package supplies dependency-free budget, grant, tool, and policy contracts
  only. There is no LangGraph runtime, MCP server, public HTTP API, authentication scheme, or web
  UI yet. A future web client consumes only a versioned HTTP contract and can live as a separately
  deployable `apps/web` project when that API exists.

## Next Decision

No active release in flight. Before adding more product surface, resume the small remaining
repository governance queue above (PyPI publish decision, optional CHANGELOG split, and the
recurring `metadata-label` permission failure) — none of it blocks other work. GitHub Projects are
intentionally not used; execution tracking lives in Linear plus repo-native Issues/PRs/labels/milestones.

The documentation-only module boundaries are present. Activating either future module still
requires one selected end-to-end user flow and a versioned, typed, read-only `KnowledgeGateway`
from `research-engine` to `chew`. Do not add ApplicationService agent tools, LangGraph, MCP, HTTP
endpoints, web UI code, model dependencies, or a public package automatically.

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

- v0.3.1 released: `src/chew` package code is unchanged from v0.3.0 in this cycle — the release
  captured docs/CI tooling only (`.github/release.yml` release-note categories,
  `scripts/check_docs_sync.py` doc-sync guard, the metadata-labeler permission fix in
  `.github/workflows/labeler.yml`, and removal of the optional GitHub Project workflow). No
  benchmark-sensitive pipeline/harness/scheduler changes, so `reports/BENCHMARK.md` was not touched.
- Latest full verification (on `release/v0.3.1` before merge): `337 passed, 2 skipped`, Ruff clean,
  mypy clean (`86 source files`). No live provider or Frontier benchmark ran.
