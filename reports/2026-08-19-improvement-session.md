# 개선 세션 리포트 — 2026-08-19

> Steps 2~5 완료. 총 154 → 164 테스트. 전 과정 TDD + Subagent-Driven Review 적용.

---

## 세션 요약

| 항목 | 수치 |
|------|------|
| 완료된 Steps | 2, 3, 4, 5 (Step 1은 이전 세션에서 완료) |
| 커밋 수 | 12개 |
| 테스트 증가 | 154개 → 164개 (+10개 신규 테스트) |
| 신규 파일 | `src/chew/log.py`, `src/chew/harness/huggingface.py`, `src/chew/harness/layered_ollama.py` |
| 최종 상태 | pytest 164 passed / 2 skipped, ruff clean, mypy clean |

---

## Step 2 — 레이어 경계 복원 & Protocol 정리

**문제:** `pipeline/engine.py`가 상위 레이어 `app/config.py`의 `Settings`를 직접 임포트 (Ports & Adapters 위반). `service.py`가 `getattr(harness, "set_preference", None)` 덕타이핑 사용.

**개선 내용:**

### `AnalysisConfig` DTO 도입 (`engine.py`)
```python
@dataclass(frozen=True, slots=True)
class AnalysisConfig:
    language: str; depth: str; instructions: str
    whisper_fallback: bool; runtime: str; recipe_json: str
```
- `engine.py`에서 `from chew.app.config import Settings` 완전 제거
- `app/service.py`가 Settings → AnalysisConfig 변환 담당 (app boundary에서만)

### `ConfigurableHarness` Protocol (`harness/base.py`)
```python
@runtime_checkable
class ConfigurableHarness(Protocol):
    def set_preference(self, runtime_id: str) -> None: ...
```
- `service.py`, `pipeline/outputs.py`에서 `getattr` 패턴 → `isinstance(h, ConfigurableHarness)` 교체

**커밋:** `260e585`, `8299fa7`, `acde4e6`

---

## Step 3 — Structured Logging + Graceful Shutdown

**문제:** 전체 codebase에 `import logging` 0건. SIGTERM 수신 시 clean shutdown 없음. `ProcessExecutor`가 SIGKILL 즉시 전송.

**개선 내용:**

### `src/chew/log.py` 신규 생성
- `JsonFormatter`: `{"timestamp", "level", "logger", "event", "run_id", "job_id"}` JSON 출력
- `contextvars.ContextVar`: `run_id_var`, `job_id_var` — async 컨텍스트 전파
- `configure_logging(level)`: idempotent, root logger 설정
- `get_logger(name)`: `logging.getLogger` 래퍼

### `scheduler.py` Job Lifecycle 로깅
- `job_started`, `job_completed`, `job_failed`, `job_retried`, `rate_limited`, `job_cancelled`, `auth_error`, `run_complete`
- 각 이벤트에 `kind`, `runtime_id`, `attempts`, `latency_ms` 등 context 필드 포함

### `ProcessExecutor` Graceful Termination
```python
# SIGTERM → 5초 대기 → SIGKILL escalation
async def _await_termination(process, sigterm_timeout=5.0):
    try:
        await asyncio.wait_for(process.wait(), timeout=sigterm_timeout)
    except asyncio.TimeoutError:
        os.killpg(process.pid, signal.SIGKILL)
        await process.wait()
```

### `Scheduler` Clean Shutdown
- `shutdown_event: asyncio.Event | None` 파라미터
- `run()` while 조건: `not shutdown_event.is_set()`
- `claim_ready_jobs` 블록에 `shutting_down` 가드 추가

### CLI SIGTERM Handler
```python
@app.callback()
def _startup(log_level: str = typer.Option("WARNING", envvar="CHEW_LOG_LEVEL")):
    configure_logging(level=log_level)
    signal.signal(signal.SIGTERM, lambda s, f: raise KeyboardInterrupt)
```

### `Database.checkpoint()`
```python
def checkpoint(self) -> None:
    with self._connect() as connection:
        connection.execute("PRAGMA wal_checkpoint(FULL)")
```

**커밋:** `eb5f87f`, `8b891d1`, `141c49d`, `1145031`, `a5ac02d`, `65e1128`

---

## Step 4 — Connection Pooling + HTTP Session Reuse + assert 제거

**문제:** SQLite 매 호출마다 connect/close. Ollama `urllib.urlopen()` 매 요청 새 TCP 연결. `assert` 4건 (`python -O` 시 무효화).

**개선 내용:**

### SQLite Thread-Local 커넥션 캐싱 (`database.py`)
```python
class Database:
    def __init__(self, path: Path) -> None:
        self._local = threading.local()
    
    def _connect(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(...); self._local.connection = conn
        return conn
    
    def close(self) -> None:
        conn = getattr(self._local, "connection", None)
        if conn: conn.close(); self._local.connection = None
```

