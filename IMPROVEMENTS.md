# `youtube-summarizer-kit` 기술 로드맵 (Technical Roadmap)

> 동영상/오디오 전용 개인 지식 축적 도구 - 볼수록 쌓이고, 쌓일수록 연결된다.
>
> **목표:** BYOK(Bring Your Own Key) 구조에서 Frontier LLM을 핵심 분석 엔진으로 유지하되, 전처리(로컬) + 지식 그래프(임베딩)로 비용을 낮추고 차별화된 가치를 만든다.

---

## Spike: 전처리 전략 검증 - Phase 1 구현 전 필수 실측

> **이 Spike는 Phase 1(자막 전처리 파이프라인) 구현 전에 반드시 완료해야 한다.** "30~50% 토큰 절감"은 현재 추정치다. 실측 없이 구현하면 투자 가치를 증명할 수 없다.

### 목적

1. **현재 기준선 측정** - 전처리 전 raw transcript의 언어별, 영상 길이별 토큰 수
2. **언어별 필러 밀도 측정** - 한국어 vs 영어 자막의 노이즈 비율 실증
3. **Phase 1 완료 후 재측정** - 동일 영상으로 전/후 비교 -> "X% 절감" 수치 확정
4. **출력 품질 측정** - 전처리 전/후 최종 요약의 문장 응집도, 정보 밀도 비교

### 고정 벤치마크 영상

실행 전 YouTube ID의 실제 길이를 검증한다. 영상이 삭제 또는 비공개가 되면 동일 길이의 대체 영상을 찾고, `reports/benchmark-videos.lock.json`에 최초 선정 기록과 변경 사유를 남긴다.

| # | 언어 | 실측 길이 | 영상 | YouTube ID | 선정 이유 | 상태 |
|---|---|---|---|---|---|---|
| 1 | 영어 | 4분 35초 | Stop Hunting in Trading Exists! But it is Just Not What You Expect it to Be | `c4GaJKprGEs` | 초단기 교육형 영상 | 확정 |
| 2 | 영어 | 39분 | Sam Altman: "Never a Better Time to Do a Startup" | `ZIaOBAjvc38` | 중간 길이 인터뷰 | 확정 |
| 3 | 영어 | 55분 48초 | Sam Altman on AGI, Compute, and Human Agency | `XDB5beon4DY` | 1시간 내외 기술 인터뷰 | 확정 |
| 4 | 영어 | 2시간 9초 | Joe Rogan Experience #1470 - Elon Musk | `RcYjXbSJBN8` | 장시간 비구조적 대화 | 확정 |
| 5 | 영어 | 2시간 49분 45초 | Elon Musk - "In 36 months, the cheapest place to put AI will be space" | `BYXbuik3dgA` | 다른 형식의 장시간 인터뷰 | 확정 |

### 측정 항목

```text
[현재 기준선 - 전처리 없음]
  raw_chars          원본 자막 총 문자 수
  raw_tokens         tiktoken cl100k_base 기준 토큰 수
  filler_count       필러 단어/패턴 매칭 수
  filler_ratio       filler_count / total_word_count
  segment_count      현재 segmentation.py가 생성한 세그먼트 수
  transcript_source  yt-dlp / YouTube API / Whisper

[Phase 1 완료 후 - 전처리 있음]
  processed_chars
  processed_tokens
  token_reduction_pct
  punctuation_added
  boundary_hints

[출력 품질 - Frontier 분석 후]
  output_sentences
  avg_sentence_len
  unique_info_ratio
```

### 실행 스크립트 위치와 명령

```bash
# 계획된 maintainer 전용 스크립트 위치
scripts/spike_token_baseline.py

# 전처리 없는 기준선
uv run --extra youtube --with tiktoken python scripts/spike_token_baseline.py --mode baseline

# Phase 1 완료 후 비교
uv run --extra youtube --with tiktoken python scripts/spike_token_baseline.py --mode compare
```

결과는 `reports/token-baseline.md`, `reports/token-comparison.md`, `reports/benchmark-videos.lock.json`에 저장한다.

### 스크립트 구현 요구사항

1. `BENCHMARK_VIDEOS`에서 URL을 읽는다.
2. `yt-dlp`로 자막을 내려받고 VTT/SRT를 plain text로 파싱한다.
3. `tiktoken cl100k_base`로 토큰 수를 계산한다.
4. 한국어/영어 필러 패턴으로 `filler_ratio`를 계산한다.
5. 결과를 Markdown 표로 저장한다.

