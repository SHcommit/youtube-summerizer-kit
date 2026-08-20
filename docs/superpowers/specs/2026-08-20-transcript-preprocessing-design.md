# Transcript Preprocessing Pipeline Design

**Date:** 2026-08-20
**Status:** Approved for implementation

---

## 1. 목표

Frontier LLM에 전달되는 자막 토큰 수를 30~50% 줄여 BYOK 비용을 낮추고, 전처리 품질 향상으로 분석 결과의 정확도를 높인다.

**핵심 원칙:** Frontier LLM은 여전히 핵심 분석을 담당한다. 전처리는 Frontier가 더 적은 토큰으로 더 좋은 결과를 내도록 돕는 역할이다. 로컬 LLM은 이 단계에서 사용하지 않는다.

---

## 2. 현재 파이프라인과 변경 위치

### 현재

```
TranscriptService.resolve()          # engine.py:157
    ↓  (artifact cache check)
transcript: Transcript               # engine.py:169
    ↓  ← 전처리 없음
segment_transcript(transcript, ...)  # engine.py:180
    ↓
SegmentManifest → topic jobs → Frontier LLM
```

### 변경 후

```
TranscriptService.resolve()          # engine.py:157
    ↓
transcript: Transcript               # engine.py:169
    ↓
preprocess_transcript(transcript)    # engine.py:180 (새로 삽입) ← NEW
    ↓
segment_transcript(transcript, ...)  # engine.py:183 (한 줄 밀림)
    ↓
SegmentManifest → topic jobs → Frontier LLM
```

**변경 파일:**
- `src/chew/pipeline/preprocessing.py` — 신규 모듈
- `src/chew/pipeline/engine.py` — line 180 앞에 `preprocess_transcript()` 호출 삽입
- `src/chew/pipeline/segmentation.py` — `BoundaryDetector` 인터페이스에 `SemanticBoundaryDetector` 추가
- `pyproject.toml` — `[preprocess]` optional extras 그룹 추가
- `tests/test_preprocessing.py` — 신규 테스트

---

## 3. 전처리 3단계

### Stage 1: 규칙 기반 필터 (Rule-Based Filter)

**의존성:** 없음 (표준 라이브러리만)

**처리 내용:**

| 대상 | 처리 방법 | 예시 |
|---|---|---|
| 한국어 필러 | 정규식 제거 | `"음~"`, `"어~"`, `"그~"`, `"뭐~"` |
| 영어 필러 | 정규식 제거 | `"um"`, `"uh"`, `"like"`, `"you know"` |
| 말 더듬 반복 | 정규식 축약 | `"이이이이게"` → `"이게"` |
| 연속 공백 | collapse | `"hello   world"` → `"hello world"` |
| 빈 세그먼트 | 제거 | `text=""` 또는 공백만 있는 세그먼트 |
| 과도한 줄바꿈 | 정리 | `"\n\n\n"` → `"\n"` |

**구현:**

```python
# src/chew/pipeline/preprocessing.py

import re
from chew.core.models import Transcript, TranscriptSegment

_KO_FILLERS = re.compile(
    r'\b(음+~?|어+~?|그+~?|뭐+~?|아+~?|네+~?|예+~?)\b', re.IGNORECASE
)
_EN_FILLERS = re.compile(
    r'\b(um+|uh+|like|you know|i mean|basically|literally|actually)\b',
    re.IGNORECASE,
)
_STUTTER = re.compile(r'\b(\w+)\1{2,}\b')  # 3회 이상 반복 단어
_MULTI_SPACE = re.compile(r' {2,}')

def _clean_text(text: str) -> str:
    text = _KO_FILLERS.sub('', text)
    text = _EN_FILLERS.sub('', text)
    text = _STUTTER.sub(r'\1', text)
    text = _MULTI_SPACE.sub(' ', text)
    return text.strip()
```

### Stage 2: 문장부호 복원 (Punctuation Restoration)

**의존성:** `deepmultilingualpunctuation` (선택적 — `[preprocess]` extras)

