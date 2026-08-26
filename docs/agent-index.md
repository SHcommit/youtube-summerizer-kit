# Agent Index — youtube-summarizer-kit

> **Purpose:** Lightweight LLM-readable wiki for AI coding agents. Read this before exploring the codebase. It tells you where everything lives, what the key contracts are, and what to update when you change something.
>
> **Sync rule:** Whenever you add a harness, CLI command, layer, or major feature, update the relevant section below and add a `CHANGELOG.md` entry. This doc is the single reference point agents use to orient themselves — stale entries cost future agents time.

---

## 1. What This Project Does

`chew` is a local-first, resumable **Grounded Knowledge Compiler** that turns YouTube videos and local audio/video files into structured knowledge outputs (Digest, Blog, Study Notes, Obsidian Vault). It analyzes a video **once** into an evidence-grounded, content-addressed **Knowledge Pack** and reassembles it into any output format without re-running LLM calls.

Key properties:
- **Analyze once, reassemble anywhere** — Knowledge Packs are content-addressed (SHA-256) and cached.
- **Parallel DAG execution** — topics run concurrently; chapters merge as soon as their topics finish.
- **Resumable** — SQLite WAL state machine; interrupted runs resume from the last completed job.
- **Multi-runtime** — pluggable AI harnesses; `runtime: auto` selects the best available one.

---

## 2. Layer Map

The codebase follows Ports & Adapters (Hexagonal) architecture. Layers may only import from layers below them.

| Layer | Package | Responsibility |
|---|---|---|
| 1 | `src/chew/core/` | Domain models, URL/content identity (SHA-256), prompt templates |
| 2 | `src/chew/pipeline/` | DAG scheduler, segmentation, synthesis engine, output compilation |
| 3 | `src/chew/storage/` | SQLite WAL state machine, zstd content-addressed artifact storage |
| 4 | `src/chew/harness/` | AI runtime adapters — implement `Harness` protocol from `base.py` |
| 5 | `src/chew/transcripts/` | Transcript/STT adapters — implement `TranscriptProvider` from `base.py` |
| 6 | `src/chew/app/` | Application orchestrator, DI bootstrap, CHEW.md config loader |
| 7 | `src/chew/agents/` | Dependency-free bounded-agent contracts, grant policy, and tool ports; no graph runtime yet |
| 8 | `src/chew/retention/` | Storage retention policy planner and cleaner |
| 9 | `src/chew/benchmark/` | Quality benchmarking runner and comparison reports |
| 10 | `src/chew/interfaces/` | Inbound protocol-neutral response contracts and presenters; HTTP/MCP are future namespaces |
| 11 | `src/chew/cli/` | Typer CLI (bilingual Korean/English), `chew serve` health server launcher |
| — | `src/chew/server.py` | FastAPI `/health` + `/readiness` server (optional `[server]` extras) |

---

## 3. Key Files — Go Here First

| Question | File |
|---|---|
| How does URL normalization / source identity work? | `src/chew/core/identity.py` |
| What fields does a Knowledge Pack have? | `src/chew/core/models.py` — `KnowledgePack` (`completion_status`, missing ranges, runtime/model provenance, grounded-tree fingerprint) |
| How are sensitive operational fields redacted? | `src/chew/core/redaction.py` |
| How are jobs scheduled and retried? | `src/chew/pipeline/scheduler.py` |
| How are run traces isolated? | `src/chew/telemetry.py`, `src/chew/app/bootstrap.py` — injected manager with `ContextVar` collectors |
| How does chapter/topic segmentation work? | `src/chew/pipeline/segmentation.py` |
| How are credential-free caption failures, public fallbacks, and user-provided transcript files handled? | `docs/wiki/transcript-acquisition.md`, `src/chew/transcripts/service.py`, `src/chew/transcripts/user_input.py`, `src/chew/transcripts/youtube_timedtext.py`, `src/chew/transcripts/yt_dlp.py` |
| How are model citations validated? | `src/chew/pipeline/evidence.py` — untrusted candidates become references only after raw span validation |
| How are Codex output schemas made strict-compatible? | `src/chew/harness/codex.py` — normalizes required fields, closed objects, defaults, and fixed tuple arrays before CLI execution |
| How is runtime routing decided? | `src/chew/pipeline/policy.py` — pure Frontier-first execution-plan compiler |
| How does optional local preprocessing work? | `src/chew/pipeline/preprocessing.py` — Strategy composer, conservative filler removal, optional punctuation and semantic boundaries |
| How does the pipeline stitch topics → chapters → pack? | `src/chew/pipeline/engine.py` |
| What does the SQLite schema look like? | `src/chew/storage/database.py` — `initialize()` |
| How do I add a new AI runtime? | `src/chew/harness/base.py` — implement `Harness` protocol |
| How does runtime auto-selection work? | `src/chew/harness/registry.py` |
| How are dependencies wired together? | `src/chew/app/bootstrap.py` |
| What does the application use-case entry point look like? | `src/chew/app/service.py` — `ApplicationService.generate()` |
| What constrains an optional agent tool call? | `src/chew/agents/contracts/models.py`, `src/chew/agents/policy/authorization.py` |
| How is an application result shaped without importing Typer/FastAPI? | `src/chew/interfaces/presenters/command.py` |
| Where is the CLI defined? | `src/chew/cli/main.py` |
| Where is the health server? | `src/chew/server.py` — `create_app()` |