### 결과 기대치 (가설 - Spike로 검증)

| 영상 유형 | 예상 필러 비율 | 예상 토큰 절감 |
|---|---|---|
| 한국어 브이로그/대화형 | 15~25% | 25~40% |
| 한국어 설명/강의형 | 8~15% | 15~25% |
| 영어 기술 인터뷰 | 5~10% | 10~18% |
| 영어 장시간 팟캐스트 | 10~20% | 18~30% |

가설이 틀릴 경우 절감률이 10% 미만이면 Phase 1 우선순위를 낮추고, 35%를 넘으면 즉시 구현 검토한다. 한국어의 절감률이 더 높으면 한국어 특화 전략을 강화한다.

---

## 완료된 작업 (Steps 1~9)

| Step | 내용 | 완료일 |
|---|---|---|
| Step 1 | `telemetry.py` dead code 제거, 동적 메트릭 | 2026-08-19 |
| Step 2 | `AnalysisConfig` DTO, `ConfigurableHarness` Protocol - 레이어 경계 복원 | 2026-08-19 |
| Step 3 | Structured Logging, SIGTERM Graceful Shutdown | 2026-08-19 |
| Step 4 | SQLite thread-local connection, Ollama `httpx` 세션 재사용, `assert` 제거 | 2026-08-19 |
| Step 5 | `HuggingFaceHarness`, `LayeredOllamaHarness` (1.5B/7B/14B 라우팅) | 2026-08-19 |
| Step 6 | Full Jitter backoff, CLI 토큰 사용량 표시 | 2026-08-19 |
| Step 7 | Event push polling, Partial Failure, SpanRecord memory cap | 2026-08-19 |
| Step 8 | FastAPI health/readiness, `chew serve`, 모델 태그 pin, `chew doctor` hints | 2026-08-19 |
| Step 9 | rate-limit, WAL, partial failure, auth fault-injection tests | 2026-08-20 |

---

## 다음 로드맵

### Phase 1: Frontier 토큰 절감 - 자막 전처리 파이프라인

**상세 설계:** `docs/superpowers/specs/2026-08-20-transcript-preprocessing-design.md`

유튜브 자동 생성 자막은 필러, 말 더듬, 문장부호 누락 상태로 Frontier LLM에 전달된다. 전처리는 Frontier가 더 적은 토큰으로 더 좋은 결과를 내도록 돕고, Frontier LLM은 계속 핵심 분석을 담당한다.

#### Strategy 패턴과 조합기

```text
Harness Protocol        -> AI runtime 전략
TranscriptProvider      -> 자막 수집 전략
BoundaryDetector        -> 경계 탐지 전략
PreprocessingStrategy   -> 자막 전처리 전략
```

각 전처리 단계는 독립적인 `PreprocessingStrategy`이며, `TranscriptPreprocessor`가 순서대로 조합한다. 선택 의존성이 없으면 `available() -> False`로 건너뛰므로 기존 동작을 깨지 않는다.

```python
class PreprocessingStrategy(Protocol):
    @property
    def name(self) -> str: ...
    def available(self) -> bool: ...
    def process(self, transcript: Transcript) -> Transcript: ...

class TranscriptPreprocessor:
    def process(self, transcript: Transcript) -> tuple[Transcript, PreprocessingStats]: ...
```

#### P1-1. 규칙 기반 필터 (`preprocessing.py` Stage 1)

- 한국어/영어 필러 제거
- 말 더듬 반복 축약
- 빈 세그먼트 제거
- 표준 라이브러리만 사용

#### P1-2. 문장부호 복원 (`preprocessing.py` Stage 2)

- `deepmultilingualpunctuation`으로 자동 생성 자막의 문장부호 복원
- `PausePunctuationBoundaryDetector`의 세그멘테이션 품질 향상
- `pip install 'chew[preprocess]'` 선택 의존성

#### P1-3. 의미 경계 탐지 (`preprocessing.py` Stage 3)

- `sentence-transformers`의 다국어 모델을 사용한다.
- 인접 세그먼트 코사인 유사도 변곡점을 topic 경계 힌트로 사용한다.
- `segmentation.py`의 `BoundaryDetector`에 주입한다.
- `pip install 'chew[preprocess]'` 선택 의존성

#### P1-4. 파이프라인 통합과 CLI 통계

```text
TranscriptService.resolve()
  -> raw transcript artifact 저장
  -> TranscriptPreprocessor.process()
  -> processed transcript artifact 저장
  -> segment_transcript()
  -> topic -> chapter -> Knowledge Pack
```

