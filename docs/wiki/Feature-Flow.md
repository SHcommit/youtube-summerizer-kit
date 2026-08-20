# Feature Technical Flow

This page documents the internal technical flow for each major feature in `youtube-summarizer-kit (chew)`. It is auto-synced from `docs/wiki/Feature-Flow.md` in the main repository.

---

## Core Pipeline Flow

```
YouTube URL / Local Media
        ↓
[1] Source Identity & Reuse Check
    SHA-256 fingerprint → check SQLite for compatible Knowledge Pack
        ↓ (cache miss)
[2] Transcript Acquisition
    yt-dlp → YouTube Transcript API → faster-whisper (STT fallback)
        ↓
[3] Dynamic Segmentation
    Chapter-aware split → topic segmentation (5–10 min windows)
        ↓
[4] DAG Parallel Synthesis  ← AI Harness (8 concurrent workers)
    topic jobs → chapter jobs → Knowledge Pack job
        ↓
[5] Knowledge Pack (content-addressed, zstd-cached)
        ↓
[6] Output Assembly (1-sec reassembly from cache)
    Digest / Blog / Study Notes / Obsidian Vault
```

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

*Last updated: 2026-08-20 — covers Steps 5–9 (§7-3, §7-5, §7-6, §7-7, §2-3, §6-1, §9-5, §9-10, §9-11)*
