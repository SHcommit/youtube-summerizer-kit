# Current Execution Index

> Read this first to answer "what should we do now?" Read the linked canonical document only
> when its acceptance criteria or product decision is needed.

## Branch and State

- Branch: `feat/ollama-summary-efficiency`
- Active roadmap: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)

## Next Priorities

1. Run reviewed Korean and long-video preprocessing benchmarks. Keep preprocessing opt-in unless
   it achieves the 10% adoption gate without quality regression.
2. Run `chew benchmark run --short-video` for the 4m35s `5m_en` fixture after YouTube caption
   rate limiting clears and a reviewed reference is added. Compare same-transcript, same-Frontier
   one-pass and hierarchical paths before changing the default analysis path.
3. Complete the remaining Policy/Sandbox work: decide on per-task timeout/retry policy in
   `ExecutionPlan` and validate evidence handling on a real Frontier run.

## Current Decision

- Frontier remains the final reasoning and summary runtime.
- Ollama does not perform summary or judgment work. Reconsider it only for a specifically defined,
  low-risk helper task with measured benefit.
- Knowledge Graph, Notion, RSS, MCP, REST API, and automation are deferred.

## Verification and Working Tree

- Last documentation check: `git diff --check` passed.
- Untracked benchmark-report directories exist under
  `reports/performance-comparisons/transcript-preprocessing/`; inspect before staging and do not
  include them accidentally.