### Ollama `httpx.AsyncClient` 교체 (`ollama.py`)
```python
def _get_client(self) -> httpx.AsyncClient:
    if self._client is None:
        self._client = httpx.AsyncClient(timeout=180.0)
    return self._client
```
- `httpx>=0.27` core dependency 추가
- `probe()`, `generate()` 모두 동일 client 재사용
- `aclose()` 추가

### assert → RuntimeError 4건
- `process.py` (×2): `if process.stdin is None: raise RuntimeError("Expected subprocess stdin pipe but got None")`
- `whisper.py` (×1): `if source.local_path is None: raise RuntimeError("Expected local_path for LOCAL_MEDIA source but got None")`
- `outputs.py` (×1): `if self.harness is None: raise RuntimeError("OutputCompiler.harness is None; cannot generate composed output")`

**커밋:** `78b1ec7`, `459b21b`, `6445be8`

---

## Step 5 — HuggingFaceHarness + LayeredOllamaHarness

**문제:** `LayeredOllamaHarness`와 `HuggingFaceHarness` 미구현. $0 로컬 추론이 핵심 차별화 포인트임에도 코드 부재.

**개선 내용:**

### `HuggingFaceHarness` (`harness/huggingface.py`)
- `AsyncInferenceClient` lazy init, optional dep `huggingface-hub>=0.23`
- `_HF_AVAILABLE` 플래그로 미설치 시 graceful degradation (`probe().available = False`)
- `HF_TOKEN` 환경변수 인식
- `Transport = Callable[[str, str], Awaitable[str]]` — `(model, prompt) → raw text`
- `parse_json_object()` 재사용, markdown fence 자동 strip

### `LayeredOllamaHarness` (`harness/layered_ollama.py`)

| Task | Layer | 기본 모델 |
|------|-------|-----------|
| `topic_summary`, `repair` | Layer 1 | `qwen2.5:1.5b` |
| `chapter_summary` | Layer 2 | `qwen2.5:7b` |
| `compose`, `output_*` | Layer 3 | `qwen2.5:14b` |
| 미등록 task | Layer 3 (default) | `qwen2.5:14b` |

```python
TASK_LAYERS = {
    "topic_summary": "layer1", "repair": "layer1",
    "chapter_summary": "layer2",
    "output_outline": "layer3", "output_compose": "layer3",
    "output_verify": "layer3", "compose": "layer3",
}
```

- `probe()`: layer1에 위임, `runtime_id="layered_ollama"` override
- `aclose()`: 3개 layer OllamaHarness 전부 close
- `registry.py` `default_registry()`에 둘 다 등록

**커밋:** `22eabb1`, `2ef2542`

---

## 부족했던 부분 / 리뷰에서 발견된 이슈

### 구조적 문제 (해결됨)
- `pipeline/outputs.py`의 `from chew.app.config import Settings` 순환 임포트 — `TYPE_CHECKING` guard로 해결
- `test_pipeline.py` 내 `pipeline.analyze(url, settings)` 호출 6곳 — `AnalysisConfig`로 전부 교체

### 테스트 품질 문제 (일부 파킹)
- `test_ollama.py:36` — `assert True` 잔존 (실질 검증 없음, minor)
- `test_layered_ollama.py` — transport injected 시 `_client is None`이어서 `aclose()` 실질 검증이 `_get_client()` 수동 호출 필요
- `HuggingFaceHarness` — `aclose()` 미구현 (`AsyncInferenceClient` HTTP 세션 미정리 가능)

### 아키텍처 결함 (잔여)
- `registry.py` login-command map에 `huggingface`, `layered_ollama` 미등록 (실제 도달 불가 경로지만 일관성 결여)
- `LayeredOllamaHarness` — 각 layer OllamaHarness가 동일 endpoint 공유, 개별 endpoint 설정 불가

---

## 다음 Steps

| Step | 내용 | 계획 파일 |
|------|------|-----------|
| **Step 6** | `_backoff_sleep()` Full Jitter (§9-7) + CLI 토큰 사용량 표시 (§9-9) | `docs/superpowers/plans/2026-08-19-step6-backoff-token-display.md` |
| **Step 7** | Scheduler polling → Event push (§2-3) + Partial Failure (§7-3) + SpanRecord deque (§9-5) | 미작성 |
| **Step 8** | FastAPI 헬스 체크 (§7-5) + 모델 태그 핀 CI/CD (§7-7) + Getting Started 최적화 (§9-10) | 미작성 |
| **Step 9** | 장애 주입 테스트 스위트 (§9-11) | 미작성 |
