# `youtube-summarizer-kit` 아키텍처 & 코드베이스 개선 과제 (Technical Debt & Roadmap)

> 본 문서는 구글 10년차 시니어 IT/백엔드/자동화 엔지니어 관점의 코드 리뷰와 유명 GitHub 오픈소스(Fabric, Summarize 등) 분석 결과를 바탕으로 작성된 개선 과제 및 기술 로드맵 목록입니다.

---

## 1. 🔴 Critical (운영 신뢰성 및 관측성 개선)

### 1-1. `telemetry.py` 전역 싱글턴 패턴 개선
- **현상**: 모듈 레벨 전역 객체 `telemetry = TelemetryManager()` 사용으로 인해 단위/통합 테스트 간 Span 수집 데이터가 오염되거나 병렬 실행 시 Race Condition 발생 가능성 존재.
- **개선안**: `ContextVar`를 활용한 컨텍스트별 격리 처리 또는 Dependency Injection(DI) 형태로 Service/Pipeline 객체 전달 체계 구축.

### 1-2. `telemetry.py` 리포트 하드코딩 수치 및 Dead Code 제거 (1차 조치 완료)
- **현상**: 마크다운 리포트 생성 로직 내 벤치마크 비교 수치("8 workers", "16.3x speedup")가 하드코딩되어 있었으며, `return`문 뒤에 약 190줄의 미사용 HTML 생성 코드가 잔재했음.
- **개선안**: HTML dead code 삭제 완료. 실시간 기록된 `SpanRecord`로부터 메트릭을 동적 집계하는 리포터로 1차 개편 완료 및 테스트 반영.

---

## 2. 🟠 High (계층적 의존성 위반 & 타입 안전성 훼손)

### 2-1. Pipeline Layer의 App Config 직접 의존성 제거
- **현상**: `src/chew/pipeline/engine.py`가 상위 레이어인 `src/chew/app/config.py`의 `Settings` 객체를 직접 임포트하여 사용 (`AGENTS.md` 레이어 의존 규칙 위반).
- **개선안**: Pipeline 독립적 런타임 옵션 DTO(예: `AnalysisConfig`)를 정의하거나 파라미터 직접 전달로 고립시켜 Ports & Adapters 아키텍처 순수성 복원.

### 2-2. `service.py` 내 `getattr` 기반 덕타이핑 계약 위반 해소
- **현상**: `ApplicationService`가 `Harness` Protocol 표준 인터페이스에 정의되지 않은 `set_preference` 메서드를 `getattr`로 동적 탐색하여 호출함.
- **개선안**: `AutoHarness` 전용 인터페이스/Protocol(예: `ConfigurableHarness`)을 별도로 명시하거나, Harness 관리 구성을 정식 메소드로 확장.

### 2-3. `scheduler.py` 무한 Polling Busy-Wait 제어 개선
- **현상**: 작업 큐 처리 대기 시 `await asyncio.sleep(0.005)` (5ms) 고정 인터벌 폴링을 수행하여 DB 및 CPU 스핀 락 유사 자원 소모 발생.
- **개선안**: `asyncio.Event` 또는 작업 전파 채널 기반의 Push 기반 알림 구조로 전환하여 불필요한 SQLite 쿼리 낭비 제거.

---

## 3. 🟡 Medium (성능, DB 관리 및 코드 견고성)

### 3-1. `database.py` 매 메서드 호출 시 Connection 생성 Overhead 개선
- **현상**: SQLite 호출 메서드마다 `_connect()`를 통해 데이터베이스 커넥션을 매번 열고 닫음.
- **개선안**: thread-local 커넥션 캐싱 또는 커넥션 획득 컨텍스트 매니저 도입으로 SQLite 연결/해제 시스템 콜 오버헤드 축소.

### 3-2. SQLite 스키마 마이그레이션 정식 체계 도입
- **현상**: `SCHEMA_VERSION = 4` 상태이나, `initialize()`에서 테이블 칼럼 존재 유무(`if "request_key" not in columns:`)를 수동 검사하여 ALTER TABLE을 수행함.
- **개선안**: 버전별 명시적 마이그레이션 스크립트 실행 구조 또는 마이그레이션 이력 테이블 도입.

