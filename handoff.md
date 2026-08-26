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

- P0: align release version state before the next tag. The latest GitHub release/tag is `v0.2.0`,
  and `pyproject.toml` is aligned at version `0.2.0`; release consistency checks now guard future
  tags and release branches.
- P0 remaining after merge: connect the new CI, PR Governance, and Release Consistency workflows to
  the active repository ruleset as required status checks once their check run names exist.
- P1 remaining: decide whether Project auto-add is worth the token/permission maintenance cost.

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

Before adding more product surface, finish the remaining repository governance queue in
[`IMPROVEMENTS.md`](IMPROVEMENTS.md): required status checks after workflow merge, and Project
auto-add decision.

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

- Repository governance implementation is in progress: version alignment, release consistency
  validator, release/PR governance workflows, labels, Issue Forms, CODEOWNERS, ADR index, release
  playbook, and architecture boundary guard have been added locally. Full verification should be
  re-run before handoff.
- `020d965` records the approved Grounded Knowledge Compiler/module design; the documentation-only
  module-boundary update is verified with `319 passed, 2 skipped`, Ruff clean, and mypy clean. No
  live provider or Frontier benchmark ran.
- `d591ceb` adds bounded agent contracts; full verification was `315 passed, 2 skipped`, Ruff and
  mypy clean.
- `cb0c8b0` adds protocol-neutral interface result presentation and preserves CLI machine fields;
  full verification was `319 passed, 2 skipped`, Ruff and mypy clean.
- `e8b53b1` documents and diagrams the same boundary, distinguishing implemented CLI presentation
  from deferred HTTP, MCP, and web consumers. Full verification is `319 passed, 2 skipped`; Ruff
  and mypy are clean. No live Frontier benchmark was run.
