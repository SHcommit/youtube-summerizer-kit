# `youtube-summarizer-kit` 기술 로드맵 (Technical Roadmap)

> 동영상/오디오 전용 개인 지식 축적 도구 — 볼수록 쌓이고, 쌓일수록 연결된다.
>
> **목표:** BYOK(Bring Your Own Key) 구조에서 Frontier LLM을 핵심 분석 엔진으로 유지하되,
> 전처리(로컬) + 지식 그래프(임베딩)로 비용을 낮추고 차별화된 가치를 만든다.

---

## ✅ 완료된 작업 (Steps 1~9)

| Step | 내용 | 완료일 |
|---|---|---|
| Step 1 | `telemetry.py` dead code 제거, 동적 메트릭 | 2026-08-19 |
| Step 2 | `AnalysisConfig` DTO, `ConfigurableHarness` Protocol — 레이어 경계 복원 | 2026-08-19 |
| Step 3 | Structured Logging (JsonFormatter), SIGTERM Graceful Shutdown | 2026-08-19 |
| Step 4 | SQLite thread-local 커넥션 캐싱, Ollama `httpx` 세션 재사용, `assert` → `RuntimeError` | 2026-08-19 |
| Step 5 | `HuggingFaceHarness`, `LayeredOllamaHarness` (1.5B/7B/14B 라우팅) | 2026-08-19 |
| Step 6 | `_backoff_sleep()` Full Jitter, `CommandResult.usage` CLI 토큰 표시 | 2026-08-19 |
| Step 7 | `asyncio.Event` push polling, Partial Failure (`failed_runtime`), `deque(maxlen=10_000)` | 2026-08-19 |
| Step 8 | FastAPI `/health` `/readiness`, `chew serve`, 모델 태그 핀, `chew doctor` install hints | 2026-08-19 |
| Step 9 | Fault injection test suite (rate-limit recovery, WAL 동시 쓰기, 부분 실패, auth E2E) | 2026-08-20 |

---

## 🚀 다음 로드맵

### Phase 1: Frontier 토큰 절감 — 자막 전처리 파이프라인

**Spec:** `docs/superpowers/specs/2026-08-20-transcript-preprocessing-design.md`

**배경:**
- 유튜브 자동생성 자막은 필러("음~", "어~"), 말 더듬, 문장부호 없음 상태로 Frontier에 그대로 전달됨
- 원본 자막의 30~50%가 실질 정보 없는 노이즈
- 전처리로 Frontier 입력 토큰을 줄이면 BYOK 비용이 직접 감소

**구현 내용:**

#### §P1-1. 규칙 기반 필터 (`preprocessing.py` Stage 1)
- 한국어/영어 필러 단어 제거 ("음~", "어~", "um", "uh" 등)
- 말 더듬 반복 축약 ("이이이이게" → "이게")
- 빈 세그먼트 제거
- **의존성:** 없음 (표준 라이브러리)

#### §P1-2. 문장부호 복원 (`preprocessing.py` Stage 2)
- `deepmultilingualpunctuation` 모델로 자동생성 자막에 마침표/쉼표 복원
- `PausePunctuationBoundaryDetector`의 세그멘테이션 품질 향상
- **의존성:** `pip install 'chew[preprocess]'`

#### §P1-3. 의미 경계 탐지 (`preprocessing.py` Stage 3)
- `sentence-transformers`(`paraphrase-multilingual-MiniLM-L12-v2`) 임베딩
- 인접 세그먼트 코사인 유사도 변곡점 → 자연스러운 토픽 경계 힌트
- `segmentation.py`의 `BoundaryDetector` 인터페이스에 주입
- **의존성:** `pip install 'chew[preprocess]'`

#### §P1-4. CLI 전처리 통계 출력
```
📊 Preprocessing Summary
  Tokens : 48,500 → 31,200 (-35.7% — 17,300 tokens saved)
  Stages : filler-removal ✓  punctuation-restoration ✓  semantic-boundary ✓
```

---

### Phase 2: Knowledge Graph — 볼수록 연결되는 두 번째 뇌

**배경:** 현재 각 영상 분석은 독립적으로 끝난다. 같은 주제, 같은 인물, 같은 주장이 다른 영상에 등장해도 연결되지 않는다. 임베딩 기반 유사도로 영상 간 연결고리를 자동 추적한다.

#### §P2-1. 영상 간 유사도 인덱싱
- 각 Knowledge Pack 생성 후 `sentence-transformers`로 토픽/챕터 임베딩 생성
- SQLite 신규 테이블 `embeddings`, `entity_links`에 저장
- 새 영상 분석 시 기존 인덱스와 코사인 유사도 비교 → 연관 영상 목록 생성