CLI는 원본/정제 토큰 수, 절감률, 적용된 stage를 표시한다.

### Phase 2: Knowledge Graph - 보류

**상태: 보류.** 현재 토큰 비용과 Ollama 실행 효율 개선보다 우선하지 않는다. 아래 구조는 향후 사용자가 다수의 영상을 반복 분석하고, 영상 간 탐색 요구가 실제로 확인된 경우에만 재검토한다.

#### P2-1. 영상 간 유사도 인덱싱

- Knowledge Pack 생성 후 topic/chapter 임베딩 생성
- SQLite `embeddings`, `entity_links` 테이블에 저장
- 새 영상 분석 시 기존 인덱스와 유사도를 비교해 연관 영상을 제시

#### P2-2. 개체명 추출과 연결

- 토픽 분석 결과에서 인물, 개념, 주장 태깅
- 동일 개체가 등장한 영상 간 자동 링크
- Obsidian `[[wikilinks]]`에 관련 영상 섹션 확장

#### P2-3. `chew graph` 명령어

```bash
chew graph
chew graph --topic "AI"
chew graph --related RUN_ID
```

### Phase 3: Notion 연동 - 보류

**상태: 보류.** 현재는 YouTube/로컬 미디어 요약 경로의 비용, 처리 시간, 품질 측정이 우선이다.

- 영상 1개를 Notion Database row와 child page로 저장
- Database properties: Title, URL, Date, Tags, Duration, Language
- Child page에는 Knowledge Pack의 chapter/topic 계층을 저장
- `chew notion <URL> --database-id <ID>` 명령 제공

### Phase 4: Cheap Frontier 티어 라우팅

기본은 사용자가 선택한 단일 BYOK runtime을 모든 작업에 사용하는 것이다. tier 라우팅은 사용자가 보유한 runtime과 모델을 명시적으로 설정한 경우에만 활성화한다. 다른 cloud provider로 자동 전환하지 않는다.

| 작업 | 기본 정책 | tier routing opt-in |
|---|---|---|
| `topic_summary` x N | 선택 runtime | 사용자가 지정한 저비용 tier |
| `chapter_summary` | 선택 runtime | 사용자가 지정한 중간 tier |
| `output_compose` | 선택 runtime | 사용자가 지정한 고품질 tier |
| `output_verify` | 선택 runtime | 사용자가 지정한 고품질 tier 또는 opt-in |

`LayeredOllamaHarness`의 Map/Combine/Reduce 구조는 로컬 선택지로 유지한다. cloud runtime의 task-tier 정책은 `CHEW.md`에서 사용자가 runtime/model/fallback 순서를 직접 설정할 수 있을 때만 추가한다.

**현재 구현:** `CHEW.md`의 `task_runtimes`로 task별 runtime을 명시할 수 있다. map에 없는 task는 단일 기본 `runtime`을 사용하며 자동 provider fallback은 없다. 모델 단위 routing은 실제 적용 가능한 selector가 있는 Ollama의 전역 `ollama_model`만 지원한다. cloud model/fallback 순서는 adapter별 적용·검증 계약이 추가되기 전에는 받지 않는다.

### Phase 5: 콘텐츠 소스 확장 - 보류

**상태: 보류.** 뉴스 URL, 팟캐스트 RSS, PDF, Whisper VAD는 새로운 입력 표면을 늘리는 작업이다. 현재 성능 개선 범위에는 포함하지 않는다.

- 뉴스 URL: 기사 본문 자동 추출과 분석
- 팟캐스트 RSS: 에피소드 다운로드와 Whisper 변환
- 논문 PDF: PDF 파싱과 섹션별 분석
- Whisper VAD 병렬 처리: VAD 기반 오디오 슬라이싱 후 멀티코어 전사

---

## 잔여 기술 부채

| 항목 | 설명 |
|---|---|
| telemetry 격리 | 전역 singleton을 ContextVar로 격리 |
| SQLite migration | 버전별 migration 체계 |
| 인증 명령 매핑 | registry/builtin 중복 단일화 |
| segmentation depth | 하드코딩 한국어 키워드 제거 |
| custom prompts | 사용자 Pattern 시스템 |

**현재 범위:** 이 중 성능 측정·실행 안정성과 직접 연결되는 telemetry 격리, SQLite migration, segmentation depth만 성능 작업 이후에 재검토한다. 인증 명령 매핑과 custom prompts는 제품 기능 작업으로 보류한다.

