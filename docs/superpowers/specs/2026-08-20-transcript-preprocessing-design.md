# Transcript Preprocessing Pipeline Design

**Date:** 2026-08-20
**Status:** Approved for implementation

---

## 1. 목표

Frontier LLM에 전달되는 자막 토큰 수를 30~50% 줄여 BYOK 비용을 낮추고, 전처리 품질 향상으로 분석 결과의 정확도를 높인다.

**핵심 원칙:** Frontier LLM은 여전히 핵심 분석을 담당한다. 전처리는 Frontier가 더 적은 토큰으로 더 좋은 결과를 내도록 돕는 역할이다. 로컬 LLM은 이 단계에서 사용하지 않는다.

---

## 2. 설계 철학 — Strategy 패턴

기존 코드베이스 전체가 Strategy 패턴으로 설계되어 있다:

```
Harness Protocol        → AI 런타임별 전략 (codex, claude, ollama, huggingface...)
TranscriptProvider      → 자막 수집별 전략 (youtube_api, yt_dlp, whisper...)
BoundaryDetector        → 경계 탐지별 전략 (segmentation.py)
```

전처리도 동일한 패턴을 따른다. 각 단계는 독립적인 `PreprocessingStrategy`이며, `TranscriptPreprocessor`가 이를 조합한다.

**장점:**
- 미설치 의존성은 `available() → False`로 자동 skip — 기존 동작 보장
- 새 전략 추가 시 기존 코드 수정 없음 (Open/Closed Principle)
- 각 전략 독립 단위 테스트 가능
- `CHEW.md`에서 전략 on/off 설정 가능 (추후 확장)
- 아키텍처 일관성 유지

### Protocol 정의

```python
# src/chew/pipeline/preprocessing.py

from typing import Protocol
from chew.core.models import Transcript

class PreprocessingStrategy(Protocol):
    """전처리 전략 인터페이스. 각 구현체는 독립적으로 적용 가능하다."""

    @property
    def name(self) -> str:
        """전략 식별자 — CLI 통계 출력에 사용."""
        ...

    def available(self) -> bool:
        """필요한 의존성이 설치되어 있는지 확인."""
        ...

    def process(self, transcript: Transcript) -> Transcript:
        """Transcript를 받아 처리된 새 Transcript를 반환한다.
        Transcript는 frozen이므로 반드시 새 인스턴스를 반환해야 한다."""
        ...
```

### 조합기 (Composer)

```python
@dataclass
class PreprocessingStats:
    original_segment_count: int
    processed_segment_count: int
    original_token_estimate: int
    processed_token_estimate: int
    applied_strategies: list[str]  # 실제 적용된 전략 이름 목록

    @property
    def token_reduction_pct(self) -> float:
        if self.original_token_estimate == 0:
            return 0.0
        return (1 - self.processed_token_estimate / self.original_token_estimate) * 100


class TranscriptPreprocessor:
    """전처리 전략들을 순서대로 적용하는 조합기.

    strategies를 명시하지 않으면 기본 3단계 전략을 사용한다.
    각 전략은 available() 검사 후 적용되므로 선택적 의존성이 없어도 동작한다.
    """

    def __init__(self, strategies: list[PreprocessingStrategy] | None = None) -> None:
        self.strategies: list[PreprocessingStrategy] = strategies or [
            FillerRemovalStrategy(),       # 항상 available
            PunctuationStrategy(),         # deepmultilingualpunctuation 설치 시
            SemanticBoundaryStrategy(),    # sentence-transformers 설치 시
        ]

    def process(self, transcript: Transcript) -> tuple[Transcript, PreprocessingStats]:
        original_tokens = _estimate_tokens(transcript)
        original_count = len(transcript.segments)
        applied: list[str] = []

        for strategy in self.strategies:
            if strategy.available():
                transcript = strategy.process(transcript)
                applied.append(strategy.name)

        return transcript, PreprocessingStats(
            original_segment_count=original_count,
            processed_segment_count=len(transcript.segments),
            original_token_estimate=original_tokens,
            processed_token_estimate=_estimate_tokens(transcript),
            applied_strategies=applied,
        )


def _estimate_tokens(transcript: Transcript) -> int:
    """단어 수 기반 토큰 추정 (실제 토크나이저 없이 근사값)."""
    return sum(len(seg.text.split()) for seg in transcript.segments)
```

