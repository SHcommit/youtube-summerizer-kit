# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Release branch: `release/v0.3.0` (from `develop`)
- Release target: `master` with tag `v0.3.0`; CD publishes the verified wheel and GitHub Release,
  then publishes to PyPI when the repository `PYPI_API_TOKEN` secret is configured.
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decisions: [`interface and agent boundaries`](docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md), [`Grounded Knowledge Compiler modules`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)

## Immediate Repository Governance Priority

- In progress: PR #16 (`release/v0.3.0` → `master`) is open. Merging `origin/master` into the
  release branch surfaced real drift: `master` had `actions/setup-python@v7` and
  `softprops/action-gh-release@v3` bumps in `cd.yml`/`ci.yml`, and `src/chew/__init__.py.__version__`
  fixed to `0.2.0`, none of which were ever forward-ported to `develop` after the v0.2.0 release
  (the release playbook's "After Release" step 3 was skipped). Resolved by keeping master's action
  version bumps and bumping `__init__.py` to `0.3.0`. `check_release_consistency.py` does not check
  `__init__.py` at all — worth adding so this can't silently drift again.
- **Re-verify during this release**, all three in one pass:
  - `IMPROVEMENTS.md` §1: `release/*` required-checks scenario, and that the release PR actually
    targets `release/vX.Y.Z` → `master`.
  - `IMPROVEMENTS.md` §3: the new `metadata-label` job. Tried three times already (PR #12, #13, #14)
    and it never appeared in the job list, even via the raw REST API, despite `develop`'s Contents
    API confirming the job exists in the file — looks like GitHub is caching the pre-merge job list
    for this `pull_request_target` workflow. Stopped investigating further per user decision
    (2026-08-26); re-check on the next release PR, and if still missing, land a trivial commit to
    `.github/workflows/labeler.yml` to try to force a cache refresh.
  - `IMPROVEMENTS.md` §5: `[Unreleased]` actually empties into a versioned heading, and the GitHub
    Release body includes user impact + benchmark/report links, not just a PR list.
- Open decisions (not release-gated, can be made any time): configure `PROJECTS_TOKEN` for automatic
  Project writes vs. keep manual triage; expand the Project's `Status` field from GitHub's default
  `Todo/In Progress/Done` to the documented `Inbox/Ready/Doing/Review/Benchmark/Release/Done`
  (`IMPROVEMENTS.md` §4); whether to retroactively split the 211-line `[0.2.0]` CHANGELOG section
  into ADR/report entries, given it's already a tagged, published release.
- Most of the P0/P1/P2 governance queue (required status checks, architecture guard, docs role
  separation, stale-naming check) is now done — see `IMPROVEMENTS.md` for the trimmed remainder.

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

Cut the next release from `develop` (see `docs/wiki/release-playbook.md`), which naturally exercises
`IMPROVEMENTS.md` §1/§3/§5. After that, resume the small remaining repository governance queue in
`IMPROVEMENTS.md`: the `PROJECTS_TOKEN` / Project `Status` field decision (§4), and whether to
retroactively split the `[0.2.0]` CHANGELOG section. A reproducible architecture-diagram renderer
(wrapping the already-installed `mmdc`/`d2` CLIs so `assets/architecture/**` PNGs regenerate from
their `.mmd`/`.d2` sources instead of being hand-made) was also requested and is still unbuilt.

The documentation-only module boundaries are present. After governance work, activating either
future module still requires one selected end-to-end user flow and a versioned, typed, read-only
`KnowledgeGateway` from `research-engine` to `chew`. Do not add ApplicationService agent tools,
LangGraph, MCP, HTTP endpoints, web UI code, model dependencies, or a public package automatically.

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

- Repository governance merged into `develop` (`9c435d1`): version alignment, release consistency
  validator, release/PR governance workflows, labels, Issue Forms, CODEOWNERS, ADR index, release
  playbook, architecture boundary guard, PR metadata labeler, optional Project triage, and required
  status checks (`require-ci-status` on develop/master, `require-release-consistency` on master).
- Latest full verification (this session): `331 passed, 2 skipped`, Ruff clean, mypy clean. No live
  provider or Frontier benchmark ran.
- `feat/repository-governance` local/remote branch still exists (not deleted after merge); safe to
  delete once confirmed unneeded.