---

## 제품 포지셔닝

> **"동영상/오디오 전용 개인 지식 축적 도구"**

- BYOK: 내 API/CLI와 내 데이터
- Analyze Once, Reuse Forever: 같은 영상을 두 번 분석하지 않음
- Knowledge Graph: 영상 간 연결 자동 생성

---

## 추가 개선안: 비용, 품질, 장시간 영상의 실행 기준

이 섹션은 위 구조를 대체하지 않는다. 전처리와 tier 라우팅을 실제 제품 기본값으로 채택하기 위한 보완 조건이다.

### A. 토큰 측정은 추정치와 실제 청구량을 분리한다

- `tiktoken cl100k_base`는 비교용 추정치로만 사용한다.
- `GenerationResult.usage`를 job 단위로 저장해 topic, chapter, compose, retry, repair의 prompt/completion usage를 따로 표시한다.
- runtime이 usage를 제공하지 않으면 `unknown`으로 표시한다. 추정 토큰을 실제 비용으로 단정하지 않는다.
- model ID 또는 revision, prompt fingerprint, concurrency, transcript provider를 benchmark 결과에 기록한다.

### B. 전처리는 원문을 보존하고 안전하게 켠다

**현재 구현 및 실측:** `preprocess_transcript: true`는 raw transcript를 별도 artifact로 보존하면서 보수적 필러 삭제를 적용한다. 잠금된 영어 5개 영상의 `cl100k_base` 비교는 **1.92%~4.94%** 절감으로, 기본 활성화 기준(10%)에 미달했다. 따라서 기본값은 `false`를 유지한다. 문장부호 복원과 의미 경계는 `[preprocess]` 선택 의존성이 있을 때만 추가되며, Frontier 품질 fixture 평가 전에는 기본값으로 승격하지 않는다.

- raw transcript와 processed transcript는 별도 artifact로 저장한다.
- claim의 evidence와 timestamp 검증은 항상 raw transcript를 기준으로 한다.
- `like`, `actually`, 한국어 `그`, `뭐`처럼 문맥에 따라 의미가 되는 단어를 일반 필러 규칙으로 삭제하지 않는다.
- `SemanticBoundaryDetector`는 현재 `BoundaryDetector.choose()` 계약에 맞추거나 adapter와 테스트를 함께 제공한다.

### C. 영상 길이에 따라 분석 경로를 다르게 사용한다

| 조건 | 기본 경로 | 이유 |
|---|---|---|
| 15분 이하 | 전처리 후 단일 자막 요약 | 계층 호출의 prompt/schema/output 오버헤드를 피한다. |
| 15분 초과 60분 이하 | topic -> chapter -> compose | context window를 안정적으로 관리하고 병렬 처리가 가능하다. |
| 60분 초과 | 계층 처리 + 누락 구간 표기 | 장시간 문맥을 다루되 부분 실패를 정상 완료처럼 보이지 않게 한다. |
| 화면 정보가 핵심 | 자막 경로의 한계를 결과에 표시 | 자막만으로 슬라이드, 코드 화면, 차트를 보장할 수 없다. |

기본 segmentation의 5분 target과 15초 overlap은 원문 입력을 약 5% 중복시킬 수 있다. 짧은 영상에 계층 처리를 강제하지 않는다.

### D. 계층 처리 결과의 완전성을 표시한다

- `KnowledgePack`에 `completion_status`, `failed_topic_ids`, `missing_ranges`, `runtime_id`, `model`을 추가한다.
- topic이 `failed_runtime`이면 최종 결과를 `partial`로 표시하고 digest 첫머리에 누락 범위를 표시한다.
- cache key에는 runtime뿐 아니라 모델 revision과 전처리 recipe fingerprint를 포함한다.

### E. 전처리와 tier 라우팅의 채택 기준

기본 활성화 전 다음을 모두 만족해야 한다.

1. 실제 input usage 또는 측정 가능한 비용이 기준선보다 10% 이상 감소한다.
2. evidence recall과 timestamp accuracy가 기준선보다 낮아지지 않는다.
3. unsupported claims와 missing ranges가 증가하지 않는다.
4. 한국어 fixture와 30분, 1시간 fixture에서 처리 시간 중앙값이 정한 회귀 한도를 넘지 않는다.

미달 시 해당 전략은 opt-in으로 유지하고, 절감률을 마케팅 문구로 사용하지 않는다.

