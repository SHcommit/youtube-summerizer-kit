# Current Execution Index

> Read this first to answer “what should we do now?” Consult the linked canonical documents only
> for their acceptance criteria or product decisions.

## Branch and State

- Branch: `feature/benchmark-quality-readiness`
- Active work: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)
- Architecture decision: [`docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md`](docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md)

## Current Architecture Decision

- `core` is the domain; do not add a duplicate `domain` layer. `pipeline` remains the cohesive
  knowledge-compilation package and is not split pre-emptively.
- `app` is the product-use-case boundary. It is not an `examples` package.
- `pipeline.outputs` creates reusable product artifacts. `interfaces` presents operation results to
  CLI now and to future HTTP/MCP consumers later; it does not implement product rendering.
- The initial `agents` package supplies dependency-free budget, grant, tool, and policy contracts
  only. There is no LangGraph runtime, MCP server, public HTTP API, authentication scheme, or web
  UI yet. A future web client consumes only a versioned HTTP contract and can live as a separately
  deployable `apps/web` project when that API exists.

## Next Priorities

1. Define typed, read-only ApplicationService tools over completed GKT artifacts, then evaluate an
   optional bounded LangGraph adapter with separate session/checkpoint state.
2. Keep natural-language `IntentParser` deferred until its deterministic command/option contract is
   specified; it must not access credentials, browser state, or provider tools.
3. Keep transcript preprocessing opt-in. The reviewed seven-fixture metrics-only conclusion is in
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

- `d591ceb` adds bounded agent contracts; full verification was `315 passed, 2 skipped`, Ruff and
  mypy clean.
- `cb0c8b0` adds protocol-neutral interface result presentation and preserves CLI machine fields;
  full verification was `319 passed, 2 skipped`, Ruff and mypy clean.
- `e8b53b1` documents and diagrams the same boundary, distinguishing implemented CLI presentation
  from deferred HTTP, MCP, and web consumers. Full verification is `319 passed, 2 skipped`; Ruff
  and mypy are clean. No live Frontier benchmark was run.
