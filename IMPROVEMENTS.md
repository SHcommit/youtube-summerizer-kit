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
