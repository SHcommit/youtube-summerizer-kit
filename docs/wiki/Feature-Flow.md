# Feature Technical Flow

This page documents the internal technical flow for each major feature in `youtube-summarizer-kit (chew)`. It is auto-synced from `docs/wiki/Feature-Flow.md` in the main repository.

---

## Core Pipeline Flow

The default and only runtime analysis path is the **Grounded Knowledge Compiler (GKT)**
(`pipeline/engine.py: AnalysisPipeline.analyze()`). See
[`Current-System.md`](Current-System.md) for the Default / Compatibility / Deferred status of
every flow named on this page.

```
YouTube URL / Local Media
        ↓
[1] Source Identity & Reuse Check
    SHA-256 fingerprint → check SQLite for compatible Knowledge Pack
        ↓ (cache miss)
[2] Transcript Acquisition
    yt-dlp → YouTube Transcript API → faster-whisper (STT fallback)
        ↓
[3] Input Compile
    Chapter-aware split → topic segmentation (5–10 min windows) → deterministic, reversible
    transcript preparation (`pipeline/input_compiler.py`)
        ↓
[4] Frontier Generate  ← AI Harness (8 concurrent workers)
    Strict, bounded extraction of untrusted knowledge tree drafts, internally scheduled as
    `topic_summary` → `chapter_summary` jobs (`pipeline/extraction.py`, `pipeline/scheduler.py`)
        ↓
[5] Evidence Ground
    Deterministic validation of every model-proposed transcript citation against the raw
    transcript — LLM citations are never trusted directly (`pipeline/evidence.py`)
        ↓
[6] Tree Assemble
    Grounding, assembly, and compatibility projection into the knowledge tree
    (`pipeline/tree.py`)
        ↓
[7] Knowledge Pack (content-addressed, zstd-cached)
        ↓
[8] Output Assembly (1-sec reassembly from cache)
    Digest / Blog / Study Notes / Obsidian Vault
```

The older `topic jobs → chapter jobs → Knowledge Pack job` description (no Input Compile or
Evidence Ground stage) no longer matches `pipeline/engine.py`. It survives only as a comparison
condition (`hierarchical()`) inside `benchmark/runner.py`, never as a live execution path — see
`Current-System.md`.

---

## Scheduler: asyncio.Event-Driven DAG (§2-3)

**Problem solved:** Previous scheduler used a busy-wait polling loop, wasting CPU cycles while jobs were in-flight.

**Flow:**

```
Scheduler.run()
  ├── launches worker coroutines (N = global_concurrency)
  └── main loop:
        claim_ready_jobs() → dispatch to workers
        asyncio.Event.wait()   ← sleeps until a worker signals completion
        worker finishes → Event.set() → main loop wakes
```

Workers signal via `asyncio.Event` push rather than being polled. This eliminates redundant wake cycles at idle and reduces CPU overhead on long pipelines.

---

## Partial Failure: Non-Terminal Topic Jobs (§7-3)

**Problem solved:** Previously a failing topic job aborted the entire run.

**Flow:**

```
Topic job fails
  ├── attempts < 2 → retry (exponential backoff + Full Jitter)
  └── attempts >= 2 → mark as "failed_runtime"

claim_ready_jobs() SQL:
  Chapter job becomes ready when ALL dependencies are
  either "completed" OR "failed_runtime"
  → Chapter runs with partial topic data
  → Run completes; failed_jobs count is reported
```

The chapter synthesizes from the topics that succeeded. The pipeline does not abort — failed topic jobs are non-terminal.

---

## Rate-Limit Recovery (§9-11-1)

The `runtime_limits` table tracks per-runtime concurrency. Rate-limit events halve the limit; streaks of successes restore it.

```
note_rate_limit(runtime_id)
  → current_limit = max(1, current_limit // 2)
  → success_streak = 0

note_runtime_success(runtime_id)
  → success_streak += 1
  → if success_streak >= 10:
        current_limit = min(ceiling, current_limit + 1)
        success_streak = 0
```

This implements token-bucket-style adaptive concurrency: aggressive ramp-down on quota hits, gradual recovery via sustained successes.

---

## Layered Ollama Harness (§7-7)

Routes each pipeline task type to the cheapest capable Ollama model tier, minimising GPU memory and latency for lightweight tasks.

```
task_type → tier
  "topic_summary"   → layer1 (qwen2.5:1.5b-instruct-q4_K_M)
  "repair"          → layer1
  "chapter_summary" → layer2 (qwen2.5:7b-instruct-q4_K_M)
  "output_outline"  → layer3 (qwen2.5:14b-instruct-q4_K_M)
  "output_compose"  → layer3
  "output_verify"   → layer3
  "compose"         → layer3
  (unknown)         → layer3  ← safe default
```