#### §P2-2. 개체명(Entity) 추출 및 연결
- 토픽 분석 결과에서 인물/개념/주장 태깅
- 동일 개체가 등장한 영상 간 자동 링크 생성
- Obsidian `[[wikilinks]]` 자동 확장 — 기존 노트에 "관련 영상" 섹션 추가

#### §P2-3. `chew graph` 명령어
```bash
chew graph                    # 전체 Knowledge Graph 요약
chew graph --topic "AI"       # 특정 주제 관련 영상 목록
chew graph --related RUN_ID   # 특정 영상과 연관된 영상들
```

---

### Phase 3: Notion 연동

#### §P3-1. Notion Database + Page 구조
- 영상 1개 → Notion Database row + child page
- Database properties: Title, URL, Date, Tags, Duration, Language
- Child page: Knowledge Pack 전체 내용 (챕터/토픽 계층 구조)
- **의존성:** `pip install 'chew[notion]'` + `NOTION_TOKEN` 환경 변수

#### §P3-2. `chew notion` 명령어
```bash
chew notion 'https://youtu.be/VIDEO_ID'
chew notion 'https://youtu.be/VIDEO_ID' --database-id <ID>
```

---

### Phase 4: Cheap Frontier 티어 라우팅

**배경:** 현재 모든 작업이 같은 Frontier 모델을 사용한다. 토픽 요약(bulk)은 저렴한 모델로, 최종 compose만 고성능 모델을 쓰면 비용이 추가로 절감된다.

#### §P4-1. 작업 유형별 모델 라우팅
| 작업 | 추천 모델 | 비용 |
|---|---|---|
| `topic_summary` × N (bulk) | Claude Haiku / Gemini Flash | 저렴 |
| `chapter_summary` | Claude Haiku / Gemini Flash | 저렴 |
| `output_compose` | Claude Sonnet / Gemini Pro | 중간 |
| `output_verify` | Claude Sonnet / Gemini Pro | 중간 |

#### §P4-2. BYOK Token Economy 표시
```
💰 BYOK Token Economy
  Bulk (topic × 40) : 31,200 tokens → Haiku   (~$0.003)
  Final compose     :  3,800 tokens → Sonnet   (~$0.019)
  Total saved vs baseline: 87% (vs raw transcript to Sonnet)
```

---

### Phase 5: 콘텐츠 소스 확장

- **뉴스 URL** — 기사 본문 자동 추출 + 분석 (`newspaper3k`, `trafilatura`)
- **팟캐스트 RSS** — 에피소드 자동 다운로드 + Whisper 변환
- **논문 PDF** — PDF 파싱 + 섹션별 분석 (`pymupdf`)
- **Whisper VAD 병렬 처리** — VAD 기반 오디오 슬라이싱 후 멀티코어 Whisper 전사

---

### Phase 6: Python 라이브러리 API — 개발자 통합

**배경:** 현재 `chew`는 CLI 전용이다. Python 라이브러리 인터페이스를 제공하면 다른 코드에서 직접 임포트해 자동화 파이프라인에 통합할 수 있다. 기존 `ApplicationService`가 이미 잘 분리되어 있어 추가 비용이 최소화된다.

#### §P6-1. Public Python API
```python
from chew import analyze, analyze_sync

# 비동기
result = await analyze(
    "https://youtu.be/VIDEO_ID",
    runtime="codex",          # BYOK runtime_id
    depth=3,                  # 분석 깊이
    output_format="digest",   # "digest" | "blog" | "study" | "obsidian"
)
print(result.text)            # 최종 출력
print(result.knowledge_pack)  # 구조화된 Knowledge Pack

# 동기 래퍼 (스크립팅용)
result = analyze_sync("https://youtu.be/VIDEO_ID", runtime="gemini")
```

#### §P6-2. 패키지 API 공개
- `src/chew/__init__.py`에 `analyze`, `analyze_sync` 공개
- `AnalysisResult(text, knowledge_pack, stats, run_id)` 반환 타입
- **의존성:** 없음 (기존 `ApplicationService` 래핑)

---

### Phase 7: MCP 서버 — AI Agent 통합

**배경:** Model Context Protocol(MCP)을 통해 Claude Code, Cursor, Windsurf 등 AI 에이전트가 `chew`를 도구로 직접 호출할 수 있다. "AI 관련 영상 10개 분석해서 공통 인사이트 뽑아줘" 같은 워크플로우가 가능해진다.

