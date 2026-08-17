# YouTube Summarizer Kit (`chew`)

[![CI](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | **한국어**

> **Don't watch, let AI chew it!**  
> YouTube 영상과 로컬 오디오·영상 파일을 재사용 가능한 지식(**Knowledge Pack**)으로 분석하고, 1초 만에 블로그·학습노트·옵시디언 위키노트로 목적에 맞춰 재조립하는 로컬 중심 CLI 도구입니다.

---

## 💡 왜 `chew`를 만들었는가? (Motivation)

1~2시간짜리 유명 기술 발표, 팟캐스트, 강의 영상을 볼 시간은 부족하고, 기존 AI 요약 도구는 무성의한 5줄 요약만 내놓아 핵심 기술 맥락과 타임스탬프 근거를 모두 잃어버립니다.

`chew`는 이 문제를 해결하기 위해 탄생했습니다:

- **영상 보지 말고, AI가 씹어 삼켜드립니다 (Let AI Chew It)**: 긴 미디어를 장·소주제 단위로 적응형 분할하여 AI가 깊이 있게 분석(Chew)하고 구조화합니다.
- **한 번 분석(Analyze Once), 어디서나 재조립**: 영상 1개를 **Knowledge Pack**으로 한 번만 분석해 두면, LLM 재호출이나 비싼 API 비용 없이 1초 만에 기술 블로그, 학습 노트, 옵시디언 위키노트로 목적에 맞춰 즉시 재조립합니다.
- **내 로컬 AI 세션 그대로 (Zero API Cost)**: API 키 발급이나 구독료 없이, 내 컴퓨터에 이미 설치된 Codex, Gemini, Claude, Ollama, Antigravity CLI 세션을 그대로 활용합니다.

---

## ✨ 핵심 기능 (Key Features)

- ⚡ **적응형 장·소주제 병렬 분석**: 영상 길이에 맞춰 챕터와 5~10분 단위 소주제를 동적으로 쪼개어 독립된 병렬 큐에서 분석합니다.
- 🎚️ **3단계 요약 강도 조절 (`--depth`)**: 빠른 훑어보기용 `quick` (short/brief), 균형 잡힌 `detailed` (기본값), 내용이 꽉 차는 심층 요약 `deep`을 자치 선택합니다.
- 🔄 **중단 재개 & 1초 재조립**: 네트워크나 AI CLI가 끊겨도 SQLite WAL 상태 머신이 작업 위치를 기억하여 완료된 구간부터 이어하며, 동일 영상은 1초 만에 다른 양식으로 새로 생성합니다.
- 🎙️ **자막 자동 수집 & 로컬 Whisper Fallback**: 유튜브 수동/자동 자막을 먼저 수집하고, 자막이 없는 미디어는 로컬 `faster-whisper`로 원본 위치에서 직접 음성 인식합니다.
- 🚀 **16.3배 성능 향상 & OpenTelemetry 관측성**: 동적 챕터 한계 조율과 동시성 확장(8개)으로 30분 걸리던 분석을 **1분 50초**로 단축했으며, OpenTelemetry Jaeger UI 기반 실시간 대시보드를 제공합니다.

---

## ⚙️ 설치 및 빠른 시작 (Installation & Getting Started)

`chew` 명령어를 실행하기 전 **최초 1회 설치**가 필수입니다. Python 3.12 이상 환경에서 아래 **1-Click 자동 설치 스크립트**를 실행하면 1초 만에 모든 의존성 설치, 전역 `chew` 명령어 등록, 기본 설정 파일(`CHEW.md` 및 `.chew/profiles/`) 초기화가 한번에 완료됩니다.

### 1단계: 1-Click 자동 설치

```bash
git clone https://github.com/SHcommit/youtube-summerizer-kit.git
cd youtube-summarizer-kit

# 1-Click 자동 설치 (의존성 설치, 전역 'chew' 등록, CHEW.md 및 .chew/profiles/ 자동 초기화)
./setup.sh
```

### 2단계: 실행 예시

설치가 완료되면 터미널 어디서나 **`chew 'URL'`**만 입력하여 즉시 실행할 수 있습니다:

```bash
# 기본 상세 요약 (완료 시 마크다운 저장 및 파이썬 프로세스 자동 종료)
chew 'https://www.youtube.com/watch?v=VIDEO_ID'

# 내용이 꽉 차는 깊은 심층 요약 (--depth deep)
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth deep

# 빠른 초간단 요약 (--depth quick / short / brief)
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth quick

# 분석된 영상 기반 목적별 문서 1초 재조립
chew 블로그 'https://www.youtube.com/watch?v=VIDEO_ID'
chew 학습 'https://www.youtube.com/watch?v=VIDEO_ID'
chew 옵시디언 'https://www.youtube.com/watch?v=VIDEO_ID'

# 로컬 오디오·영상 파일 요약 (recording.mp3)
chew ./recordings/meeting.mp3
```

수동 설치 방법 (개발자용):
```bash
pip install -e '.[youtube,dev]'
```

---

## 🛠️ 내부 작동 원리 (How It Works)

`chew` 파이프라인은 입력부터 마크다운 출력까지 4단계 계층으로 작동합니다:

![YouTube Summarizer Kit 사용자 입력과 출력](assets/architecture/ko/user-flow.png)

```text
[입력 URL / 로컬 미디어]
       │
       ▼
 1. Transcript Extraction & Validation (자막 수집 및 자막 미제공 시 Whisper Fallback)
       │
       ▼
 2. Preprocessing & Dynamic Segmentation (적응형 챕터 및 5~10분 소주제 컷팅)
       │
       ▼
 3. Parallel Async LLM Synthesis (Bounded Concurrency DAG 스케줄러 & AI Harness)
       │
       ▼
 4. Knowledge Pack Compilation (중간 지식 아티팩트 생성)
       │
       ▼
 [Multi-Format Output: Digest / Blog / Study / Obsidian Markdown]
```

![YouTube Summarizer Kit 내부 상세 처리 흐름](assets/architecture/ko/internal-pipeline.png)

### 1. 자막 수집 및 정규화 (Transcript Extraction)
- 수동 자막 → 자동 생성 자막 → `youtube-transcript-api` 순서로 수집하고 품질(커버리지, 중복, 무음 구간)을 검사합니다.
- 자막이 없거나 품질 기준 미달 시 `whisper_fallback: true` 설정이 켜져 있으면 로컬 `faster-whisper`로 음성을 인식합니다.

### 2. 적응형 동적 분할 (Adaptive Dynamic Segmentation)
- 영상 길이에 비례하여 챕터를 조율(30분 미만 5개 상한)하고 5~10분 크기의 독립된 소주제로 쪼갭니다.

### 3. 병렬 LLM 합성 (Parallel Async LLM Processing)
- Bounded Concurrency DAG 스케줄러가 독립된 소주제 작업을 백그라운드 큐에서 병렬 처리합니다.
- 로컬 세션(Codex, Gemini, Claude, Ollama, AGY)을 공통 Harness 인터페이스로 제어합니다.

### 4. Knowledge Pack 및 목적별 재조립 (Multi-Format Output)
- 핵심 분석 결과를 담은 노란색 **Knowledge Pack**을 zstd 압축 아티팩트로 저장합니다.
- 한 번 생성된 Knowledge Pack은 1초 만에 블로그, 학습 노트, 옵시디언 노트로 즉시 재조립됩니다.

---

## 🎚️ 요약 강도 및 문체 설정 (Configuration)

### 요약 강도 선택 (`--depth`)

CLI 옵션(`--depth` / `--요약강도` / `-d`) 또는 `CHEW.md` 파일에서 요약의 밀도를 3단계로 지정할 수 있습니다:

- **`quick` (`short` / `brief` / `초간단` / `핵심`)**: 핵심 주요 마일스톤 위주의 빠른 훑어보기용 초간단 요약
- **`detailed` (`상세`, 기본값)**: 챕터별 주요 소주제와 근거 타임스탬프를 포함한 균형 잡힌 상세 요약
- **`deep` (`심층` / `꽉찬`)**: 영상의 모든 챕터, 디테일, 기술적 맥락과 세부 쟁점을 꽉 채운 깊은 심층 분석 요약

### 문체 및 양식 커스텀 (`CHEW.md` & `.chew/profiles/`)

`./setup.sh` 실행 시 생성되는 파일에서 블로그 문체, 독자 수준, 출력 레이아웃을 자유롭게 커스텀할 수 있습니다:

```text
CHEW.md               # 프로젝트 기본 전역 설정 및 공통 LLM 작성 지침
.chew/profiles/
├── blog.md           # 블로그 톤/어조 및 문서 레이아웃 양식 지정
├── study.md          # 학습 노트 항목 및 Q&A 구조 지정
└── obsidian.md       # 옵시디언 [[위키링크]] 서식 지정
```

---

## 🚀 성능 최적화 & OpenTelemetry 대시보드

### 16.3배 성능 향상 (Performance Boost)

기존 파이프라인의 30분 지연 병목 현상을 해결하여 **16.3배 성능 향상**을 달성했습니다:

| 항목 | 개선 전 (Baseline) | 개선 후 (Optimized) | 향상률 |
|---|---|---|---|
| 25분 기술 영상 분석 시간 | 30분 00초 (1,800s) | **1분 50초 (110s)** | **16.3배 단축** |
| 파이프라인 생성 작업 수 | 61개 미세 태스크 | **11개 응축 태스크** | 82% 감소 |
| AI Harness 동시성 수 | 2개 제한 | **8개 병렬 처리** | 4배 확대 |

상세 분석 보고서: [`reports/performance_analysis.md`](reports/performance_analysis.md)

### OpenTelemetry Jaeger UI 대시보드

관측성 분석이 필요한 개발자는 실시간 스팬 지연 시간 및 분할 추적 그래프를 오픈소스 Jaeger UI에서 확인할 수 있습니다:

```bash
# 선택적 관측성 패키지 설치
pip install -e '.[telemetry]'

# OpenTelemetry Trace 대시보드 생성 및 Jaeger UI 연결 안내
chew benchmark-dashboard
```

---

## 🛠️ CLI 명령어 요약

| 한국어 명령 | 영어 명령 | 옵션 및 역할 |
|---|---|---|
| `chew 'URL'` | `chew 'URL'` | 기본 요약 (URL 입력 생략 시 대화형 프롬프트) |
| `chew 'URL' -d deep` | `chew 'URL' -d deep` | 내용이 꽉 차는 심층 요약 (`quick`, `detailed`, `deep`) |
| `chew 블로그 'URL'` | `chew blog 'URL'` | 설정한 블로그 문체 및 레이아웃으로 1초 재조립 |
| `chew 학습 'URL'` | `chew study 'URL'` | 개념, 자가 점검 질문, 추가 학습 항목 중심 재조립 |
| `chew 옵시디언 'URL'` | `chew obsidian 'URL'` | `[[위키링크]]` 기반 옵시디언 노트 생성 |
| `chew 상태 [RUN_ID]` | `chew status [RUN_ID]` | 진행률 및 백그라운드 작업 상태 확인 |
| `chew 이어하기 [RUN_ID]` | `chew resume [RUN_ID]` | 중단된 작업 위치부터 바로 이어하기 |
| `chew 진단` | `chew doctor` | 설치된 AI CLI 및 로그인 인증 상태 진단 |
| `chew 정리` | `chew cleanup` | 저장소 용량 및 보존 정책에 따른 정리 |

---

## 🧩 기술 스택 & 아키텍처 (Tech Stack & Architecture)

이 프로젝트는 **포트와 어댑터(Ports & Adapters / 육각형 아키텍처)** 구조를 엄격히 준수합니다. 상세 개발 지침은 [`AGENTS.md`](AGENTS.md)를 참고하세요.

```
src/chew/
├── core/         # Layer 1: 도메인 엔티티, SHA-256 식별자, 프롬프트
├── pipeline/     # Layer 2: 계층적 분석 파이프라인, DAG 스케줄러, 출력 생성기
├── storage/      # Layer 3: SQLite WAL 상태 머신 및 zstd 아티팩트 저장소
├── harness/      # Layer 4: AI 런타임 연결 어댑터 (Codex, Gemini, Claude, Ollama, Antigravity)
├── transcripts/  # Layer 5: 자막 수집 및 음성 인식 어댑터 (YouTube API, yt-dlp, Whisper)
├── app/          # Layer 6: 응용 오케스트레이션 서비스 및 DI 컨테이너
├── retention/    # Layer 7: 저장 보존 및 정리 정책
├── benchmark/    # Layer 8: 품질 평가 벤치마크 프레임워크
└── cli/          # Layer 9: 이중 언어(한/영) Typer CLI 커맨드
```

---

## 📄 라이선스 & 버전 이력

- **License**: [MIT License](LICENSE)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
