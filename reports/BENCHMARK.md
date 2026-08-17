# YouTube Summarizer Kit (`chew`) Performance Benchmark & Tracing Guide

본 문서는 `chew` (`youtube-summarizer-kit`) 파이프라인의 성능 측정(Benchmarking), 프로파일링 및 릴리스 배포 시 버전별 최신 벤치마크 성능을 기록하고 추적하기 위한 공식 가이드 문서입니다.

---

## 🚀 1. 릴리스 버전별 최신 성능 기록 (Release Performance History)

새로운 릴리스 태그(`v*.*.*`)를 배포하거나 주요 성능 개선을 반영할 때마다, 기준 영상(`https://www.youtube.com/watch?v=NAumQObJEwM`, 약 25분)으로 측정한 **최고 성능 수치(Best Benchmark Score)**를 본 표에 기록합니다.

| 릴리스 태그 | 커밋 해시 | 측정 기준 비디오 | 총 소요 시간 | 생성 태스크 수 | 동시성 제한 | 비고 / 주요 변경 사항 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`v0.1.0-alpha`** | [`2740d68`](https://github.com/SHcommit/youtube-summerizer-kit/commit/2740d68) | `NAumQObJEwM` (25분) | **30분 00초+** | 61개 | `concurrency=2` | Baseline (비최적화 초기 버전) |
| **`v0.1.0-beta`** | [`b250492`](https://github.com/SHcommit/youtube-summerizer-kit/commit/b250492) | `NAumQObJEwM` (25분) | **1분 50초** ⚡ | 11개 | `concurrency=8` | 동적 챕터 병합 + 동시성 8 향상 |
| **`v0.1.0` (최신)** | [`e401654`](https://github.com/SHcommit/youtube-summerizer-kit/commit/e401654) | `NAumQObJEwM` (25분) | **1분 50초** ✅ | 11개 | `concurrency=8` | core 패키지 `chew` 리팩터링 완료 |

---

## 🛠️ 2. 성능 측정 및 벤치마크 실행법 (How to Run Benchmarks)

### 2.1 실시간 요약 벤치마크 실행
실제 유튜브 비디오 또는 로컬 미디어를 대상으로 전체 요약 파이프라인을 실행하고 소요 시간을 측정합니다.

```bash
# 1. 이전 실행 캐시 초기화 (정확한 측정을 위해 상태 DB 비움)
uv run python -c "import sqlite3; from pathlib import Path; from platformdirs import user_data_path; db = sqlite3.connect(Path(user_data_path('youtube-summarizer-kit', appauthor=False)) / 'state.sqlite3'); db.execute('DELETE FROM jobs'); db.execute('DELETE FROM runs'); db.commit()"

# 2. time 명령어를 조합하여 chew 요약 실행
time uv run --extra youtube chew 'https://www.youtube.com/watch?v=NAumQObJEwM'
```

---

### 2.2 벤치마크 카탈로그 및 정량적 비교 실행
내장 벤치마크 러너를 이용해 제공업체 및 런타임 간 처리 속도를 정량 분석합니다.

```bash
# 내장 벤치마크 가상 환경 실행
uv run --extra dev pytest tests/test_benchmark.py
```

---

## 📊 3. 모니터링 및 측정 지표 (Key Metrics to Track)

성능 개선 작업 시 반드시 아래 **5대 측정 지표**를 확인하고 전후 수치를 비교해야 합니다:

1. **전체 요약 소요 시간 (Total Runtime)**: 전체 파이프라인 시작부터 마크다운 파일 저장까지의 시간 (목표: < 2분).
2. **생성된 태스크/세그먼트 개수 (Job/Segment Count)**: 동적 챕터 병합 후 수립된 DAG 태스크의 수 (목표: 30분 비디오 기준 11개 이하).
3. **LLM/CLI 호출 횟수 및 라운드트립 지연 시간 (Call Count & Latency)**: 에이전트/LLM에 요청한 횟수 및 1회당 응답 속도.
4. **동시성 워커 처리 수 (Harness Concurrency)**: 백엔드 워커가 동시에 처리 중인 태스크 수 (`concurrency=8`).
5. **재시도/복구 횟수 (Retry & Repair Count)**: 오류 발생 시 재시도된 횟수 (목표: 0회).

---

## 📐 4. 개발자 및 AI 에이전트를 위한 성능 개선 규칙 (Guidelines)

1. **새로운 기능 추가 또는 파이프라인 수정 시**:
   * 수정 완료 후 반드시 `time uv run --extra youtube chew 'https://www.youtube.com/watch?v=NAumQObJEwM'`를 수행하여 이전 릴리스 수치(1분 50초) 대비 회귀(Regression)가 없는지 검증합니다.
2. **배포(Release Tag) 작성 시**:
   * 새로운 태그를 작성하기 전 최신 측정 수치를 본 문서의 `1. 릴리스 버전별 최신 성능 기록` 표에 업데이트하고 커밋합니다.
3. **보고서 동기화**:
   * 아키텍처나 스케줄러 로직이 변경된 경우 [`reports/performance_analysis.md`](file:///Users/yangseunghyeon/Development/youtube-summarizer-kit/reports/performance_analysis.md) 및 [`AGENTS.md`](file:///Users/yangseunghyeon/Development/youtube-summarizer-kit/AGENTS.md)를 함께 갱신합니다.