#### §P7-1. MCP 서버 (`chew serve --mcp`)
```python
# Claude Code / Cursor에서 자동으로 호출 가능
mcp.tool("chew_analyze")
async def chew_analyze(url: str, runtime: str = "codex") -> dict:
    result = await analyze(url, runtime=runtime)
    return {"text": result.text, "run_id": result.run_id}

mcp.tool("chew_list")
async def chew_list() -> list[dict]:
    # 로컬 캐시된 Knowledge Pack 목록 반환
    ...

mcp.tool("chew_get")
async def chew_get(run_id: str, format: str = "digest") -> dict:
    # 기존 분석 결과를 다른 포맷으로 재조립
    ...
```

#### §P7-2. MCP 설정 예시
```json
// ~/.claude/mcp_servers.json
{
  "chew": {
    "command": "chew",
    "args": ["serve", "--mcp"],
    "env": {"CODEX_API_KEY": "..."}
  }
}
```

#### §P7-3. AI Agent 워크플로우 예시
```
Claude Code → chew_analyze(url) → Knowledge Pack → Obsidian에 자동 저장
Custom Agent → "AI 영상 10개 분석" → chew_analyze × 10 → Knowledge Graph → 리포트
```

- **의존성:** `pip install 'chew[mcp]'` + `mcp` 패키지

---

### Phase 8: 자동화 통합 — n8n / Zapier / Make

**배경:** Phase 6 REST API (`chew serve`)와 Phase 7 MCP를 기반으로 no-code 자동화 플랫폼과 연결한다. 새 유튜브 영상이 올라오면 자동으로 분석하고 Notion에 저장하는 워크플로우를 비개발자도 구성할 수 있다.

#### §P8-1. n8n 워크플로우 예시
```
YouTube Channel 구독 (RSS) → HTTP Request: POST /analyze → Notion Database 업데이트
```

#### §P8-2. REST API 확장 (`chew serve` 기반)
```http
POST /analyze
Content-Type: application/json
{"url": "https://youtu.be/VIDEO_ID", "runtime": "codex", "output_format": "digest"}

→ 202 Accepted
{"run_id": "abc123", "status": "processing", "poll": "/runs/abc123"}

GET /runs/{run_id}
→ 200 {"status": "completed", "text": "...", "knowledge_pack": {...}}
```

#### §P8-3. 자동화 플랫폼 연동 시나리오
| 트리거 | 액션 | 결과 |
|---|---|---|
| YouTube 채널 새 영상 | `POST /analyze` | Notion DB 자동 업데이트 |
| 팟캐스트 RSS 새 에피소드 | `POST /analyze` | Obsidian Vault 자동 추가 |
| Slack 링크 공유 | `POST /analyze` | 요약본 Slack 스레드에 게시 |

- **의존성:** Phase 6 REST API 완성 후 (추가 의존성 없음)

---

## 📋 잔여 기술 부채 (낮은 우선순위)

| 항목 | 설명 |
|---|---|
| §1-1 | `telemetry.py` 전역 싱글턴 → `ContextVar` 격리 |
| §3-2 | SQLite 스키마 마이그레이션 정식 체계 (버전별 스크립트) |
| §3-4 | CLI 인증 명령어 매핑 중복 단일화 (`registry.py` + `builtin.py`) |
| §4-1 | `segmentation.py` 하드코딩 한국어 키워드 (`"초간단"` 등) 제거 |
| §5-1 | 사용자 커스텀 프롬프트 Pattern 시스템 (`~/.chew/patterns/`) |

---

## 🎯 제품 포지셔닝

> **"동영상/오디오 전용 개인 지식 축적 도구"**
>
> ChatGPT에 요약 시키면 대화가 끝나면 사라진다.
> `chew`는 볼수록 연결되고 쌓인다.
>
> - BYOK — 내 API/CLI로, 내 데이터는 내 로컬에
> - Analyze Once, Reuse Forever — 같은 영상 두 번 분석하지 않는다
> - Knowledge Graph — 영상들 간의 연결이 자동으로 만들어진다

### AI Agent 통합 비전

```
지금:   $ chew summarize 'https://youtu.be/...'

미래:
  Claude Code → chew_analyze(url) → Obsidian에 자동 저장
  Zapier/n8n  → YouTube 새 영상 감지 → chew → Notion DB 업데이트
  Python      → from chew import analyze; result = await analyze(url)
  Custom Agent→ "AI 관련 영상 10개 분석해서 공통 인사이트 뽑아줘"
                → chew × 10 → Knowledge Graph → 리포트 생성
```

**왜 하네스 구조가 이 비전을 가능하게 하는가:**
- 런타임이 Protocol로 추상화되어 있어 어떤 BYOK 키도 그대로 전달 가능
- `ApplicationService`가 CLI/MCP/REST API 모두에서 재사용 가능한 단일 진입점
- Knowledge Pack이 content-addressed로 캐싱되어 다중 소비자(Obsidian, Notion, API)가 재조립 비용 없이 활용 가능