### F. Ollama 실행 효율 개선 우선순위

현재 Ollama 경로는 topic마다 전체 segment payload와 JSON schema를 전송하고, 시간 기반 분절, JSON repair, profile별 compose/verify 호출의 영향을 함께 받는다. 실제 병목을 가정하지 않고 아래 순서로 측정하고 개선한다.

#### F1. 실행별 비용 프로파일 기록

**현재 구현:** Ollama의 provider-reported token count와 duration, runtime/model/task/request ID를 SQLite `job_measurements`에 기록한다. 각 시도에는 입력 문자 수, 입력 segment 수, output schema 문자 수, repair 여부, scheduler retry 여부도 함께 기록한다. 이 값은 요청 구조 프로파일이며 provider 청구 토큰과 구분한다. cache hit 및 품질 평가는 fixture benchmark 결과와 함께 다음 단계에서 추가한다.

각 Ollama 요청에서 다음을 job 단위로 저장한다.

- `model`, `prompt_eval_count`, `eval_count`
- Ollama가 제공하면 load, prompt evaluation, generation duration
- task 종류, 입력 segment 수, 입력 문자 수, output schema 크기
- retry, repair, parse failure, cache hit 여부

30분과 1시간 fixture에서 이 정보를 먼저 수집한다. 그 전에는 특정 모델 크기나 단계가 병목이라고 단정하지 않는다.

maintainer는 실행 후 아래처럼 집계 리포트를 생성한다. 이 리포트는 provider가 보고한 값만 표시하며, provider usage가 없으면 `unknown`으로 남긴다.

```bash
uv run python scripts/report_job_measurements.py \
  --database .chew/state.sqlite3 --run-id RUN_ID \
  --output reports/ollama-profile-RUN_ID.md
```

#### F2. token budget 기반 분절

**현재 구현:** `CHEW.md`의 `max_input_tokens`, `reserved_output_tokens`를 설정하면 보수적 추정치로 topic 입력을 자른다. 기본값은 비활성화이며, 실제 provider token/cost 절감 주장은 아직 하지 않는다.

현재 5분 target은 말하기 속도와 자막 밀도를 반영하지 못한다. 같은 5분이라도 인터뷰와 강의의 입력 토큰은 크게 다를 수 있다.

- runtime/model별 `max_input_tokens`와 예약 output budget을 정의한다.
- topic은 시간 경계와 token budget을 모두 만족하도록 자른다.
- 15초 overlap은 품질 benchmark에서 필요성이 확인된 경우에만 유지하거나 길이를 줄인다.
- 15분 이하 영상은 단일 요약 경로와 계층 경로를 비교해 더 싼 경로를 기본값으로 선택한다.

#### F3. repair와 모델 교체의 비용 통제

- 1.5B 모델의 JSON 준수율이 낮아 repair가 증가하면, 저비용 tier는 절감이 아니라 비용 증가다.
- repair는 실패한 tier보다 같은 수준 또는 더 높은 수준의 모델로 보내며, repair rate를 routing 채택 조건에 포함한다.
- 하나의 Ollama server에서 1.5B/7B/14B 모델을 자주 교체하면 모델 로딩과 메모리 압박이 생길 수 있다. benchmark에서 확인되기 전에는 run 단위 단일 모델과 layered 모델을 비교한다.
- 모델을 유지할 수 있는 환경에서는 `keep_alive`와 모델 상주 메모리 비용을 함께 측정한다.

#### F4. 불필요한 생성 호출 제거

- digest와 JSON/Obsidian 출력은 저장된 Knowledge Pack을 deterministic renderer로 재사용한다.
- blog/study의 outline -> compose -> verify 세 호출은 기본값으로 강제하지 않는다. 검증은 고위험 output 또는 명시적 옵션에서만 실행할지 benchmark로 결정한다.
- 같은 source, recipe, model revision, preprocessing recipe의 결과는 cache hit 시 LLM을 다시 호출하지 않는다.

#### F5. Ollama 채택 기준

변경은 30분과 1시간 fixture에서 다음을 모두 만족할 때만 기본값으로 적용한다.

1. 총 `prompt_eval_count + eval_count` 또는 총 실행 시간이 기준선보다 감소한다.
2. JSON parse failure와 repair rate가 기준선보다 증가하지 않는다.
3. evidence recall, timestamp accuracy, missing ranges가 악화되지 않는다.
4. peak memory와 모델 load 시간이 로컬 실행 환경의 한계를 넘지 않는다.
