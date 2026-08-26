# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Branch: `feat/repository-governance`
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decisions: [`interface and agent boundaries`](docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md), [`Grounded Knowledge Compiler modules`](docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md)

## Immediate Repository Governance Priority

- Open: PR #12 (`feat/repository-governance` → `develop`) is `MERGEABLE`/`CLEAN` with all required
  checks passing; awaiting a decision on merging it.
- After PR #12 merges, verify on the *next* PR into `develop` that the new `metadata-label` job
  (title/branch → `kind:*`/`status:needs-triage` labels) actually fires — `pull_request_target`
  reads the workflow definition from the base branch, so it could not run on PR #12 itself
  (`IMPROVEMENTS.md` §3).
- P1 remaining: decide whether to configure `PROJECTS_TOKEN` for automatic Project writes, or keep
  Project triage manual (`IMPROVEMENTS.md` §4).
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

Before adding more product surface, decide whether to merge PR #12, then finish the small remaining
repository governance queue in [`IMPROVEMENTS.md`](IMPROVEMENTS.md): metadata-labeler live
verification and the Project auto-add (`PROJECTS_TOKEN`) decision.

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

- Repository governance is implemented and pushed to `feat/repository-governance` (PR #12, targeting
  `develop`): version alignment, release consistency validator, release/PR governance workflows,
  labels, Issue Forms, CODEOWNERS, ADR index, release playbook, architecture boundary guard, PR
  metadata labeler, optional Project triage, and required status checks.
- Latest full verification (this session): `331 passed, 2 skipped`, Ruff clean, mypy clean. No live
  provider or Frontier benchmark ran.
- Working tree is clean; latest commit is `d9c0343` (pushed).