Model tags are pinned to reproducible `q4_K_M` quantized variants via module-level constants (`LAYER1_MODEL`, `LAYER2_MODEL`, `LAYER3_MODEL`) so model selection is stable across Ollama restarts and `ollama pull` updates.

---

## HuggingFace Harness (§7-6)

Free-tier hosted LLM inference via `huggingface_hub.AsyncInferenceClient`.

```
HuggingFaceHarness.generate(request)
  → build prompt from request.prompt + JSON schema instruction
  → AsyncInferenceClient.text_generation(model, prompt, max_new_tokens=...)
  → parse_json_object() extracts first valid JSON block from response
  → return GenerationResult(content=json_str)

Auth: HF_TOKEN env var (optional for public models, required for gated)
Install: pip install 'chew[huggingface]'
```

---

## FastAPI Health Server (§7-5)

`chew serve` starts a lightweight FastAPI app for infrastructure health checks.

```
GET /health
  → always 200 {"status": "ok"}

GET /readiness
  → probe database connectivity
  → 200 {"status": "ready",   "checks": {"database": "ok"}}
  → 503 {"status": "degraded","checks": {"database": "error: <msg>"}}

chew serve --host 0.0.0.0 --port 8080
  → uvicorn.run(create_app(database), host=host, port=port)
```

FastAPI and uvicorn are optional dependencies: `pip install 'chew[server]'`. The `create_app()` function raises an actionable `ImportError` with the install command if the extras are missing.

---

## Doctor Install Hints (§9-10)

`chew doctor` now prints `→ Install: <command>` when a runtime is not available.

```
_emit_diagnostics(runtime_id, available, ...)
  if not available and runtime_id in _INSTALL_HINTS:
      print(f"  → Install: {_INSTALL_HINTS[runtime_id]}")
```

Covered runtimes: `codex`, `gemini`, `ollama`, `layered_ollama`, `huggingface`, `antigravity`, `claude`.

---

## Auth Error Propagation Chain

```
Pipeline layer
  HarnessAuthenticationError("codex", "codex login")
        ↓
ApplicationService.generate()   [app/service.py:88-89]
  except HarnessAuthenticationError as exc:
      raise AuthenticationRequired(exc.runtime_id, str(exc)) from exc
        ↓
CLI layer
  except AuthenticationRequired:
      print login hint → exit code 2
```

This three-layer chain is verified end-to-end by `test_service_converts_harness_auth_error_to_authentication_required`.

---

## Exponential Backoff with Full Jitter (§6-1)

```python
async def _backoff_sleep(attempt: int, base: float = 1.0, cap: float = 60.0) -> None:
    slot = min(cap, base * (2 ** attempt))
    await asyncio.sleep(random.uniform(0, slot))
```

Full Jitter (0 to cap) prevents synchronized retries ("thundering herd") when multiple workers hit the same rate limit simultaneously.

---

*Last updated: 2026-08-20 — covers Steps 5–9 (§7-3, §7-5, §7-6, §7-7, §2-3, §6-1, §9-5, §9-10, §9-11) + AI Agent Integration Roadmap*

---

## Strategy 패턴 도입 배경 및 개선점 (2026-08-20)

### 계기

전처리 파이프라인(Phase 1)을 설계하면서 핵심 질문이 나왔다:

> "지금 설계가 더 나은 방식으로 바뀔 수 있잖아 — 그걸 쉽게 갈아낄 수 있는 구조로 하고 싶어."

이미 코드베이스 전체가 Strategy 패턴으로 설계되어 있었다:
- `Harness Protocol` → AI 런타임을 갈아낄 수 있는 구조
- `TranscriptProvider` → 자막 수집 방식을 갈아낄 수 있는 구조
- `BoundaryDetector` → 경계 탐지 알고리즘을 갈아낄 수 있는 구조

전처리도 같은 원칙을 따라야 일관된 아키텍처가 된다.

### 기존 방식 (하드코딩)

```python
# 변경 전 — 단계가 고정, 추가·교체 시 함수 내부를 직접 수정해야 함
def preprocess_transcript(transcript):
    transcript = _remove_fillers(transcript)
    transcript = _restore_punctuation(transcript)   # 항상 호출됨
    transcript = _detect_boundaries(transcript)     # 항상 호출됨
    return transcript
```

문제:
- 새 전처리 방법이 생기면 함수 내부를 수정해야 함 (Open/Closed Principle 위반)
- 의존성 없이는 단계가 실패하거나 try/except로 감싸야 함
- 테스트 시 특정 단계만 격리하기 어려움
- 순서 변경, A/B 테스트, 사용자 설정이 어려움

### Strategy 패턴 적용 후

