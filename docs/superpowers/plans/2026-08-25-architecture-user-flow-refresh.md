# Architecture User-Flow Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the bilingual architecture diagrams and README so users first see the product flow, then external boundaries, then the meaningful internal pipeline.

**Architecture:** Keep three progressive diagrams per language. `user-flow` presents visible CLI behavior, `external-boundaries` isolates adapters from the core, and `internal-pipeline` shows the irreversible data path plus cross-cutting run control, state, logging, and tracing. README prose mirrors those views and links to deeper operational documentation rather than becoming a package inventory.

**Tech Stack:** Mermaid flowcharts, committed PNG renderings, Markdown, existing Python verification suite.

## Global Constraints

- Use the same diagram nodes, edge semantics, order, and filenames in English and Korean; translate only labels.
- Do not add a browser/cookie path, vector database, provider-quality comparison, Frontier benchmark, latency claim, worker count, or unimplemented module.
- Treat Ollama as optional bounded transcript annotation, never a summary/judgment runtime.
- Show logging, tracing, durable checkpoints, and state as cross-cutting concerns rather than every package/module.
- Keep the generated preprocessing run directories untracked.

---

### Task 1: Refresh the bilingual user-flow diagrams

**Files:**
- Modify: `assets/architecture/en/user-flow.mmd`
- Modify: `assets/architecture/ko/user-flow.mmd`
- Modify: `assets/architecture/en/user-flow.png`
- Modify: `assets/architecture/ko/user-flow.png`

**Consumes:** Current CLI behavior: public URL/local media/user-supplied transcript inputs, compatible pack reuse, status/resume, and deterministic output profiles.

**Produces:** A user-visible happy path with two recovery/reuse branches, suitable for the first README architecture image.

- [ ] **Step 1: Replace the English source with the visible flow**

  Use five primary nodes in this order: `Input`, `Transcript`, `Analyze once`,
  `Knowledge Pack`, `Outputs`. Add only `compatible pack? -> reassemble` and
  `interrupted/authentication-required -> status -> resume` branches. Label
  outputs as Digest, Blog, Study, and Obsidian.

- [ ] **Step 2: Mirror the English graph in Korean**

  Preserve every node ID and edge direction. Translate visible labels to Korean;
  retain product identifiers such as `Knowledge Pack`, `status`, and `resume`
  where they identify CLI concepts.

- [ ] **Step 3: Render and inspect both images**

  Render each source to its matching PNG with the repository's available
  Mermaid CLI. Verify the output dimensions, Korean font readability, branch
  labels, and no clipped node text by opening the PNGs.

- [ ] **Step 4: Commit the user-flow asset set**

  ```bash
  git add assets/architecture/en/user-flow.mmd assets/architecture/en/user-flow.png \
    assets/architecture/ko/user-flow.mmd assets/architecture/ko/user-flow.png
  git commit -m "docs: refresh architecture user flows"
  ```

### Task 2: Add bilingual external-boundary diagrams

**Files:**
- Create: `assets/architecture/en/external-boundaries.mmd`
- Create: `assets/architecture/ko/external-boundaries.mmd`
- Create: `assets/architecture/en/external-boundaries.png`
- Create: `assets/architecture/ko/external-boundaries.png`

**Consumes:** Ports & Adapters boundaries from `docs/agent-index.md` and the product constraints in `IMPROVEMENTS.md`.

**Produces:** A compact system-context image showing only meaningful external dependencies and one application-core boundary.

- [ ] **Step 1: Create the English source**

  Place a `chew application core` subgraph in the center containing `Application
  service`, `identity + policy`, `grounded extraction + local evidence`, and
  `Knowledge Pack + deterministic rendering`. Around it, draw adapters for CLI
  / local input files, public captions / optional Whisper, Frontier runtimes,
  optional installed Ollama annotation, SQLite + artifacts, and optional
  OpenTelemetry / Jaeger export. Use dashed edges only for optional adapters.

- [ ] **Step 2: Create the Korean source from the same graph**

  Preserve IDs, group order, and optional-edge styling. Translate the labels
  while preserving runtime product names and `SQLite`, `OpenTelemetry`, and
  `Jaeger` identifiers.

- [ ] **Step 3: Render and visually inspect both images**

  Confirm the core boundary is clear, optional adapters are visually distinct,
  no adapter suggests direct database/provider access by an agent, and no
  removed Frontier benchmark path appears.

- [ ] **Step 4: Commit the external-boundary asset set**

  ```bash
  git add assets/architecture/en/external-boundaries.mmd assets/architecture/en/external-boundaries.png \
    assets/architecture/ko/external-boundaries.mmd assets/architecture/ko/external-boundaries.png
  git commit -m "docs: add architecture boundary diagrams"
  ```

### Task 3: Refresh the bilingual internal-pipeline diagrams

