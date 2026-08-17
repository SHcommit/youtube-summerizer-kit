# YouTube Summarizer Kit (`chew`) Performance Benchmark & Tracing Guide

본 문서는 `chew` (`youtube-summarizer-kit`) 파이프라인의 OpenTelemetry 관측성(Observability), Jaeger 벤치마킹 대시보드 시각화, 프로파일링 및 릴리스 배포 시 버전별 최신 벤치마크 성능을 기록하고 추적하기 위한 공식 가이드 문서입니다.

---

## 1. 릴리스 버전별 최신 성능 기록 (Release Performance History)

새로운 릴리스 태그(`v*.*.*`)를 배포하거나 주요 성능 개선을 반영할 때마다, 기준 영상(`https://www.youtube.com/watch?v=NAumQObJEwM`, 약 25분)으로 측정한 최신 최고 성능 수치를 본 표에 기록합니다.

| 릴리스 태그 | 커밋 해시 | 측정 기준 비디오 | 총 소요 시간 | 생성 태스크 수 | 동시성 제한 | 비고 / 주요 변경 사항 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`v0.1.0-alpha`** | [`2740d68`](https://github.com/SHcommit/youtube-summerizer-kit/commit/2740d68) | `NAumQObJEwM` (25분) | **30분 00초+** | 61개 | `concurrency=2` | Baseline (비최적화 초기 버전) |
| **`v0.1.0-beta`** | [`b250492`](https://github.com/SHcommit/youtube-summerizer-kit/commit/b250492) | `NAumQObJEwM` (25분) | **1분 50초** | 11개 | `concurrency=8` | 동적 챕터 병합 + 동시성 8 향상 |
| **`v0.1.0` (최신)** | [`e401654`](https://github.com/SHcommit/youtube-summerizer-kit/commit/e401654) | `NAumQObJEwM` (25분) | **1분 50초** | 11개 | `concurrency=8` | core 패키지 `chew` 리팩터링 완료 |

---

## 2. 오픈소스 트레이싱 & 벤치마크 시각화 (OpenTelemetry & Jaeger UI)

`chew`는 CNCF 표준 **OpenTelemetry (OTel)** 트레이싱을 내장하고 있어 오픈소스 **Jaeger** 대시보드 UI를 통해 파이프라인의 실시간 구간별 실행 지연시간 Waterfall 그래프를 시각적으로 직접 볼 수 있습니다.

### 2.1 Jaeger 트레이싱 대시보드 구동 (OpenTelemetry + Jaeger)

```bash
# 1. Jaeger All-in-One 오픈소스 서버 구동 (Docker 1줄 실행)
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

# 2. chew 요약 실행 (OpenTelemetry 트레이스가 Jaeger로 자동 전송됨)
chew 'https://www.youtube.com/watch?v=NAumQObJEwM'

# 3. 브라우저에서 Jaeger 웹 UI 접속하여 시각화 그래프 확인
open http://localhost:16686
```

---

### 2.2 로컬 대시보드 UI 명령어 (`chew dashboard`)
별도의 서버 없이 local HTML 대시보드 UI를 띄워 실시간 트레이스 waterfall 그래프를 확인할 수 있습니다:

```bash
# 웹 브라우저로 대시보드 UI 구동
chew dashboard
# 또는
chew ui
```

---

### 2.3 파이프라인 실행 워터폴 시각화 (Pipeline Trace Gantt Diagram)

```mermaid
gantt
    title YouTube Summarizer Pipeline Execution Trace Waterfall (1m 50s)
    dateFormat  ss.SSS
    axisFormat  %S초
    
    section 자막 취득 (Transcript)
    Transcript Acquisition (ko/en) :active, t1, 00.000, 03.200
    
    section 세그먼테이션 (Segmentation)
    Dynamic Chapter Coalescing (30 -> 5) :crit, s1, 03.200, 03.250
    
    section DAG 스케줄러 실행 (Concurrency: 8)
    Topic Job 1 (chapter-001) :done, j1, 03.250, 18.100
    Topic Job 2 (chapter-002) :done, j2, 03.250, 19.300
    Topic Job 3 (chapter-003) :done, j3, 03.250, 17.800
    Chapter Job 1 (chapter-001) :done, j4, 18.100, 31.400
    Chapter Job 2 (chapter-002) :done, j5, 19.300, 33.200
    Compose Job (Knowledge Pack) :active, j6, 95.100, 108.500
    
    section 최종 마크다운 생성 (Output)
    Output File Generation (chew-output) :a1, 108.500, 108.550
```

---

## 3. 모니터링 및 측정 지표 (Key Metrics to Track)

성능 개선 작업 시 반드시 아래 5대 측정 지표를 확인하고 전후 수치를 비교해야 합니다:

1. **전체 요약 소요 시간 (Total Runtime)**: 전체 파이프라인 시작부터 마크다운 파일 저장까지의 시간 (목표: < 2분).
2. **생성된 태스크/세그먼트 개수 (Job/Segment Count)**: 동적 챕터 병합 후 수립된 DAG 태스크의 수 (목표: 30분 비디오 기준 11개 이하).
3. **LLM/CLI 호출 횟수 및 라운드트립 지연 시간 (Call Count & Latency)**: 에이전트/LLM에 요청한 횟수 및 1회당 응답 속도.
4. **동시성 워커 처리 수 (Harness Concurrency)**: 백엔드 워커가 동시에 처리 중인 태스크 수 (`concurrency=8`).
5. **재시도/복구 횟수 (Retry & Repair Count)**: 오류 발생 시 재시도된 횟수 (목표: 0회).

---

## 4. 개발자 및 AI 에이전트를 위한 성능 개선 규칙 (Guidelines)

1. **새로운 기능 추가 또는 파이프라인 수정 시**:
   * 수정 완료 후 반드시 `time uv run --extra youtube chew 'https://www.youtube.com/watch?v=NAumQObJEwM'`를 수행하여 이전 릴리스 수치(1분 50초) 대비 회귀(Regression)가 없는지 검증합니다.
2. **배포(Release Tag) 작성 시**:
   * 새로운 태그를 작성하기 전 최신 측정 수치를 본 문서의 `1. 릴리스 버전별 최신 성능 기록` 표에 업데이트하고 커밋합니다.
3. **보고서 동기화**:
   * 아키텍처나 스케줄러 로직이 변경된 경우 [`reports/performance_analysis.md`](file:///Users/yangseunghyeon/Development/youtube-summarizer-kit/reports/performance_analysis.md) 및 [`AGENTS.md`](file:///Users/yangseunghyeon/Development/youtube-summarizer-kit/AGENTS.md)를 함께 갱신합니다.