**왜 필요한가:** 유튜브 자동생성 자막은 마침표, 쉼표가 없다. 현재 `PausePunctuationBoundaryDetector`가 문장부호를 단서로 경계를 탐지하는데, 자막에 문장부호가 없으면 세그멘테이션 품질이 떨어진다. 복원 후 Frontier 입력 품질도 올라간다.

```python
def _restore_punctuation(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    try:
        from deepmultilingualpunctuation import PunctuationModel  # type: ignore[import]
    except ImportError:
        return segments  # 미설치 시 skip

    model = PunctuationModel()
    restored = []
    for seg in segments:
        cleaned = model.restore_punctuation(seg.text)
        restored.append(seg.model_copy(update={"text": cleaned}))
    return restored
```

**지원 언어:** 영어, 한국어, 독일어, 프랑스어, 중국어 등 다국어 지원.

### Stage 3: 의미 경계 탐지 (Semantic Boundary Detection)

**의존성:** `sentence-transformers` (선택적 — `[preprocess]` extras)

**왜 필요한가:** 현재 `segmentation.py`는 타임스탬프 + 문장부호 기반으로 분절한다. 같은 주제가 이어지는 구간을 임의로 잘라내거나, 다른 주제가 하나의 토픽으로 묶이는 문제가 있다. 임베딩 유사도 변곡점을 `BoundaryDetector`에 힌트로 전달하면 더 자연스러운 토픽 경계를 찾을 수 있다.

**설계:**

```python
class SemanticBoundaryDetector:
    """sentence-transformers 기반 의미 경계 탐지기.

    segmentation.py의 BoundaryDetector 프로토콜을 구현한다.
    인접 세그먼트 쌍의 임베딩 코사인 유사도가 임계값(threshold) 아래로
    떨어지는 지점을 토픽 경계 후보로 표시한다.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._model: object | None = None  # lazy init

    def _get_model(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return self._model

    def detect(self, segments: list[TranscriptSegment]) -> list[int]:
        """경계로 판단된 segment index 목록을 반환한다."""
        if len(segments) < 3:
            return []
        model = self._get_model()
        texts = [s.text for s in segments]
        embeddings = model.encode(texts, convert_to_tensor=True)  # type: ignore[union-attr]
        boundaries = []
        for i in range(len(embeddings) - 1):
            sim = float(
                (embeddings[i] * embeddings[i + 1]).sum()
                / (embeddings[i].norm() * embeddings[i + 1].norm())
            )
            if sim < self.threshold:
                boundaries.append(i + 1)
        return boundaries
```

**사용 모델:** `paraphrase-multilingual-MiniLM-L12-v2`
- 크기: ~120MB
- 다국어 지원 (한국어 포함)
- CPU에서 실시간 처리 가능

---

## 4. 통합 진입점

```python
# src/chew/pipeline/preprocessing.py

def preprocess_transcript(transcript: Transcript) -> Transcript:
    """자막 전처리 파이프라인.

    Transcript는 frozen이므로 새 인스턴스를 반환한다.
    각 단계는 독립적으로 skip 가능 (의존성 미설치 시 자동 bypass).

    Stage 1: 규칙 기반 필러/반복 제거 (항상 실행)
    Stage 2: 문장부호 복원 (deepmultilingualpunctuation 설치 시)
    Stage 3: 의미 경계 탐지는 segmentation.py에 SemanticBoundaryDetector 주입
    """
    segments = list(transcript.segments)

    # Stage 1: 항상 실행
    segments = [
        seg.model_copy(update={"text": _clean_text(seg.text)})
        for seg in segments
        if _clean_text(seg.text)  # 빈 세그먼트 제거
    ]

    # Stage 2: 선택적
    segments = _restore_punctuation(segments)

    return transcript.model_copy(update={"segments": tuple(segments)})
```

**engine.py 변경 (최소):**