### 3-3. Production 코드 내 `assert` 문을 명시적 예외 처리로 전환
- **현상**: `process.py` 등 일부 모듈에서 `assert process.stdin is not None`과 같이 Python `assert` 구문 사용. (`python -O` 최적화 모드 시 무효화)
- **개선안**: `if process.stdin is None: raise RuntimeError(...)` 형태로 명시적 에러 검증.

### 3-4. CLI 인증 명령어 매핑 중복 정의 단일화
- **현상**: `registry.py`와 `builtin.py` 두 곳에 CLI 런타임별 로그인 명령 맵(`{"codex": "codex login", ...}`)이 이중 관리됨.
- **개선안**: 각 Harness 구현체 클래스 속성(`login_command`)으로 캡슐화 및 단일 출처화.

### 3-5. 예외 및 장애 복구 테스트 커버리지 강화
- **현상**: 현재 테스트 체계는 정상 분석/성공 케이스 캐싱 중심.
- **개선안**: 
  - LLM Rate Limit 시 `AdaptiveLimiter` 동시성 감소 및 recovery 테스트
  - Worker Lease 만료 시 다른 Worker의 Job 재탈취(Lease takeover) 동작 검증
  - `HarnessAuthenticationError` 발생 시 스케줄러 터미널 중단 흐름 검증

---

## 4. 🔵 Low (코드 정돈 및 도메인 명확성)

### 4-1. `segmentation.py` 파라미터 비교부 하드코딩 제거
- **현상**: `coalesce_chapters` 함수 내 `depth` 비교 시 Settings Pydantic 모델 범위 외의 하드코딩된 한국어 키워드("초간단", "핵심", "꽉찬" 등) 조건 잔재.
- **개선안**: Pydantic Enum/Literal 정의와 1:1 일치시키고 매핑 구조체 분리.

### 4-2. 언어 매칭 가시성 개선
- **현상**: `transcripts/service.py` 내 `cand_base in ("ko", "en", "ja")` 형태의 암묵적 특정 언어 허용 로직에 대한 설명 부족.
- **개선안**: 도메인 사유 주석 명시 및 관련 정책을 상수로 분리.

---

## 5. 💡 오픈소스 경쟁력 분석 기반 제품/기능 개선점 (Fabric, Summarize 벤치마크)

### 5-1. 사용자 커스텀 프롬프트 패턴(Pattern) 시스템
- **배경**: `danielmiessler/fabric` 오픈소스의 핵심 성공 요인은 사용자가 자유롭게 `extract_wisdom`, `summarize_paper` 등 목적별 프롬프트를 확장할 수 있는 Pattern 커뮤니티 구조.
- **개선안**: `~/.chew/patterns/` 경로 내 Markdown Front-matter 기반 사용자 프롬프트 템플릿 추가 및 `--pattern=tech-interview` 지원 플러그인 체계 구축.

### 5-2. 의미 기반 세그멘테이션 (Semantic Chunking)
- **배경**: 현재 타임스탬프 5분 단위와 문장부호 기준 분할 방식은 장시간 대화형 영상에서 화자의 맥락이 단절될 수 있음.
- **개선안**: 임베딩 유사도 변곡점 탐지 또는 슬라이딩 윈도우 기반 세만틱 경계 추출 알고리즘 도입.

### 5-3. 음성 미디어 Whisper 오디오 병렬 처리 (VAD Chunking)
- **배경**: 자막이 없는 YouTube 영상이나 로컬 오디오 처리 시 단일 통파일 인퍼런스로 시간 소요 과다.
- **개선안**: VAD(Voice Activity Detection) 기반 오디오 슬라이싱 후 멀티코어 병렬 Whisper 트랜스크립션 Pipeline 구현.

---

## 6. 🚀 100% 무료 (Free $0) HuggingFace & 경량 오픈 모델 Layered 아키텍처 전략

### 6-1. 계층별 (Layered) 모델 라우팅 구조
- **개념**: 사용자 OS 자원(CPU/GPU/Ollama)을 활용하여 DAG 노드별 작업 난이도에 따라 오픈 모델을 차등 배치함으로써 API 비용 $0 달성.
- **파인튜닝 모델 활용**: Hugging Face에 공개된 이미 요약/Chat 파인튜닝 및 GGUF 양자화(Q4_K_M)가 완료된 검증 모델들(`Qwen2.5-Instruct`, `Llama-3.2-Instruct`)을 즉시 적용.