```python
class PreprocessingStrategy(Protocol):
    def available(self) -> bool: ...   # 의존성 체크
    def process(self, t: Transcript) -> Transcript: ...

class TranscriptPreprocessor:
    def __init__(self, strategies: list[PreprocessingStrategy] | None = None):
        self.strategies = strategies or [
            FillerRemovalStrategy(),    # 항상 available
            PunctuationStrategy(),      # deepmultilingualpunctuation 설치 시
            SemanticBoundaryStrategy(), # sentence-transformers 설치 시
        ]
```

### 개선된 점

| 항목 | 기존 | Strategy 패턴 |
|---|---|---|
| 새 전처리 추가 | 함수 내부 수정 | 새 클래스 작성 후 목록에 추가 |
| 의존성 미설치 | try/except 산재 | `available()` 한 곳에서 관리 |
| 단계 순서 변경 | 코드 수정 | 목록 순서만 바꾸면 됨 |
| 특정 단계 테스트 | 전체 실행 | 전략 인스턴스 하나만 테스트 |
| CHEW.md 설정 | 불가 | 전략 목록을 설정으로 주입 가능 |
| A/B 테스트 | 불가 | 다른 전략 목록으로 `TranscriptPreprocessor` 생성 |

### 미래에 갈아낄 수 있는 것들

```python
# 지금
TranscriptPreprocessor([
    FillerRemovalStrategy(),
    PunctuationStrategy(),
    SemanticBoundaryStrategy(),
])

# 나중에 — 더 좋은 방식이 나오면 목록만 교체
TranscriptPreprocessor([
    FillerRemovalStrategy(),
    WhisperPunctuationStrategy(),      # Whisper 기반 더 정확한 복원
    SpeakerDiarizationStrategy(),      # 화자 분리 추가
    TopicShiftDetectionStrategy(),     # GPT-4o mini 기반 토픽 전환 탐지
])
```

기존 코드를 건드리지 않고 새 전략 클래스만 작성하면 된다.

### 결론

Strategy 패턴은 단순히 코드를 정리하는 게 아니라 **"설계가 바뀌어도 비용이 최소화되는 구조"** 를 만드는 것이다. `chew`의 핵심 가치인 느슨한 결합(Ports & Adapters)과 완전히 일치하는 방향이다.

---

## AI Agent Integration Vision (Phase 6–8)

### Why the Harness Architecture Enables This

The harness system was designed with Protocol-based abstraction so any BYOK runtime can be swapped without touching pipeline logic. This same abstraction makes `chew` composable as a tool for other systems:

```
Current:  $ chew summarize 'https://youtu.be/...'

Future:
  Claude Code → MCP tool call → chew_analyze(url) → Obsidian auto-save
  Zapier/n8n  → YouTube new video trigger → POST /analyze → Notion DB update
  Python app  → from chew import analyze; result = await analyze(url)
  AI Agent    → "Analyze 10 AI videos and extract common insights"
               → chew × 10 → Knowledge Graph → report
```

### Phase 6: Python Library API

`ApplicationService` is already the single use-case entry point. The library wraps it:

```python
from chew import analyze, analyze_sync

# async
result = await analyze("https://youtu.be/VIDEO_ID", runtime="codex", depth=3)
print(result.text)           # formatted output
print(result.knowledge_pack) # structured KnowledgePack

# sync wrapper for scripting
result = analyze_sync("https://youtu.be/VIDEO_ID")
```

`AnalysisResult` exposes: `text`, `knowledge_pack`, `stats` (token savings), `run_id`.

### Phase 7: MCP Server

`chew serve --mcp` exposes three tools to any MCP-compatible agent:

| Tool | Description |
|---|---|
| `chew_analyze(url, runtime)` | Analyze a video; returns Knowledge Pack |
| `chew_list()` | List locally cached Knowledge Packs |
| `chew_get(run_id, format)` | Reassemble existing pack in a new format |

MCP config example (`~/.claude/mcp_servers.json`):
```json
{
  "chew": {
    "command": "chew",
    "args": ["serve", "--mcp"]
  }
}
```

Install: `pip install 'chew[mcp]'`

### Phase 8: n8n / Zapier Automation

`chew serve` REST API becomes the automation endpoint:

```
POST /analyze  → 202 Accepted + run_id
GET  /runs/{id} → 200 completed + text + knowledge_pack
```

Automation scenario examples:

| Trigger | Action | Result |
|---|---|---|
| YouTube channel new video (RSS) | `POST /analyze` | Notion DB auto-update |
| Podcast RSS new episode | `POST /analyze` | Obsidian Vault auto-append |
| Slack link shared | `POST /analyze` | Summary posted to thread |

No additional dependencies beyond Phase 6 REST API completion.
