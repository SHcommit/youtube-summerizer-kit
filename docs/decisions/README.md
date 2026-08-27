# Architecture Decision Records

This directory stores durable architecture and repository operating decisions.
Use ADRs for decisions that future maintainers need to understand before
changing architecture, runtime policy, release flow, governance, or long-lived
engineering practice.

## Index

| Decision | Scope |
|---|---|
| [`local-llm-runtime.md`](local-llm-runtime.md) | Local LLM/Ollama remains optional and bounded to input cleanup. |
| [`0002-repository-governance.md`](0002-repository-governance.md) | Repository governance, release consistency, CHANGELOG scope, labels, PR/issue flow, and right-sized automation. |
| [`0003-run-manifest-provenance.md`](0003-run-manifest-provenance.md) | `RunManifest` v1 as the per-run code/prompt/schema/model provenance snapshot. |

## When to Add an ADR

Add or update an ADR when a change:

- changes package, module, or layer boundaries;
- changes release or repository governance;
- changes prompt/model/runtime responsibility;
- creates a durable benchmark or evidence policy;
- accepts a meaningful tradeoff that is not obvious from code.

Keep execution checklists in `IMPROVEMENTS.md`, not in ADRs.