| 계층 (Layer) | 담당 DAG Job Kind | 추천 오픈 파인튜닝 모델 | 모델 크기 | 자원 요구량 |
| :--- | :--- | :--- | :--- | :--- |
| **Layer 1 (Map)** | `topic` (소주제 요약 및 팩트 추출) | **Qwen2.5-1.5B-Instruct** / Llama-3.2-3B | 1.5B ~ 3B | RAM 1.5GB ~ 3GB |
| **Layer 2 (Combine)** | `chapter` (소주제 묶음 합성) | **Qwen2.5-7B-Instruct** / Llama-3.1-8B | 7B ~ 8B | RAM 4.5GB ~ 6GB |
| **Layer 3 (Reduce)** | `compose` (전체 통찰/종합 작성) | **Qwen2.5-14B-Instruct** 또는 Groq/Gemini Free | 14B ~ 32B | RAM 8GB ~ 18GB (또는 Cloud Free API) |

### 6-2. `LayeredOllamaHarness` 및 스케줄러 바인딩 구현 방안
- **어댑터 구조**: `Harness` Protocol을 만족하는 계층형 오프라인 하네스 도입.
- **비용/속도 이점**:
  - 100% 사용자 OS(Mac M1~M4, 일반 PC GPU)에서 로컬 추론 실행 ➔ 개발자 및 사용자 모두 **서버/API 비용 0원**.
  - 80% 이상의 노드(`topic`)를 1.5B 초경량 모델로 구동하여 초당 100+ 토큰의 극단적 속도 향상.

---

## 7. ⚙️ Agentic Harness 9축 기반 프로덕션 운영 & UX 고도화 과제 (Operational & UX Architecture)

### 7-1. API 키 사용 및 BYOK (Bring Your Own Key) 비용 구조 명확화
- **기본 개념**: 개발사(우리)가 API 비용을 부담하는 중앙 서버 방식이 아니라, **사용자 로컬 자원($0)** + **BYOK (Bring Your Own Key)** 구조.
- **작동 원리**:
  - **Layer 1 & 2 (1.5B/7B 로컬 SLM)**: 사용자 로컬 OS (Ollama/vLLM) 실행 ➔ **API 키 불필요, 비용 $0**.
  - **Layer 3 (최종 합성 거대 LLM)**: 사용자의 개인 API Key (`OPENAI_API_KEY`, `GEMINI_API_KEY`) 사용.
- **웹 서비스 확장 시**:
  - 사용자가 웹 UI 상에 자신의 API Key를 등록하여 소비(BYOK)하거나, 서버가 로컬 모델(vLLM)로 무료 처리하도록 유연한 라우팅 제공.

### 7-2. CLI 실시간 BYOK 토큰 절감률 표시 (Token Savings Indicator)
- **현상**: 토큰 절감 파이프라인이 동작하더라도 CLI 사용자는 자신이 얼마의 비용을 아꼈는지 체감할 수 없음.
- **개선안**: 파이프라인 수행 완료 시 또는 `SLOMonitor` 통계 집계 시 CLI에 실시간 토큰 절감 지표 출력:
  ```bash
  📊 [BYOK Token Economy]
  - Raw Transcript Tokens : 48,500 tokens (Single LLM Baseline)
  - Layer 1/2 Local SLM   : 45,200 tokens processed locally ($0)
  - Layer 3 BYOK Consumed : 3,300 tokens
  - 💰 BYOK Token Saved   : 93.2% (45,200 / 48,500 tokens saved!)
  ```

### 7-3. 부분 실패 (Partial Failure) 허용 및 Graceful Degradation
- **현상**: 현재 `scheduler.py`는 단 1개 노드(`topic`)라도 최종 실패할 경우 `terminal_error`를 발생시켜 전체 파이프라인 중단 (All-or-Nothing).
- **개선안**:
  - `topic` 노드 40개 중 2~3개 실패 시, 전체 중단 대신 **실패 노드 격리 스킵(Partial Skip)** 및 사용 가능한 나머지 `topic` 결과를 바탕으로 `chapter` / `compose` 계속 진행.
  - 최종 결과물 마크다운 상단에 `⚠️ 일부 소주제(2개) 분석 실패로 인한 부분 요약 결과입니다` 경고 배너 삽입.

