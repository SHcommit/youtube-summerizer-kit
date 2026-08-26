# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Released: `v0.3.0` is tagged on `master` (merge commit `95e3019`) and the GitHub Release is live
  with built wheel/sdist: https://github.com/SHcommit/youtube-summerizer-kit/releases/tag/v0.3.0
- PyPI publish was intentionally skipped — no `PYPI_API_TOKEN` secret is configured yet. `pip
  install youtube-summarizer-kit` does not work until that secret is added and a release re-runs
  (or a new tag is pushed). GitHub Release download is the current distribution channel.
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decisions: [`interface and agent boundaries`](docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md), [`Grounded Knowledge Compiler modules`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)

## Immediate Repository Governance Priority

- Done: `IMPROVEMENTS.md` §1 fully verified live during the v0.3.0 release — the release PR
  (`release/v0.3.0` → `master`) triggered `Check release version consistency` for real (head ref
  started with `release/`) and it passed; required status checks worked on both `develop` and
  `master`.
- Found and fixed during this release: `master` carried drift never forward-ported to `develop`
  after v0.2.0 (`actions/setup-python@v7`, `softprops/action-gh-release@v3` in `cd.yml`/`ci.yml`,
  and `src/chew/__init__.py.__version__` stuck at a stale value). Merged `master` back into
  `develop` (branch `chore/sync-master-into-develop`) to close the loop this time. **Going forward,
  always merge `master` back into `develop` right after a release** — this was skipped for v0.2.0
  and caused a real merge conflict when preparing v0.3.0.
- Hardened `scripts/check_release_consistency.py` to also validate `src/chew/__init__.py.__version__`
  against `pyproject.toml`, with new tests, so this exact drift can't recur silently.
- Still open, not release-gated:
  - `IMPROVEMENTS.md` §3: the `metadata-label` job never appeared in Auto Labeler's job list across
    three attempts (PR #12/#13/#14), even via raw REST API, despite `develop`'s file confirming the
    job exists — looks like GitHub caching the pre-merge job list for this `pull_request_target`
    workflow. Not re-checked during this release cycle either. Next step if picked back up: land a
    trivial commit to `.github/workflows/labeler.yml` to try to force a cache refresh.
  - `IMPROVEMENTS.md` §4: decide whether to configure `PYPI_API_TOKEN` (for PyPI) and `PROJECTS_TOKEN`
    (for Project auto-add), and whether to expand the Project `Status` field from GitHub's default
    `Todo/In Progress/Done` to `Inbox/Ready/Doing/Review/Benchmark/Release/Done`.
  - Whether to retroactively split the large `[0.2.0]` CHANGELOG section into ADR/report entries.
  - A reproducible architecture-diagram renderer (wrapping the already-installed `mmdc`/`d2` CLIs so
    `assets/architecture/**` PNGs regenerate from their `.mmd`/`.d2` sources) was requested and is
    still unbuilt.

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
repository governance queue above (§3 labeler live-check, §4 token/Status decisions, CHANGELOG
split, diagram renderer) — none of it blocks other work.

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

- v0.3.0 released: `src/chew` package code is unchanged from v0.2.0 in this cycle — the release
  captured repository governance/CI tooling only (release consistency checks, PR/issue templates,
  architecture boundary guard, PR metadata labeling, optional Project triage, required status
  checks) plus the master→develop drift fix above.
- Latest full verification: `333 passed, 2 skipped` (2 new tests for the `__init__.py` version
  check), Ruff clean, mypy clean. No live provider or Frontier benchmark ran.