---

## 4. AI Runtime Adapters

All harnesses live in `src/chew/harness/`. Each implements the `Harness` protocol (`harness/base.py`). To add a new one: create `<name>.py`, implement `generate(request) -> GenerationResult`, register in `registry.py` and `bootstrap.py`.

| runtime_id | File | Auth / Setup | Notes |
|---|---|---|---|
| `frontier` | logical selector | Codex, Gemini, or Claude | Default selector; excludes local runtimes |
| `codex` | `codex.py` | `codex login` | Preflight: `codex login status` |
| `gemini` | `gemini.py` | `gemini` login | Verified on first generation |
| `claude` | `claude.py` | `claude auth` | Preflight: `claude auth status` |
| `ollama` | `ollama.py` | None | Local Ollama server required; `CHEW.md` can select `ollama_model` |
| `layered_ollama` | `layered_ollama.py` | None | Routes by task type across 3 model tiers (1.5B / 7B / 14B `q4_K_M`) |
| `huggingface` | `huggingface.py` | `HF_TOKEN` env var | Free-tier HuggingFace Inference API; `pip install 'chew[huggingface]'` |
| `antigravity` | `antigravity.py` | `agy` session | Verified on invocation |

---

## 5. CLI Commands

All commands are in `src/chew/cli/main.py`. Each command has both an English name and a Korean alias.

| English | Korean | What it does |
|---|---|---|
| `summarize` | `요약` | Full digest with chapter and topic summaries |
| `blog` | `블로그` | Reassemble Knowledge Pack in blog voice |
| `study` | `학습` | Concepts, evidence, follow-up study material |
| `obsidian` | `옵시디언` | Index + topic notes with `[[wikilinks]]` |
| `status` | `상태` | Show run and job progress |
| `resume` | `이어하기` | Resume interrupted run |
| `doctor` | `진단` | Diagnose runtime installation; prints `→ Install: <cmd>` hints |
| `serve` | `서버` | Start FastAPI `/health` + `/readiness` server (needs `[server]` extras) |
| `storage` | `저장소` | Internal file count and usage |
| `cleanup` | `정리` | Preview or apply retention policy |
| `benchmark` | `벤치마크` | Reference-based quality benchmark; prints each condition/repeat before its live call, and `--short-video` resolves one raw snapshot before comparing Frontier paths |
| `benchmark-dashboard` | — | Generate `reports/trace_report.md` from OTel spans |

---

## 6. Key Protocols & Interfaces

### `Harness` protocol (`harness/base.py`)

```python
class Harness(Protocol):
    runtime_id: str
    async def generate(self, request: GenerationRequest) -> GenerationResult: ...
    def probe(self) -> HarnessProbe: ...  # availability + auth status
    def capabilities(self) -> HarnessCapabilities: ...
```

### `TranscriptProvider` protocol (`transcripts/base.py`)

```python
class TranscriptProvider(Protocol):
    async def fetch(self, source: SourceIdentity) -> Transcript: ...
```

### `GenerationRequest` / `GenerationResult` (`core/models.py` via `domain.py`)

```python
@dataclass
class GenerationRequest:
    task: str          # "topic_summary" | "chapter_summary" | "output_compose" | ...
    prompt: str
    schema: dict       # JSON schema the LLM must conform to
    runtime_id: str

@dataclass
class GenerationResult:
    content: str       # raw LLM output
    usage: dict[str, int]               # provider counts/durations when available
```