### 7-4. 프로덕션 Structured Logging (JSON Context) 전면 도입
- **현상**: 전체 코드베이스에 `logging` 모듈 미적용 상태. 에러 발생 시 콘솔 Traceback만 터미널에 노출되어 모니터링 툴(Datadog, CloudWatch, Loki) 연동 불가.
- **개선안**: `structlog` 또는 Python 표준 `logging` 기반의 JSON 구조화 로거 도입:
  ```json
  {"timestamp": "2026-08-19T02:59:00Z", "level": "INFO", "run_id": "run-123", "job_id": "job:topic:01", "model": "qwen2.5:1.5b", "latency_ms": 420, "event": "job_completed"}
  ```

### 7-5. 헬스 체크 (Health Check) & 리디니스 프로브 구현
- **배경**: 웹 서비스(FastAPI) 및 로컬 데몬 구동 시 Ollama/vLLM 인퍼런스 서버 및 DB 연결 생존 여부를 주기적으로 점검해야 함.
- **개선안**:
  - `/health`: 프로세스 핑 및 SQLite 접근 확인.
  - `/readiness`: Ollama HTTP API (`/api/tags`) 헬스체크 및 지정 모델(`qwen2.5:1.5b`) 로드 여부 검증.

### 7-6. Graceful Shutdown & 자원 정리 자동화
- **현상**: SIGINT(Ctrl+C) 또는 SIGTERM 수신 시 진행 중이던 HTTP 요청(Ollama) 및 Worker DB Lease가 유휴 상태로 남아 락 형성.
- **개선안**:
  - `signal.signal(SIGINT/SIGTERM)` 핸들러 등록.
  - 진행 중인 비동기 Task 취소(`task.cancel()`), Ollama HTTP 세션 Graceful Close, DB Worker Claim 해제 및 WAL flush 자동화.

### 7-7. 모델 태그 버전 관리 및 CI/CD 자동화 (Model Tag Pinning)
- **현상**: 단순 `qwen2.5:1.5b` 사용 시 오프라인 환경이나 Ollama 모델 태그 업데이트 시 불일치 발생 가능.
- **개선안**:
  - `qwen2.5:1.5b-instruct-q4_K_M`과 같이 양자화 포맷 및 버전 명시적 핀(Pinning).
  - GitHub Actions CI/CD에 Ollama 셋업 및 경량 모델 로드 가능 여부 자동 통합 테스트 린트 단계 추가.

---

## 9. 🔥 20년차 Google Staff Engineer / CEO 관점 운영 성숙도 평가 기반 추가 과제

> 본 섹션은 코드베이스 전체 심층 감사(2026-08-19) 결과 발견된 **프로덕션 운영 준비도(Operational Readiness)** 결함을 기반으로 작성되었습니다.

### 9-1. 🔴 Structured Logging 전면 도입 (Python `logging` 모듈 0건 사용)
- **현상**: 전체 `src/chew/` 소스에서 `import logging` 구문이 **단 한 건도 없음**. 에러 발생 시 Python traceback만 터미널에 노출되어 Datadog, CloudWatch, Loki 등 모니터링 시스템 연동이 원천적으로 불가.
- **심각도**: 🔴 Critical — 엔터프라이즈 환경 도입 차단 요인
- **개선안**:
  - `structlog` 또는 Python 표준 `logging` + JSON formatter 도입
  - 모든 harness 호출, scheduler 이벤트, DB 연산에 `run_id`, `job_id`, `runtime_id` 컨텍스트 필드 포함
  - 로그 레벨 정책: `DEBUG`(개발), `INFO`(운영), `WARNING`(degradation), `ERROR`(실패)
  - 출력 형식: `{"timestamp": "...", "level": "INFO", "run_id": "...", "job_id": "...", "model": "...", "latency_ms": 420, "event": "job_completed"}`

