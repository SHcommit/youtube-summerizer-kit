# Grounded Knowledge Compiler and Future Modules Design

## Purpose

Keep `chew` as the stable public package and CLI while naming its architectural role
precisely: **Grounded Knowledge Compiler**.  Add two documentation-only module
boundaries so later sessions can build independent, composable packages without
coupling them to the existing compiler.

## Naming

| Name | Role | Status |
| --- | --- | --- |
| `chew` | Public package, CLI, and **Grounded Knowledge Compiler** | Implemented |
| `intent-analysis` | Reusable natural-language request-analysis package | Documentation boundary only |
| `research-engine` | Follow-up research, retrieval, session, and future graph execution package | Documentation boundary only |

`chew` is not renamed.  Existing imports, command names, storage, and artifacts
remain compatible.  “Grounded Knowledge Compiler” is the product's architectural
role: it turns a source into an evidence-grounded Knowledge Tree and a reusable
Knowledge Pack.

## Target Repository Shape

```text
youtube-summarizer-kit/
├── src/chew/                         # chew — Grounded Knowledge Compiler
│   ├── core/                          # Source, evidence, GKT, Knowledge Pack values
│   ├── pipeline/                      # Compile source → GKT → Knowledge Pack → outputs
│   ├── app/                           # Compiler use cases and dependency assembly
│   ├── storage/                       # Run and artifact persistence
│   ├── transcripts/                   # Source-input adapters
│   ├── harness/                       # AI runtime adapters
│   ├── interfaces/ and cli/           # Existing inbound interfaces
│   └── agents/                        # Existing bounded control contracts only
│
└── modules/
    ├── intent-analysis/               # Documentation-only boundary now
    │   └── README.md                   # Contract and non-goals
    └── research-engine/               # Documentation-only boundary now
        └── README.md                   # Contract and dependency direction
```

No `pyproject.toml`, Python package, model dependency, LangGraph dependency,
MCP server, web application, or CLI command is added in this slice.

## Dependency Direction

```text
natural-language interface
        ↓
intent-analysis
        ↓
research-engine ────────read-only typed gateway──────→ chew
```

Explicit `chew` CLI commands such as `chew summarize <URL>` remain deterministic
and bypass natural-language parsing.  A future natural-language interface may
choose to call `intent-analysis`; that package must not execute tools itself.

`research-engine` may later use a completed Knowledge Pack for retrieval and
follow-up questions.  It must not receive direct database, artifact-path, shell,
browser, cookie, credential, or runtime-adapter access.  Any future gateway into
`chew` exposes typed, read-only Pack data rather than its internals.

## Module Responsibilities

### `intent-analysis`

- Owns transport-neutral request interpretation: `IntentParser`, typed intent,
  clarification, unsupported result, and capability description.
- Begins with no model download: deterministic URL/file/option extraction and
  high-confidence patterns only.
- May later add optional ONNX or installed-Ollama adapters behind a port.  A
  model may only propose schema-validated intents; uncertainty returns a
  clarification and never performs an action.
- Does not know RAG, LangGraph, MCP, storage, credentials, or product tools.

### `research-engine`

- Owns future research sessions, retrieval over completed Packs, research notes,
  and optional LangGraph orchestration.
- Consumes `intent-analysis` results and a narrow `chew` knowledge gateway.
- Keeps conversation-derived claims separate from the immutable source-derived
  Knowledge Pack.
- Does not modify the compiler's canonical run/job/artifact schema.

### `chew` — Grounded Knowledge Compiler

- Remains responsible for source acquisition, evidence validation, GKT synthesis,
  Knowledge Pack persistence, and deterministic product-output compilation.
- Remains usable without either future module.
- Does not acquire a default RAG, vector database, LangGraph, or natural-language
  parser in its normal video-analysis path.

## Documentation-Only Acceptance Criteria

1. Architecture-facing documentation calls `chew` the Grounded Knowledge
   Compiler while preserving its package and CLI name.
2. [`modules/intent-analysis/README.md`](../../../modules/intent-analysis/README.md) records its
   contract, non-goals, future optional adapters, and extraction rule.
3. [`modules/research-engine/README.md`](../../../modules/research-engine/README.md) records its
   contract, dependency direction, and non-goals.
4. A new session can tell that the two directories are documentation-only, not runnable
   packages, and can identify the next prerequisite before implementation.
5. No runtime behavior, dependency, provider call, or Frontier benchmark changes.

## Deferred Prerequisite

Before implementing either module, specify the first end-to-end user flow and
create a versioned typed read-only `KnowledgeGateway` contract from `chew` to
`research-engine`.  Only then decide whether the package is still nested here or
is extracted into its own repository.