---

## 3. 현재 파이프라인과 변경 위치

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

## 4. 전처리 전략 구현체 (3단계)

### Strategy 1: `FillerRemovalStrategy` — 규칙 기반 필러 제거

**`available()` → 항상 `True`** (표준 라이브러리만 사용)

| 대상 | 처리 | 예시 |
|---|---|---|
| 한국어 필러 | 정규식 제거 | `"음~"`, `"어~"`, `"그~"`, `"뭐~"` |
| 영어 필러 | 정규식 제거 | `"um"`, `"uh"`, `"like"`, `"you know"` |
| 말 더듬 반복 | 정규식 축약 | `"이이이이게"` → `"이게"` |
| 연속 공백 | collapse | `"hello   world"` → `"hello world"` |
| 빈 세그먼트 | 제거 | `text=""` 또는 공백만 있는 세그먼트 |

```python
import re
from chew.core.models import Transcript

_KO_FILLERS = re.compile(r'\b(음+~?|어+~?|그+~?|뭐+~?|아+~?|네+~?|예+~?)\b')
_EN_FILLERS = re.compile(
    r'\b(um+|uh+|like|you know|i mean|basically|literally|actually)\b',
    re.IGNORECASE,
)
_STUTTER = re.compile(r'\b(\w)\1{2,}\b')
_MULTI_SPACE = re.compile(r' {2,}')


class FillerRemovalStrategy:
    name = "filler-removal"

    def available(self) -> bool:
        return True

    def process(self, transcript: Transcript) -> Transcript:
        cleaned = []
        for seg in transcript.segments:
            text = _KO_FILLERS.sub('', seg.text)
            text = _EN_FILLERS.sub('', text)
            text = _STUTTER.sub(r'\1', text)
            text = _MULTI_SPACE.sub(' ', text).strip()
            if text:  # 빈 세그먼트 제거
                cleaned.append(seg.model_copy(update={"text": text}))
        return transcript.model_copy(update={"segments": tuple(cleaned)})
```

---

### Strategy 2: `PunctuationStrategy` — 문장부호 복원

**`available()` → `deepmultilingualpunctuation` 설치 여부**

유튜브 자동생성 자막은 마침표·쉼표가 없다. 복원하면 `PausePunctuationBoundaryDetector`의 경계 탐지 품질이 올라가고, Frontier 입력 가독성도 높아진다.

```python
import importlib.util


class PunctuationStrategy:
    name = "punctuation-restoration"

    def available(self) -> bool:
        return importlib.util.find_spec("deepmultilingualpunctuation") is not None

    def process(self, transcript: Transcript) -> Transcript:
        from deepmultilingualpunctuation import PunctuationModel  # type: ignore[import]
        model = PunctuationModel()
        restored = [
            seg.model_copy(update={"text": model.restore_punctuation(seg.text)})
            for seg in transcript.segments
        ]
        return transcript.model_copy(update={"segments": tuple(restored)})
```

**지원 언어:** 영어, 한국어, 독일어, 프랑스어, 중국어 등.

---

### Strategy 3: `SemanticBoundaryStrategy` — 의미 경계 탐지

**`available()` → `sentence-transformers` 설치 여부**

타임스탬프 기반 분절의 한계를 보완한다. 인접 세그먼트 간 임베딩 코사인 유사도가 임계값 아래로 떨어지는 지점을 `segmentation.py`의 `BoundaryDetector`에 힌트로 전달한다.