`TopicSummaryDraft` and `EvidenceCandidate` are untrusted model output. `ValidatedEvidenceRef` is created only by `pipeline/evidence.py` after matching the immutable raw transcript. `ExecutionPlan` is generated before the run and is immutable for its lifetime. It records routing, token budgets, normal runtime retries (2 attempts), and 429 recovery (3 attempts, a 60-second per-job budget, and a 5-second full-jitter cap); explicit resume starts a fresh in-memory 429 budget.

`OutputCompiler` renders every default profile from the persisted compatible pack and makes no
model request. Legacy strict schemas for `output_outline`, `output_compose`, and `output_verify`
remain only for compatibility and are not part of the default output path.

The maintainer preprocessing catalog (`benchmarks/videos.lock.json`) is parsed as `BenchmarkVideo`.
Every entry requires a stable key, YouTube ID, title, caption `language`, and verified duration;
measurement runners request the entry-specific language rather than applying a catalog-wide default.

### `ApplicationService.generate()` (`app/service.py`)

Entry point for the application layer. Catches `HarnessAuthenticationError` and re-raises as `AuthenticationRequired`.

### Agent tool policy (`agents/`)

```python
@runtime_checkable
class AgentTool(Protocol):
    name: str
    async def invoke(self, request: AgentToolRequest) -> AgentToolResult: ...

async def invoke_granted(
    tool: AgentTool,
    request: AgentToolRequest,
    grant: ToolGrant,
    *,
    approved: bool = False,
) -> AgentToolResult: ...
```

`AgentBudget` validates positive step/model/deadline limits. `ToolGrant` must name the
requested tool; disabled grants and approval-required grants without `approved=True` fail before
the tool runs. These are control-plane contracts only—not a LangGraph workflow or a provider tool.

### Inbound interface response (`interfaces/`)

```python
@dataclass(frozen=True, slots=True)
class InterfaceResponse:
    ok: bool
    data: Mapping[str, object] | None = None
    problem: InterfaceProblem | None = None

def command_result_data(result: CommandResult) -> dict[str, object]: ...
```

An `InterfaceResponse` is exactly one success (data, no problem) or failure (problem, no data).
`command_result_data()` preserves the existing CLI machine-result fields. It does not render a
Knowledge Pack; `pipeline.outputs.OutputCompiler` owns product content artifacts.

---

## 7. SQLite State Machine

Jobs go through these states (see `database.py`):

```
pending → claimed → completed
                  → failed_runtime   (topic jobs only — non-terminal, chapter still runs)
                  → failed           (chapter/output jobs — terminal)
blocked_auth      (authentication failure — resumable after login)
```

Key tables: `runs`, `jobs`, `job_measurements`, `artifacts`, `runtime_limits`. `runs.execution_plan_json` stores the policy snapshot; `job_measurements.details_json` includes the policy fingerprint when a plan is present.

`job_measurements` stores every generation attempt for a durable job, including repairs. For Ollama it records provider-reported input/output counts and available duration fields, plus request input/schema sizes and repair/retry flags. It does not infer provider billing.

Rate limiting: `note_rate_limit()` halves `current_limit`; 10 consecutive successes via `note_runtime_success()` restore it by 1. Scheduler 429 recovery follows the immutable execution-plan limits and ends a persistent provider rate limit as `failed_runtime` rather than returning a job to pending indefinitely.

---

## 8. Optional Extras Groups

| Extras | Installs | Needed for |
|---|---|---|
| `[youtube]` | `yt-dlp`, `youtube-transcript-api` | YouTube transcript fetching |
| `[whisper]` | `faster-whisper` | Local audio/video transcription |
| `[preprocess]` | `deepmultilingualpunctuation`, `sentence-transformers` | Optional punctuation restoration and semantic boundaries |
| `[telemetry]` | `opentelemetry-*` | OpenTelemetry Jaeger tracing |
| `[server]` | `fastapi>=0.111`, `uvicorn[standard]>=0.29` | `chew serve` health endpoints |
| `[huggingface]` | `huggingface_hub` | HuggingFace Inference API harness |
| `[dev]` | `pytest`, `ruff`, `mypy`, etc. | Development and testing |

---

## 9. Docs & Reports Index