**Files:**
- Modify: `assets/architecture/en/internal-pipeline.mmd`
- Modify: `assets/architecture/ko/internal-pipeline.mmd`
- Modify: `assets/architecture/en/internal-pipeline.png`
- Modify: `assets/architecture/ko/internal-pipeline.png`

**Consumes:** Current GKT path: raw identity/transcript validation, prepared transcript, grounded extraction, local evidence grounding, Knowledge Pack, deterministic render.

**Produces:** A single internal data path with three cross-cutting support bands: run control, durable state, and observability.

- [ ] **Step 1: Replace the English main path**

  Use these ordered nodes: `Source identity + raw transcript`, `Validate +
  prepare`, `Grounded extraction`, `Local evidence grounding`, `Knowledge Pack`,
  `Deterministic output rendering`. Remove the old topic/chapter DAG, worker
  counts, speed multiplier, and runtime-specific output calls.

- [ ] **Step 2: Add three non-main-path bands**

  Add `Run control` (policy, checkpoints, pause/resume, unknown external
  outcome), `Durable state` (SQLite job state plus content-addressed artifacts),
  and `Observability` (structured logs, OpenTelemetry spans, optional Jaeger
  export). Connect them with non-directional/dashed support edges to the main
  path rather than inserting them as data transforms.

- [ ] **Step 3: Mirror the source in Korean and render both PNGs**

  Keep Mermaid IDs and graph geometry aligned. Open both renderings and verify
  cross-cutting bands do not obscure the main pipeline or require reading
  package-level details.

- [ ] **Step 4: Commit the internal-pipeline asset set**

  ```bash
  git add assets/architecture/en/internal-pipeline.mmd assets/architecture/en/internal-pipeline.png \
    assets/architecture/ko/internal-pipeline.mmd assets/architecture/ko/internal-pipeline.png
  git commit -m "docs: simplify internal pipeline diagrams"
  ```

### Task 4: Rewrite the bilingual README architecture narrative

**Files:**
- Modify: `README.md:119-145`
- Modify: `README.ko.md:120-146`
- Modify: `docs/agent-index.md:1-110` only if a README statement needs an
  updated canonical module pointer.

**Consumes:** The six rendered diagrams and current product guarantees.

**Produces:** Parallel English/Korean README sections that answer what users do, what the app connects to, and how a run is made trustworthy.

- [ ] **Step 1: Replace the current two-view Architecture section in `README.md`**

  Use headings `How a run works`, `External boundaries`, and `Inside the
  pipeline`. Embed `en/user-flow.png`, `en/external-boundaries.png`, and
  `en/internal-pipeline.png` in that order. Explain cache reuse and resume in
  the first section; optional adapters and their restrictions in the second;
  grounding, durable state, structured logs, and traces in the third.

- [ ] **Step 2: Mirror the section in `README.ko.md`**

  Use headings `한 번의 실행이 진행되는 방식`, `외부 경계`, and `내부
  파이프라인`. Embed the Korean assets in the same order. Keep command names,
  product names, and linked canonical documents equivalent to English.

- [ ] **Step 3: Keep observability concise and link outward**

  Preserve the existing Jaeger screenshot only as a supporting observability
  example. State that structured logs and traces explain runs but are optional;
  point module-level readers to `docs/agent-index.md` and operational readers to
  `docs/wiki/transcript-acquisition.md`.

- [ ] **Step 4: Verify README links and commit documentation**

  Run:

  ```bash
  rg -n "assets/architecture/(en|ko)/(user-flow|external-boundaries|internal-pipeline)\.png" README.md README.ko.md
  git diff --check
  git add README.md README.ko.md docs/agent-index.md CHANGELOG.md handoff.md
  git commit -m "docs: explain architecture through user flows"
  ```

### Task 5: Full verification and handoff refresh

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `handoff.md`

**Consumes:** Completed diagram and README assets.

**Produces:** A durable record of the documentation refresh and a handoff with no stale diagram next step.

- [ ] **Step 1: Record the completed documentation behavior**

  Add one `Changed` entry in `CHANGELOG.md` stating that the README now
  separates user flow, external adapter boundaries, and the core GKT pipeline,
  with logging/tracing depicted as cross-cutting concerns.

- [ ] **Step 2: Refresh the execution index**

  Remove this documentation work from `handoff.md` and retain only the next
  active product objective plus the no-Frontier-benchmark constraint.

- [ ] **Step 3: Run the required full verification suite**

  ```bash
  uv run --extra dev pytest
  uv run --extra dev ruff check .
  uv run --extra dev mypy src/chew
  ```

- [ ] **Step 4: Inspect the final worktree and report it**

  Run:

  ```bash
  git status --short
  git log -5 --oneline
  ```

  Confirm that only intended documentation/assets are committed and that the
  existing untracked preprocessing metric run directories remain excluded.