### 9-2. 🔴 Graceful Shutdown 라이프사이클 구현 (SIGINT/SIGTERM 핸들러 부재)
- **현상**: `grep -r "signal.signal" src/chew/` 결과 **핸들러 등록 0건**. `process.py`의 `signal.SIGKILL` 전송만 존재하며, 이는 자식 프로세스를 graceful 종료 없이 즉시 강제 종료함.
- **영향**:
  - Ctrl+C 시 Ollama HTTP 요청 중단 불완전
  - Worker DB Lease가 해제되지 않아 다음 실행 시 lease 충돌
  - SQLite WAL flush 미보장으로 데이터 유실 가능
- **개선안**:
  - `signal.signal(SIGINT/SIGTERM)` 핸들러 등록
  - `ProcessExecutor._terminate()`: SIGTERM → 5초 대기 → SIGKILL escalation 패턴 적용
  - 스케줄러 `run()` 메서드에 `shutdown_event: asyncio.Event` 주입하여 진행 중 task의 clean cancellation 보장
  - DB worker claim 해제 및 WAL checkpoint 자동화

### 9-3. 🔴 SQLite 커넥션 풀링 / 재사용 구현 (매 메서드 호출 시 Connect/Close)
- **현상**: `database.py`의 모든 public 메서드가 `_connect()`를 호출하여 매번 새 `sqlite3.Connection` 생성 후 파괴. 스케줄러 루프 1회 반복 당 최소 3-4회 커넥션 생성/파괴 발생.
- **성능 영향**: topic 40개 처리 시 수백 회의 불필요한 PRAGMA 설정 + 시스템 콜 오버헤드
- **개선안**:
  - `threading.local()` 기반 thread-local 커넥션 캐싱
  - 또는 `contextlib.contextmanager` 기반 커넥션 획득/반환 패턴
  - 커넥션 수명 관리: 최대 idle 시간 설정 후 자동 재연결

### 9-4. 🔴 Ollama HTTP 세션 재사용 (매 요청 새 TCP 연결)
- **현상**: `ollama.py`의 `_transport()` 메서드가 `urllib.request.urlopen()`으로 매 API 호출마다 새 TCP 연결 생성. HTTP Keep-Alive, 커넥션 풀링 미적용.
- **개선안**:
  - `aiohttp.ClientSession` 또는 `httpx.AsyncClient`로 교체
  - `TCPConnector(limit=max_concurrency)` 기반 커넥션 풀 설정
  - 세션 수명을 `OllamaHarness` 인스턴스에 바인딩하고 `async with` 패턴으로 자원 관리

### 9-5. 🟠 SpanRecord 무한 축적 메모리 누수 방지
- **현상**: `telemetry.py` L87의 `self.spans.append(record)`가 프로세스 수명 동안 모든 span을 리스트에 무한 축적. 장시간 배치 실행 시 메모리 증가.
- **개선안**:
  - Ring buffer 또는 최대 span 수 제한 (`maxlen=10000`)
  - 주기적 flush/export 후 리스트 초기화
  - 또는 `collections.deque(maxlen=N)` 적용

### 9-6. 🟠 Production `assert` 문 → 명시적 예외 전환 (4건 잔존)
- **현상**: `process.py` (2건), `whisper.py` (1건), `outputs.py` (1건)에서 `assert` 구문 사용. `python -O` 최적화 모드에서 검증이 사라짐.
- **개선안**: `if X is None: raise RuntimeError("...")` 형태로 4건 전환

### 9-7. 🟠 Exponential Backoff with Jitter 적용
- **현상**: `scheduler.py` L150의 rate limit 재시도 대기가 `error.retry_after` (고정 1.0초)만 사용.
- **개선안**: `min(base * 2^attempt + random_jitter, max_backoff)` 패턴 적용. AWS 표준 "Full Jitter" 알고리즘 권장.

### 9-8. 🟡 HuggingFace Inference API / vLLM 하네스 어댑터 구현
- **현상**: §6에 계획된 `LayeredOllamaHarness`가 미구현 상태. $0 로컬 추론이 핵심 차별화 포인트임에도 코드 부재.
- **개선안**:
  - `HuggingFaceHarness`: `huggingface_hub.InferenceClient` 기반 무료 Inference API 연동
  - `LayeredOllamaHarness`: DAG job kind별 모델 라우팅 (`topic` → 1.5B, `chapter` → 7B, `compose` → 14B+)
  - `harness/huggingface.py` 신규 어댑터 + `registry.py`에 등록