```python
# engine.py — segment_transcript() 호출 앞에 삽입
from chew.pipeline.preprocessing import preprocess_transcript, SemanticBoundaryDetector

# line ~180
transcript = preprocess_transcript(transcript)
detector = SemanticBoundaryDetector() if _semantic_available() else None
manifest = segment_transcript(transcript, selected_chapters, policy, detector=detector, depth=config.depth)
```

---

## 5. 새 extras 그룹

```toml
# pyproject.toml
[project.optional-dependencies]
preprocess = [
    "deepmultilingualpunctuation>=1.0",
    "sentence-transformers>=3.0",
]
```

```bash
pip install 'chew[preprocess]'
```

설치 안 해도 `chew`는 완전히 동작한다. Stage 2, 3만 bypass된다.

---

## 6. Token 절감 측정

전처리 전후 토큰 수를 `PreprocessingStats`로 기록하고 CLI에 출력한다.

```python
@dataclass
class PreprocessingStats:
    original_segment_count: int
    processed_segment_count: int
    original_token_estimate: int   # len(text.split()) 기반 추정
    processed_token_estimate: int
    removed_filler_count: int

    @property
    def token_reduction_pct(self) -> float:
        if self.original_token_estimate == 0:
            return 0.0
        return (1 - self.processed_token_estimate / self.original_token_estimate) * 100
```

CLI 출력 예시:
```
📊 Preprocessing Summary
  Segments : 312 → 287 (-8%)
  Tokens   : 48,500 → 31,200 (-35.7% — 17,300 tokens saved)
  Stages   : filler-removal ✓  punctuation-restoration ✓  semantic-boundary ✓
```

---

## 7. 테스트 계획

`tests/test_preprocessing.py`:

```python
def test_filler_removal_korean():
    seg = TranscriptSegment(start_ms=0, end_ms=1000, text="음~ 그러니까 어~ 이게")
    result = _clean_text(seg.text)
    assert "음" not in result
    assert "이게" in result

def test_filler_removal_english():
    result = _clean_text("um like you know this is basically great")
    assert "um" not in result
    assert "great" in result

def test_empty_segment_removed():
    t = make_transcript(["hello", "   ", "world"])
    processed = preprocess_transcript(t)
    assert len(processed.segments) == 2

def test_stutter_collapsed():
    result = _clean_text("이이이이게 뭔가")
    assert result.startswith("이게")

def test_preprocess_returns_new_transcript():
    t = make_transcript(["hello world"])
    result = preprocess_transcript(t)
    assert result is not t  # frozen → 새 인스턴스

def test_punctuation_restoration_skipped_without_dep(monkeypatch):
    monkeypatch.setitem(__import__('sys').modules, 'deepmultilingualpunctuation', None)
    t = make_transcript(["hello world this is a test"])
    result = preprocess_transcript(t)
    assert result.segments[0].text == "hello world this is a test"

def test_semantic_detector_returns_boundary_indexes():
    # 두 개의 완전히 다른 주제 텍스트 → 경계 탐지
    ...
```

---

## 8. 완료 기준

- [ ] `preprocessing.py` 구현 및 unit test 통과
- [ ] `engine.py` 통합 — 기존 테스트 전부 통과 (regression 없음)
- [ ] `segmentation.py` — `SemanticBoundaryDetector` 주입 인터페이스 추가
- [ ] `pyproject.toml` — `[preprocess]` extras 추가
- [ ] CLI 전처리 통계 출력
- [ ] `uv run --extra dev pytest` 전체 통과
- [ ] `uv run --extra dev ruff check .` 통과
- [ ] `uv run --extra dev mypy src/chew` 통과

---

## 9. 미래 확장 (이번 구현 범위 밖)

- **Notion 연동** — `chew notion` 명령어 (추후)
- **Knowledge Graph** — 영상 간 임베딩 유사도 기반 연결 (추후)
- **Cheap Frontier 티어 라우팅** — Haiku/Flash for topics, Sonnet for compose (추후)
- **뉴스/논문 소스** — URL input 확장 (추후)