```python
class SemanticBoundaryStrategy:
    """sentence-transformers 기반 의미 경계 탐지.

    Transcript 자체를 변경하지 않는다.
    대신 segmentation.py에 주입할 SemanticBoundaryDetector 인스턴스를 생성한다.
    (engine.py에서 별도로 주입 — 아래 통합 진입점 참고)
    """
    name = "semantic-boundary"

    def available(self) -> bool:
        return importlib.util.find_spec("sentence_transformers") is not None

    def process(self, transcript: Transcript) -> Transcript:
        return transcript  # Transcript 수정 없음 — detector 주입으로 효과 발현

    def make_detector(self, threshold: float = 0.5) -> "SemanticBoundaryDetector":
        return SemanticBoundaryDetector(threshold=threshold)


class SemanticBoundaryDetector:
    """segmentation.py BoundaryDetector 프로토콜 구현체."""

    def __init__(self, threshold: float = 0.5) -> None:
        self.threshold = threshold
        self._model: object | None = None

    def _get_model(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return self._model

    def detect(self, segments: list) -> list[int]:
        if len(segments) < 3:
            return []
        model = self._get_model()
        texts = [s.text for s in segments]
        embeddings = model.encode(texts, convert_to_tensor=True)  # type: ignore[union-attr]
        boundaries = []
        for i in range(len(embeddings) - 1):
            a, b = embeddings[i], embeddings[i + 1]
            sim = float((a * b).sum() / (a.norm() * b.norm()))
            if sim < self.threshold:
                boundaries.append(i + 1)
        return boundaries
```

**사용 모델:** `paraphrase-multilingual-MiniLM-L12-v2` (~120MB, 한국어 포함 다국어, CPU 실시간 처리 가능)

---

## 5. 통합 진입점

**engine.py 변경 (최소 — 두 줄 추가):**

```python
# engine.py — line ~178 (transcript fetch 직후, segment_transcript 직전)
from chew.pipeline.preprocessing import TranscriptPreprocessor, SemanticBoundaryStrategy

preprocessor = TranscriptPreprocessor()          # 기본 3전략
transcript, prep_stats = preprocessor.process(transcript)

# SemanticBoundaryStrategy가 available하면 detector 주입
_semantic = SemanticBoundaryStrategy()
detector = _semantic.make_detector() if _semantic.available() else None

manifest = segment_transcript(
    transcript, selected_chapters, policy, detector=detector, depth=config.depth
)
```

**`preprocess_transcript()` 공개 함수 (편의 래퍼):**

```python
def preprocess_transcript(
    transcript: Transcript,
    strategies: list[PreprocessingStrategy] | None = None,
) -> tuple[Transcript, PreprocessingStats]:
    """기본 TranscriptPreprocessor로 전처리. engine.py에서 호출."""
    return TranscriptPreprocessor(strategies).process(transcript)
```

---

## 6. 새 extras 그룹

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

## 7. Token 절감 측정

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

## 8. 테스트 계획

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

## 9. 완료 기준

- [ ] `preprocessing.py` 구현 및 unit test 통과
- [ ] `engine.py` 통합 — 기존 테스트 전부 통과 (regression 없음)
- [ ] `segmentation.py` — `SemanticBoundaryDetector` 주입 인터페이스 추가
- [ ] `pyproject.toml` — `[preprocess]` extras 추가
- [ ] CLI 전처리 통계 출력
- [ ] `uv run --extra dev pytest` 전체 통과
- [ ] `uv run --extra dev ruff check .` 통과
- [ ] `uv run --extra dev mypy src/chew` 통과

---

## 10. 미래 확장 (이번 구현 범위 밖)

- **Notion 연동** — `chew notion` 명령어 (추후)
- **Knowledge Graph** — 영상 간 임베딩 유사도 기반 연결 (추후)
- **Cheap Frontier 티어 라우팅** — Haiku/Flash for topics, Sonnet for compose (추후)
- **뉴스/논문 소스** — URL input 확장 (추후)