### 9-9. 🟡 CLI 토큰 사용량 / 비용 표시 (사용자 체감 지표)
- **현상**: `engine.py`의 `_AnalysisJobHandler.usage` dict에서 토큰 수 집계하지만, 최종 CLI 출력에 노출되지 않아 사용자가 비용/절감 효과를 체감할 수 없음.
- **개선안**:
  ```
  📊 Token Usage Summary
  - Input tokens:  12,400 | Output tokens: 3,200
  - Estimated cost: $0.047 (gpt-4o-mini pricing)
  - Local SLM saved: 93.2% (45,200 / 48,500 tokens)
  ```

### 9-10. 🟡 Getting Started "5분 내 작동" 최적화
- **현상**: `./setup.sh` 후 `chew 'URL'`까지 도달하려면 AI 런타임(Codex/Gemini/Claude/Ollama) 설치 & 인증이 필요하나, README에 이 과정의 Quick Setup 가이드가 부족함. `chew doctor`에서 "설치되지 않음" 출력 시 다음 단계 안내 미제공.
- **개선안**:
  - README에 "⚡ 30-Second Quick Start" 섹션 추가: 가장 쉬운 런타임(Ollama) 기준 3단계 안내
  - `chew doctor` 출력에 각 런타임별 설치 명령 자동 안내 추가
  - `setup.sh`에 Ollama 자동 설치 + `qwen3:8b` 모델 pull 옵션 추가

### 9-11. 🟡 장애 주입(Fault Injection) 테스트 커버리지 강화
- **현상**: 현재 테스트는 정상 흐름 중심. 장애 시나리오 검증이 미비.
- **개선안** (구체적 테스트 케이스):
  1. `test_adaptive_limiter_rate_limit_and_recovery`: Rate limit 시 concurrency 절반 감소 → 연속 10회 성공 시 복구 검증
  2. `test_lease_expiry_retakeover`: Worker A crash → lease 만료 → Worker B의 job 재claim 검증
  3. `test_auth_error_propagation_e2e`: HarnessAuthenticationError → scheduler terminal_error → CLI exit code 2 전파 검증
  4. `test_partial_failure_continues`: topic 40개 중 3개 실패 시 나머지 결과로 partial Knowledge Pack 생성 검증
  5. `test_concurrent_db_writers`: 다중 스레드 동시 DB 쓰기 시 WAL 모드 무결성 검증

---

## 10. 우선순위 요약 Roadmap (Updated 2026-08-19)

1. **Step 1 (완료)**: `telemetry.py` 내 dead code 제거, 하드코딩 메트릭 제거 및 함수 소형화 refactoring.
2. **Step 2 (차기 우선과제)**: `engine.py` 레이어 경계 복원 (`Settings` 의존성 분리) 및 `service.py` Protocol 정리.
3. **Step 3 (🔴 신규 최우선)**: **Structured Logging** (`structlog`) 전면 도입 (§9-1) + **Graceful Shutdown** SIGINT/SIGTERM 핸들러 구현 (§9-2).
4. **Step 4 (🔴 신규)**: **SQLite 커넥션 풀링** (§9-3) + **Ollama HTTP 세션 재사용** (§9-4) + `assert` → `RuntimeError` 전환 (§9-6).
5. **Step 5**: `HarnessRouter` + `ResilientHarness` (Phase 1) 구현으로 **BYOK 토큰 95% 절감 계층 아키텍처** 완성 + HuggingFace 하네스 (§9-8).
6. **Step 6**: CLI 실시간 토큰 사용량/절감률 표시 (§9-9) + **Exponential Backoff** 적용 (§9-7).
7. **Step 7**: `scheduler.py` Polling 구조 개선 + **부분 실패 (Partial Failure) 허용** 처리 + SpanRecord 메모리 누수 방지 (§9-5).
8. **Step 8**: FastAPI 헬스 체크, 모델 버전 핀 CI/CD 자동화, Getting Started 5분 최적화 (§9-10).
9. **Step 9**: 장애 주입 테스트 스위트 구축 (§9-11) — Rate limit, Lease expiry, Auth error, Partial failure, Concurrent DB.