| File | What it contains |
|---|---|
| `AGENTS.md` (= `CLAUDE.md` = `GEMINI.md`) | Core rules for AI agents; architecture layout; development guidelines |
| `docs/agent-index.md` | **This file** — LLM wiki; start here when orienting |
| `IMPROVEMENTS.md` | Active performance, quality, and safety work with adoption gates |
| `PRODUCT_ROADMAP.md` | Deferred product opportunities and their reconsideration conditions |
| `handoff.md` | Short, continuously refreshed execution index for new agent/session context |
| `docs/wiki/transcript-acquisition.md` | Durable transcript failures, provider decisions, and recovery rules |
| `docs/wiki/release-playbook.md` | Maintainer release sequence for version, branch, tag, changelog, benchmark, and CD alignment |
| `scripts/spike_token_baseline.py` / `src/chew/benchmark/metrics.py` | Maintainer-only raw-caption token baseline and pure measurement helpers; uses the locked videos and requires `yt-dlp` + `tiktoken` |
| `scripts/report_job_measurements.py` | Read-only SQLite run profiler for provider usage, request shape, repairs, and retries |
| `scripts/check_release_consistency.py` | Release guard that verifies `pyproject.toml`, release branch/tag, and `CHANGELOG.md` version headings agree before publishing |
| `scripts/check_architecture.py` | CI guard for high-risk architecture boundaries: core isolation, interface adapter access, and dependency-free agent contracts/policy/ports |
| `docs/decisions/local-llm-runtime.md` | Product decision: local LLM/Ollama is optional, with adoption criteria |
| `docs/decisions/README.md` | ADR index and criteria for adding architecture or operating decisions |
| `docs/decisions/0002-repository-governance.md` | Repository governance decision: release/version consistency, CHANGELOG scope, labels, PR/issue flow, and right-sized automation |
| `docs/superpowers/specs/2026-08-26-interface-and-agent-boundaries-design.md` | Approved boundary between app use cases, agent control contracts, content rendering, and inbound interfaces |
| `docs/superpowers/specs/2026-08-26-grounded-knowledge-compiler-modules-design.md` | Approved naming of `chew` as the Grounded Knowledge Compiler and future module dependency direction |
| `modules/intent-analysis/README.md` | Documentation-only boundary for reusable natural-language request analysis; not an installable package |
| `modules/research-engine/README.md` | Documentation-only boundary for Pack-based follow-up research; not an installable package |
| `CHANGELOG.md` | Feature history by version |
| `README.md` / `README.ko.md` | User-facing documentation (en/ko) |
| `reports/BENCHMARK.md` | Performance baseline and release benchmark scores |
| `reports/performance_analysis.md` | Baseline vs optimized commit comparisons |
| `reports/performance-comparisons/transcript-preprocessing/` | Maintainer preprocessing comparison reports and immutable run artifacts |
| `benchmarks/` | Maintainer-only benchmark scripts, `benchmark.sh report allInOne`, and locked transcript-preprocessing video fixtures; locks are reproducibility inputs, not product URL restrictions |
| `assets/architecture/en/` | English Mermaid + PNG user-flow, external-boundary, and internal-pipeline diagrams |
| `assets/architecture/ko/` | Korean Mermaid + PNG user-flow, external-boundary, and internal-pipeline diagrams |

---

## 10. When You Make a Change — Sync Checklist

| Change type | What to update |
|---|---|
| New CLI command or option | `cli/main.py` + command table in this doc (§5) + `README.md` + `README.ko.md` + `CHANGELOG.md` |
| New harness | `harness/<name>.py` + `registry.py` + `bootstrap.py` + harness table in this doc (§4) + `README.md` runtime table + `README.ko.md` + `CHANGELOG.md` + `assets/architecture/*.mmd` |
| New layer or module | Update layer map in this doc (§2) + `AGENTS.md` architecture layout + `CHANGELOG.md` |
| Activate a documentation-only future module | Select one user flow; define its typed dependency contract; update its module README, `IMPROVEMENTS.md`, `handoff.md`, `CHANGELOG.md`, and relevant user documentation before adding packages or dependencies |
| New inbound interface | Keep it behind `interfaces/`; update the relevant presenter/contract, architecture diagrams, README, and `CHANGELOG.md` |
| New extras group | `pyproject.toml` + optional extras table in this doc (§8) + `README.md` |
| Schema / protocol change | Update interfaces section in this doc (§6) |
| SQLite state change | Update state machine section in this doc (§7) |
| Release preparation | Align `pyproject.toml`, `release/vX.Y.Z`, `CHANGELOG.md`, tag, and GitHub Release; run `uv run python scripts/check_release_consistency.py --tag vX.Y.Z` before tagging |
| Architecture boundary rule | Update `scripts/check_architecture.py` and `tests/test_architecture_boundaries.py`, then document the rule in this index and `AGENTS.md` if it changes agent behavior |
