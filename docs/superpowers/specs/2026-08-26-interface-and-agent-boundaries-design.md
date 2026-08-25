# Interface, Presentation, and Agent Boundary Design

## Status

Approved architectural direction. This specification extends the Grounded Knowledge Tree
compiler and agent-orchestration direction without changing the current compiler behaviour.

## Goal

Keep `chew`'s core purpose—turning one source into a reusable, grounded Knowledge Pack—
independent of how a person or another program asks for it or consumes the result.  The
design must make a future web client, HTTP API, MCP server, and bounded agent workflow
possible without allowing any of them to reach into SQLite, artifacts, transcript
providers, or AI runtime credentials directly.

## Decisions

### Keep `app`, do not rename it to `examples`

`app` is the application layer.  It owns product use cases such as generate, resume,
status, diagnostics, and later read/render/research. `ApplicationService` is already
the shared facade used by the CLI and future integrations.

`examples` has a different responsibility: small, disposable programs showing a public
API. It may be added later at the repository root, but it cannot replace `app` and does
not take part in production dependency wiring.

### Keep `core` as the domain

There will not be both a `core` layer and a separate `domain` layer. In this project
`core` is the domain: immutable models, source identity, validation invariants, and
prompts that define semantic contracts. A second package with the same responsibility
would make import direction and ownership less clear.

### Do not subdivide `pipeline` pre-emptively

`pipeline` already has focused modules for input preparation, segmentation, extraction,
evidence, tree assembly, scheduling, policy, and output compilation. Its common reason
to change is the knowledge-compilation workflow, so it remains one package. A new
sub-package is justified only when it has a separate extension boundary or independently
testable policy—not merely because it resembles a Clean Architecture folder name.

### Add an explicit inbound-interface boundary

The product-facing term is **interfaces**, not simply *view layer*. CLI, HTTP, and MCP
are all inbound interfaces, but only a web client is a visual view. Interfaces translate
their protocol-specific input into application requests, invoke a typed application use
case, and translate the result into a protocol-specific response. They contain no
analysis, evidence, storage, or model-routing policy.

The initial physical shape is intentionally small:

```text
src/chew/
  core/                         # Domain invariants and immutable values
  pipeline/                     # Knowledge compilation and local rendering
  app/                          # Application use cases and composition root
  agents/                       # Future bounded control plane
    contracts/                  # Session, budget, grant, request/result values
    policy/                     # Pure tool and budget authorisation
    ports/                      # AgentTool and AgentRuntime protocols
    adapters/                   # Empty until an optional LangGraph adapter is added
  interfaces/                   # Inbound protocol boundary
    contracts/                  # Stable input/result/error DTOs for integrations
    presenters/                 # CLI text and JSON response shaping
    cli/                        # Migration home for Typer-specific adapters
    http/                       # Future FastAPI request/response adapters
    mcp/                        # Future MCP request/response adapters
  storage/ harness/ transcripts/# Outbound infrastructure adapters
```

Existing `chew.cli` and `chew.server` remain compatible entry points. They are migrated
only as a concrete interface adapter is introduced; this first step does not move the
working CLI or turn the health server into a public API.

## Three Outputs That Must Not Be Confused

```text
Knowledge Pack
  ├─ Product output renderer (`pipeline.outputs`)
  │    Digest · Blog · Study · Obsidian · JSON artifacts
  │
  └─ Interface presenter (`interfaces.presenters`)
       terminal text · machine JSON · future HTTP/MCP response envelopes

Web client (future, separately deployable)
  └─ consumes only the versioned HTTP API contract
```

Product output rendering is reusable content generation and remains close to the
Knowledge Pack. A presenter only describes the result of an operation to a caller; it
never re-renders a pack, writes export artifacts, or invokes a model.

## Dependency and Data Flow

```text
Web client / CLI / MCP client
          |
          v
interfaces (parse, validate protocol, present result)
          |
          v
app (typed use cases)
          |
          +--------------------+
          |                    |
          v                    v
pipeline (compile/render)   agents (future control plane)
          |                    |
          +---------+----------+
                    v
      core contracts and outbound ports
                    |
                    v
storage / transcripts / harness adapters
```

An agent control flow is similarly constrained:

```text
natural-language request -> interface -> normalized intent -> agent policy
  -> allowlisted typed application tool -> Knowledge Pack / rendered artifact
  -> presenter -> caller
```

An agent never obtains a database connection, filesystem artifact path, shell, browser
session, cookie, Keychain credential, or runtime provider credential. LangGraph, when
needed, belongs only in `agents.adapters` behind `AgentRuntime` and is installed through
an optional extra.

## Future Web Client Boundary

The web UI is not a Python adapter embedded in the domain. It is a separately deployable
client, initially allowed to live in `apps/web/` for coordinated development and later
extractable without changing the API. It uses only a versioned HTTP contract, for example:

- `POST /v1/analyses` to begin an analysis;
- `GET /v1/runs/{run_id}` to observe a run;
- `GET /v1/packs/{pack_id}` to read a safe Knowledge Pack projection;
- `POST /v1/packs/{pack_id}/renders` to request a deterministic output profile.

These endpoint names describe the future contract; no public API, authentication scheme,
or web framework is added in this first slice. `chew serve` remains health/readiness only.

## Initial Implementation Slice

1. Add import-safe `agents` and `interfaces` package skeletons with concise package-level
   boundary documentation.
2. Define typed, dependency-free agent values, tool grants, and `AgentTool` protocol.
3. Define an interface result envelope and presenter protocol that can wrap the existing
   `CommandResult` without importing Typer or FastAPI.
4. Add unit tests proving contracts are immutable, presenters do not depend on CLI/web
   frameworks, and denied tool grants cannot be invoked.
5. Update the architecture diagrams and agent index to show the interface and web-client
   boundary. Keep the old CLI/server paths working unchanged.

## Non-Goals

- No React/Next.js application, public REST API, authentication, or WebSocket progress
  service in this slice.
- No LangGraph dependency, MCP server, external research provider, or autonomous loop.
- No repository-wide package move from `cli/` to `interfaces/`.
- No new broad logging system; current structured redacted logs and optional telemetry
  remain sufficient.
- No change to the current knowledge-compilation, output-rendering, or benchmark policy.

## Acceptance Criteria

- `app` remains the single application-use-case boundary; `examples` is not used for
  production behaviour.
- Existing CLI commands and `chew.server.create_app()` imports remain backward compatible.
- The new contracts depend only on standard library/Pydantic-compatible domain values, not
  Typer, FastAPI, LangGraph, SQLite, artifact storage, or vendor SDKs.
- Product-output renderers and protocol presenters stay separate by import direction and
  tests.
- A future web client can be added or extracted while depending only on an HTTP contract.
- Documentation describes the physical current state versus deferred adapters precisely.
