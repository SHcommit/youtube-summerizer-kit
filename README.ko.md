# YouTube Summarizer Kit (`chew`)

[![CI](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[English](README.md) | **한국어**

![YouTube Summarizer Kit Banner](assets/architecture/social-preview.png)

YouTube 영상과 로컬 오디오·영상 파일을 재사용 가능한 지식으로 변환하는 로컬 중심 CLI(`chew`)입니다.
일회성 요약을 출력하는 대신 자막을 검증하고, 장·소주제를 병렬 분석하여 다양한 포맷 문서로 조립합니다.

아키텍처 역할에서 `chew`는 원문을 근거 기반 Knowledge Tree와 재사용 가능한 Knowledge Pack으로 컴파일하는 **Grounded Knowledge Compiler(근거 기반 지식 컴파일러)**입니다.

- `chew <URL>` 명령으로 실행합니다.
- 챕터를 인식하고 소주제 단위로 병렬 처리하여 긴 영상도 안정적으로 분석합니다.
- 중간에 네트워크나 AI CLI가 끊겨도 완료된 작업부터 이어합니다.
- 같은 URL과 분석 설정은 run-id 없이도 기존 Knowledge Pack을 재사용합니다.
- 직접 지정한 로컬 미디어는 원본 위치에서 음성 인식하고, 파일을 옮기거나 이름을 바꿔도 콘텐츠 해시로 기존 분석을 재사용합니다.
- Codex CLI, Gemini CLI, Claude Code / Claude CLI, Ollama, Antigravity CLI(`agy`)를 공통 Harness 인터페이스로 연결합니다.
- 블로그 문체와 학습 방식은 긴 CLI 옵션 대신 Markdown 파일로 관리합니다.

---

## 왜 `chew`인가?

1~2시간짜리 유명 기술 발표, 팟캐스트, 강의 영상을 볼 시간은 부족하고, 기존 AI 요약 도구는 무성의한 5줄 요약만 내놓아 핵심 기술 맥락과 타임스탬프 근거를 모두 잃어버립니다.

`chew`는 이 문제를 해결하기 위해 만들어졌습니다:

- **영상 보지 말고, AI가 씹어 삼켜드립니다 (Don't watch, let AI chew it)**: 긴 미디어를 장·소주제 단위로 쪼개어 AI가 깊이 있게 분석(Chew)하고 구조화합니다.
- **한 번 분석(Analyze Once), 어디서나 재조립**: 영상 1개를 **Knowledge Pack**으로 한 번만 분석해 두면, LLM 재호출이나 비싼 API 비용 없이 1초 만에 기술 블로그, 학습 노트, 옵시디언 위키노트로 목적에 맞춰 즉시 재조립합니다.
- **내 로컬 AI 세션 그대로**: API 키 발급이나 구독료 없이, 내 컴퓨터에 이미 설치된 Codex, Gemini, Claude, Ollama, Antigravity CLI 세션을 그대로 활용합니다.

> 현재는 자막 중심 분석입니다. 화면에만 나타나는 도표·코드·장면이 핵심인 영상은 정보가 빠질 수 있으며, 프레임 기반 멀티모달 분석은 아직 기본 파이프라인에 포함되지 않습니다.

---

## 필수 다운로드 및 설치 (Download & Getting Started)

`chew` 명령어를 터미널에서 구동하기 전 **반드시 다운로드 및 환경 설치 과정을 최우선으로 완료**해야 합니다. Python 3.12 이상이 필요하며, 사용하시는 선호 패키지 관리자에 맞춰 아래 1줄 명령어로 설치할 수 있습니다:

### 패키지 관리자 1줄 설치 (권장)

```bash
# Homebrew 설치 (macOS / Linux 권장)
brew install SHcommit/tap/chew

# pipx 전역 독립 환경 설치
pipx install youtube-summarizer-kit

# uv 초고속 전역 CLI 설치
uv tool install youtube-summarizer-kit

# pip 설치
pip install youtube-summarizer-kit
```

### 소스코드 클론 & 1-Click 자동 설치

아래 **1-Click 자동 설치 스크립트**를 실행하면 1초 만에 저장소 클론, 의존성 설치, 전역 `chew` 명령어 등록, 그리고 기본 설정 파일(`CHEW.md` 및 `.chew/profiles/`) 자동 초기화가 완료됩니다:

```bash
# 1. 저장소 클론 (다운로드)
git clone https://github.com/SHcommit/youtube-summerizer-kit.git
cd youtube-summarizer-kit

# 2. 1초 자동 설치, chew 명령어 전역 등록, CHEW.md & .chew/profiles/ 자동 초기화
./setup.sh
```

설치 후에는 터미널에서 **`chew 'URL'`**만 입력하여 즉시 실행할 수 있습니다:

```bash
# 기본 상세 요약 실행 (완료 시 파이썬 프로세스 자동 종료 및 마크다운 파일 저장)
chew 'https://www.youtube.com/watch?v=VIDEO_ID'

# 내용이 꽉 차는 깊은 심층 요약 실행
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth deep

# 빠른 초간단 요약 실행 (quick / short / brief)
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth quick

# 분석 완료된 기존 영상 목적별 문서 1초 재조립
chew 블로그 'https://www.youtube.com/watch?v=VIDEO_ID'
chew 학습 'https://www.youtube.com/watch?v=VIDEO_ID'
chew 옵시디언 'https://www.youtube.com/watch?v=VIDEO_ID'

# 로컬 미디어 녹음 파일 요약
chew 요약 ./recordings/meeting.mp3
```

개발 도구까지 포함한 수동 설치 방법:

```bash
pip install -e '.[youtube,dev]'
```

선택적 `faster-whisper` fallback은 모델과 영상 오디오를 자동으로 내려받지 않도록 기본값이 비활성화되어 있습니다. 사용하려면 `pip install -e '.[youtube,whisper]'`로 설치하고 `CHEW.md`에 `whisper_fallback: true`를 지정합니다. 처음 실제로 음성 인식을 실행할 때는 `faster-whisper`가 모델을 내려받을 수 있습니다.

YouTube timedtext가 `HTTP 429`를 반환하면 `yt-dlp`는 설치된 Node.js runtime과 공식 EJS challenge component를 자동으로 사용합니다. 그래도 제한되면 사용자가 확보한 스크립트를 제공합니다.

```bash
chew 요약 --transcript ./captions.vtt \
  --source-url "https://www.youtube.com/watch?v=VIDEO_ID"
```

`chew`는 브라우저 로그인, cookie-file, 브라우저 프로필 기반 자막 fallback을 제공하지 않으며 자막 복구를 위해 브라우저 쿠키, Keychain 값, 비밀번호, 프록시 credential을 읽지 않습니다. VTT/SRT의 cue timing은 보존하며 일반 TXT 줄에는 결정적인 시간 범위를 부여합니다. 영상·계정이 제한된 경우 YouTube가 자막을 거부할 수 있습니다. provider 제한과 오류 이유는 [자막 획득 문서](docs/wiki/transcript-acquisition.md)를 참고하세요.

로컬 오디오·영상 파일 입력에도 `whisper` extra가 필요하지만, YouTube fallback 설정을 켤 필요는 없습니다.

```bash
pip install -e '.[youtube,whisper]'
```

설치 후 환경 점검:

```bash
chew 진단
chew 진단 --json
```

---

## 한 번의 실행이 진행되는 방식

YouTube URL, 로컬 미디어, 또는 이미 가진 자막으로 시작합니다. `chew`는 원문을 검증하고 한 번 분석해 재사용 가능한 Knowledge Pack을 저장한 뒤, 선택한 출력 형식으로 렌더링합니다.

![YouTube Summarizer Kit 사용자 흐름](assets/architecture/ko/user-flow.png)

호환되는 Knowledge Pack이 이미 있으면 분석을 반복하지 않고 재조립합니다. 중단되었거나 인증이 필요한 실행도 완료된 checkpoint를 유지합니다. `chew 상태`로 확인하고 가능한 경우 `chew 이어하기`로 계속할 수 있습니다. 공개 자막을 가져오지 못하면 사용자가 제공한 VTT, SRT, TXT 자막으로 복구할 수 있습니다.

## 외부 경계

애플리케이션은 식별, 정책, grounding, Knowledge Pack 조립, 출력 렌더링을 하나의 코어 안에 둡니다. 외부 시스템과는 목적이 분명한 adapter로만 연결합니다.

![YouTube Summarizer Kit 외부 경계](assets/architecture/ko/external-boundaries.png)

최종 추론은 Frontier runtime이 담당합니다. Ollama는 선택 사항이며, 활성화해도 제한된 자막 annotation에만 사용되고 최종 요약이나 판단을 대체하지 않습니다. SQLite와 content-addressed artifact는 로컬 상태를 보존합니다. OpenTelemetry/Jaeger는 선택적 관측 도구이지 실행에 필요한 의존성이 아닙니다.

Knowledge Pack renderer는 Digest, Blog, Study, Obsidian, JSON처럼 실제로 재사용할 콘텐츠를 만듭니다. 반면 interface presenter는 완료된 작업을 터미널 문구나 machine JSON으로 전달할 뿐입니다. 현재 inbound interface는 CLI이고, HTTP·MCP·별도 배포 가능한 웹 클라이언트는 미래 계약 소비자로만 표시합니다. 아직 공개 API나 웹 UI는 포함하지 않습니다.

공통 자연어 요청 분석을 위한 [`intent-analysis`](modules/intent-analysis/README.md)와 Pack 기반 후속 조사를 위한 [`research-engine`](modules/research-engine/README.md)는 문서 경계만 존재하는 미래 모듈입니다. 아직 설치·호출·의존할 필요가 없습니다.

## 내부 파이프라인

핵심 경로는 검증된 원문을 근거가 있는 재사용 지식으로 만든 뒤, 각 출력 프로필을 렌더링합니다.

![YouTube Summarizer Kit 내부 파이프라인](assets/architecture/ko/internal-pipeline.png)

Knowledge Pack이 재사용 경계입니다. evidence span과 timestamp는 로컬에서 raw transcript와 대조해 grounding하며, 저장된 pack에서 출력 프로필을 결정론적으로 렌더링합니다. 정책, 지속 checkpoint, structured log, tracing은 콘텐츠 자체가 아니라 이 실행 경로를 지원합니다. 모듈별 위치는 [agent index](docs/agent-index.md), 자막 획득 제한과 복구는 [자막 획득 문서](docs/wiki/transcript-acquisition.md)를 참고하세요.

### OpenTelemetry Jaeger 실시간 trace 예시

![OpenTelemetry Jaeger Trace Dashboard](assets/architecture/jaeger-trace-dashboard.png)

---

## 현재 지원 상태

| 실행기 | 사용 가능 | 로그인 확인 | 로그인/실행 방법 |
|---|---|---|---|
| Codex CLI (`codex`) | 예 | `codex login status`로 사전 확인 | 필요하면 `codex login` |
| Claude Code / Claude CLI (`claude`) | 예 | `claude auth status`로 사전 확인 | 필요하면 `claude`에서 로그인 |
| Gemini CLI (`gemini`) | 예 | 공식 비소모성 상태 명령이 없어 첫 생성 때 확인 | 필요하면 `gemini`에서 로그인 |
| Ollama (`ollama`) | 예 | 로그인 불필요 | 로컬 Ollama 서버 실행 |
| 계층형 Ollama (`layered_ollama`) | 예 | 로그인 불필요 | 1.5B / 7B / 14B 모델 티어(`qwen2.5:*-instruct-q4_K_M`) 설치 후 Ollama 실행 |
| HuggingFace (`huggingface`) | 예 | `HF_TOKEN` 환경 변수 | `HF_TOKEN` 설정 후 `pip install 'chew[huggingface]'` |
| Antigravity CLI / AGY (`agy`) | 예 | 첫 생성 때 확인 / 기존 로컬 세션 사용 | `agy` CLI 설치 및 세션 사용 |

**로컬 LLM은 완전히 선택 사항입니다.** 기본값 `runtime: frontier`는 인증된 Codex, Gemini, Claude만 선택하며 로컬 모델은 제외합니다. 최종 요약과 판단에는 Frontier runtime이 필요하며, 로컬 모델은 요약 task route로 사용할 수 없습니다.

Ollama는 선택적 로컬 모델 다운로드가 필요한 실행기입니다.

| 구성 | 추가 디스크 용량 |
|---|---|
| Codex / Gemini / Claude / Antigravity / HuggingFace | 추가 없음 |
| `ollama` 단일 모델 | ~1–5 GB |
| `layered_ollama` 3개 티어 전체 | 약 15 GB (`q4_K_M` 양자화 기준) |

`chew doctor`를 실행하면 현재 사용 가능한 실행기를 확인하고, 미설치 항목에 대한 설치 안내를 확인할 수 있습니다.

로그인 여부를 사전에 확정할 수 없는 Gemini는 확인된 실행기가 하나도 없을 때 후보가 되고, 첫 생성 요청에서 실제 인증을 검증합니다.

Codex나 Claude처럼 인증 상태를 확인할 수 있는 실행기가 로그아웃 상태라면 다른 준비된 실행기로 넘어갑니다. 특정 실행기를 설정으로 고정했는데 로그인되어 있지 않다면 로그인 명령을 안내하고 실행을 `blocked_auth` 상태로 보존합니다. 로그인 후 `chew 이어하기`를 실행하면 완료된 구간을 다시 처리하지 않고 계속합니다.

이 프로젝트는 사용자의 인증 파일이나 API 키를 직접 읽거나 복사하지 않습니다. 설치된 CLI를 별도 프로세스로 실행하므로 기존 Codex·Gemini·Claude 로그인 세션을 그대로 사용합니다.

---

## Markdown 설정과 출력 문체

프로젝트에서 한 번만 초기화합니다.

```bash
chew 설정 --초기화
```

다음 파일이 생성되며 기존 파일은 덮어쓰지 않습니다.

```text
CHEW.md
.chew/
└── profiles/
    ├── blog.md
    ├── study.md
    └── obsidian.md
```

`CHEW.md` 예시:

```markdown
---
language: ko
default_profile: digest
depth: detailed
runtime: frontier
task_runtimes: {} # 선택: task별 BYOK Frontier runtime. 예: {topic_summary: gemini, compose: codex}
local_accelerator: false # 향후 승인된 저위험 보조 작업용
ollama_model: null # 향후 승인된 로컬 보조 작업용
whisper_fallback: false
# 선택 사항: Ollama 입력 상한. 설정하지 않으면 기존 시간 기반 분절을 유지한다.
max_input_tokens: 4096
reserved_output_tokens: 512
output_verify: true
normalize_transcript: false
preprocess_transcript: false
storage_policy: compact
---

사실과 AI의 추가 설명을 구분한다.
기술 용어는 첫 등장에 짧게 정의하고, 모든 핵심 주장에 영상 근거를 연결한다.
```

`max_input_tokens`와 `reserved_output_tokens`로 보수적 입력 상한을 opt-in할 수 있습니다. 이 값은 provider 청구 토큰이 아니며, 기존 시간 기반 분절을 유지하려면 둘 다 설정하지 않습니다.

`blog`와 `study`에서는 `output_verify: false`로 마지막 LLM 검증 호출을 생략할 수 있습니다. fixture 측정으로 품질 저하가 없음을 확인하기 전까지 기본값 `true`를 유지합니다.

`normalize_transcript: true`는 공백을 정리하고 인접한 중복 자막만 병합합니다. 원문 자막은 근거 source로 별도 보존합니다.

`preprocess_transcript: true`는 여기에 보수적인 로컬 필러 제거를 추가합니다. `pip install 'chew[preprocess]'`를 설치하면 문장부호 복원과 의미 경계 힌트도 선택적으로 적용됩니다. 고정 fixture의 품질·비용 비교가 끝날 때까지 기본값은 꺼져 있습니다.

`task_runtimes`는 opt-in BYOK Frontier routing입니다. map에 없는 task는 기존 `runtime`을 그대로 쓰며, 다른 provider로 자동 전환하지 않습니다. 로컬 runtime은 요약이나 판단 작업에 선택할 수 없습니다. cloud provider별 모델 선택은 adapter가 실제 적용·검증할 수 있을 때 추가합니다.

현재 고정 영어 fixture 비교에서 보수적 필러 제거의 `cl100k_base` 절감은 `1.92%~4.94%`였습니다. 이는 provider 청구 비용이 아닌 tokenizer 비교이며, 기본 활성화 기준 10%에 미달하므로 opt-in을 유지합니다.

대화형 터미널에서 처음 `chew config --init`을 실행하면 Qwen3 4B(약 2.5GB), Qwen3 8B(약 5.2GB), 나중에 설정 중 하나를 선택할 수 있습니다. 확인한 경우에만 `ollama pull` 다운로드가 시작됩니다.

### 요약 강도 및 깊이 설정 (`depth`)

CLI 옵션(`--depth` / `--요약강도` / `-d`) 또는 `CHEW.md` 파일에서 3단계 요약 강도를 자유롭게 선택할 수 있습니다:

- **`quick` (`short` / `brief` / `초간단` / `핵심`)**: 핵심 주요 마일스톤 위주의 빠른 훑어보기용 초간단 요약
- **`detailed` (`상세`, 기본값)**: 챕터별 주요 소주제와 근거 타임스탬프를 포함한 균형 잡힌 상세 요약
- **`deep` (`심층` / `꽉찬`)**: 영상의 모든 챕터, 디테일, 기술적 맥락과 세부 쟁점을 꽉 채운 깊은 심층 분석 요약

```bash
# 빠른 초간단 핵심 요약 (quick / short / brief 모두 사용 가능)
chew '유튜브_URL' --depth quick

# 내용이 꽉 차는 깊은 심층 요약
chew '유튜브_URL' --depth deep
```

본문은 LLM 지침으로 사용됩니다. `.chew/profiles/blog.md` 같은 목적별 파일에서는 문체, 독자 수준, 글의 구성 방식을 추가로 지정할 수 있습니다. 프로젝트 설정은 상위 디렉터리까지 탐색하며, 파일이 없으면 패키지에 포함된 안전한 기본 설정을 사용합니다.

분석 설정과 출력 설정은 분리됩니다. 예를 들어 블로그 문체만 바꿨다면 자막과 소주제를 다시 분석하지 않고 기존 Knowledge Pack에서 블로그 문서만 새로 만듭니다. 프로필별로 다른 `runtime`을 지정하면 캐시되지 않은 출력 재조립에 그 실행기를 사용합니다.

`task_runtimes`는 opt-in BYOK Frontier routing입니다. 각 run은 route, input budget, fallback, 선택 이유가 담긴 immutable Execution Plan을 먼저 기록합니다. map에 없는 task는 `runtime`을 유지하며, 모델 출력은 이 계획을 바꿀 수 없습니다. 로컬 runtime은 요약이나 판단 작업에 선택할 수 없습니다.

중요 source claim의 citation은 모델이 제안한 뒤에도 raw transcript의 segment index, timestamp, quote가 일치할 때만 결과에 연결됩니다. 이 검증은 claim의 사실 여부가 아니라 원문 근거 연결만 보장합니다.

---

## 자막이 없는 영상

일반 경로에서는 영상 미디어를 내려받지 않고 이미 존재하는 텍스트를 수집합니다. 수동 자막, 자동 생성 자막, `youtube-transcript-api` 순서로 시도하며, 셋 모두 사용할 수 없거나 품질 검사를 통과하지 못하면 모델이나 오디오를 몰래 내려받지 않고 로컬 음성 인식 활성화 방법을 안내합니다.

선택적 의존성을 설치하고 `CHEW.md`에서 fallback을 활성화합니다.

```bash
pip install -e '.[youtube,whisper]'
```

```markdown
---
whisper_fallback: true
---
```

이 설정을 켜면 네 번째 fallback이 영상 오디오를 임시 디렉터리에 내려받고 `faster-whisper`로 타임스탬프가 있는 transcript를 로컬에서 새로 만듭니다. 음성 인식이 끝나면 임시 오디오는 삭제됩니다. 최초 실행에는 Whisper 모델 다운로드가 발생할 수 있고 로컬 CPU/GPU 시간을 사용하지만, AI CLI 로그인이나 hosted API quota는 소비하지 않습니다. 앞서 yt-dlp로 확인한 영상 제목과 챕터도 유지됩니다. 정확도는 음질, 화자, 설정한 자막 언어에 따라 달라질 수 있습니다.

---

## 로컬 오디오·영상 파일

YouTube URL을 받는 자리에 기존 로컬 미디어 경로를 넣을 수 있습니다. 경로를 직접 제공한 것 자체가 해당 파일의 음성 인식을 명시적으로 요청한 것이므로 `whisper_fallback`은 `false`여도 됩니다. `faster-whisper`가 원본 파일을 그 위치에서 바로 읽으며, 원본을 복사·수정·삭제하지 않습니다. HTTP 미디어 URL은 로컬 입력으로 받지 않습니다.

```bash
chew 요약 ./recordings/meeting.mp3
chew 학습 ./lectures/week-01.mp4

# URL이나 지원하는 로컬 경로는 `요약` 없이 바로 줄 수도 있음
chew ./recordings/interview.m4a
```

지원 확장자는 AAC, FLAC, M4A, MKV, MOV, MP3, MP4, MPEG/MPG, OGA/OGG, OPUS, WAV, WebM입니다. 파일 내용의 SHA-256으로 입력을 식별하므로 같은 파일을 옮기거나 이름을 바꿔도 호환되는 Knowledge Pack을 재사용합니다. 중단된 실행은 `chew 이어하기`를 위해 절대 경로를 저장하므로 분석이 끝날 때까지는 해당 경로에 파일을 유지해야 합니다. 첫 음성 인식 때 설정한 Whisper 모델을 내려받을 수 있고 로컬 CPU/GPU 시간을 사용하지만, hosted 음성 인식 quota는 쓰지 않습니다.

---

## 빠른 시작 명령어

```bash
# 기본 긴 내용 정리본
chew 요약 'https://youtu.be/VIDEO_ID'

# 로컬 녹음 파일 (`whisper` extra 필요)
chew 요약 ./recordings/meeting.mp3

# URL을 첫 인자로 주면 `요약`을 생략할 수도 있음
chew 'https://youtu.be/VIDEO_ID'

# 목적별 재조립
chew 블로그 'https://youtu.be/VIDEO_ID'
chew 학습 'https://youtu.be/VIDEO_ID'
chew 옵시디언 'https://youtu.be/VIDEO_ID'

# 출력 위치 지정
chew 블로그 'https://youtu.be/VIDEO_ID' -o ./posts/my-video
```

입력을 생략하면 YouTube URL 또는 로컬 미디어 경로를 대화형으로 묻습니다. 자동화에서는 `--json`을 붙이면 `{"ok": true, "data": ...}` 형식으로 실행 결과를 받을 수 있습니다.

| 한국어 명령 | 영어 별칭 | 역할 |
|---|---|---|
| `요약` | `summarize` | 전체 요약과 챕터·소주제별 핵심 정리 |
| `블로그` | `blog` | 지정한 블로그 문체로 재구성 |
| `학습` | `study` | 개념, 근거, 추가 학습 항목 중심으로 재구성 |
| `옵시디언` | `obsidian` | `[[위키링크]]`가 있는 인덱스와 소주제 노트 생성 |
| `상태 [RUN_ID]` | `status` | 실행 및 작업 진행률 확인 |
| `이어하기 [RUN_ID]` | `resume` | 최신 또는 지정한 미완료 실행 재개 |
| `진단` | `doctor` | 실행기 설치·인증·지원 기능 확인 및 미설치 실행기 설치 안내 |
| `서버` | `serve` | FastAPI `/health` 및 `/readiness` HTTP 서버 시작 (`pip install 'chew[server]'`) |
| `저장소` | `storage` | 내부 파일 수와 용량 확인 |
| `정리` | `cleanup` | 보존 정책에 따른 삭제 후보 미리보기·적용 |

---

## 내부 상세 처리 흐름

### 1. 입력 식별자와 재사용 키

`youtu.be`, `youtube.com/watch`, Shorts, 모바일 URL을 하나의 canonical URL과 `youtube:<video-id>`로 통일합니다. 로컬 미디어는 이름이나 경로가 아닌 파일 바이트의 SHA-256에서 `local:<sha256>` 식별자를 만듭니다. 언어, 분석 깊이, 실행기 정책, 공통 지침, 프롬프트·분할·스키마 버전도 fingerprint에 넣어 호환되는 결과만 재사용합니다.

### 2. 메타데이터와 자막

기본 fallback 순서는 다음과 같습니다.

1. yt-dlp 수동 자막
2. yt-dlp 자동 생성 자막
3. `youtube-transcript-api`
4. `whisper_fallback: true`일 때만 `faster-whisper`

사용자가 명시적으로 준 로컬 미디어 파일은 YouTube provider를 거치지 않고 `faster-whisper`로 바로 넘어갑니다. fallback 설정은 YouTube 오디오 자동 다운로드만 제어합니다.

자막은 언어, 시간 순서, 전체 길이 대비 coverage, 과도한 반복, 큰 무음 구간을 검사합니다. 한 provider가 실패하거나 품질 기준을 통과하지 못하면 이유를 기록하고 다음 provider로 넘어갑니다. yt-dlp에서 얻은 제목과 YouTube 챕터는 선택적 Whisper를 포함해 이후 자막 provider가 바뀌어도 보존됩니다.

### 3. 원문 준비와 실행 제어

원문 자막은 근거로 보존하고, 되돌릴 수 있는 준비된 입력으로 만듭니다. 실행 정책은 생성 전에 routing, budget, retry 경계를 고정합니다. checkpoint는 완료된 작업을 남기며, 외부 provider의 수신 결과가 불명확하면 자동으로 다시 보내지 않습니다.

### 4. Grounded Compilation과 Knowledge Pack

```text
Raw transcript
  → prepared transcript
  → Grounded Knowledge Tree draft
  → 로컬 evidence grounding
  → Knowledge Pack
  → 목적별 문서
```

compiler는 configured Frontier runtime으로 추론하고, evidence span과 timestamp를 raw transcript에 로컬로 대조합니다. 결과 Knowledge Pack은 검증되지 않은 모델 응답이 아니라 재사용 가능한 버전 지식입니다.

### 5. 결정론적 출력 렌더링

- `digest`: 저장된 pack의 개요와 타임스탬프 근거를 렌더링
- `blog`: 새 outline·compose 요청 없이 선택한 블로그 프로필로 pack을 렌더링
- `study`: 개념, 근거, 추가 학습 항목을 렌더링
- `obsidian`: 저장된 pack에서 인덱스와 연결된 노트를 생성

출력 자체도 Knowledge Pack fingerprint, 프로필, 지침, 언어, 깊이, 실행기, 출력 recipe 버전으로 캐시합니다. 동일한 출력 요청은 로그인된 AI CLI가 없어도 로컬 캐시만으로 복원할 수 있습니다.

---

## 주요 모듈 및 기술 스택

- **언어 및 런타임**: Python 3.12+
- **CLI 라이브러리**: Typer, Rich
- **저장소 엔진**: SQLite WAL, zstandard
- **자막 및 오디오**: yt-dlp, youtube-transcript-api, faster-whisper
- **관측성**: OpenTelemetry API/SDK, VizTracer

이 프로젝트는 **포트와 어댑터(Ports & Adapters / 육각형 아키텍처)** 모듈 구조를 따릅니다. 상세 지침은 [`AGENTS.md`](AGENTS.md)를 참고하세요.

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

| 모듈 | 책임 |
|---|---|
| `application.py` | CLI와 분석·출력·재개의 use case 연결 |
| `transcripts/` | 자막 provider fallback, 정규화, 품질 검증 |
| `segmentation.py` | 챕터 우선·시간 기반 소주제 분할 |
| `scheduler.py` | 의존성 DAG, 병렬 실행, lease, heartbeat, 재시도 |
| `harness/` | 외부 AI CLI 탐색, 인증 진단, 구조화 출력 변환 |
| `pipeline.py` | 소주제 → 챕터 → Knowledge Pack 계층형 합성 |
| `outputs.py` | digest·blog·study·Obsidian 재조립과 출력 캐시 |
| `storage/` | SQLite 상태 저장과 content-addressed artifact 저장 |
| `retention.py` | 미리보기 기반 보존·삭제 정책 |
| `benchmark.py` | Gemini 직접 분석과 계층형 파이프라인 비교 |

핵심 파이프라인은 특정 업체 SDK나 계정 파일을 알지 못합니다. 모든 AI 요청은 `GenerationRequest → Harness → GenerationResult` 계약을 통과하므로 새 실행기를 추가할 때 파이프라인을 수정하지 않고 어댑터만 구현할 수 있습니다.

---

## 중단 복구와 캐시

SQLite WAL에 run, job, 의존성, 시도 횟수, worker claim, lease 만료 시각을 기록합니다. 각 작업은 고유 claim token을 가져 오래된 worker가 새 결과를 덮어쓰지 못합니다. 실행 중에는 heartbeat로 lease를 연장하고, 프로세스 종료나 네트워크 단절로 lease가 만료되면 다시 큐에 넣습니다.

```bash
chew 상태
chew 상태 RUN_ID
chew 이어하기
chew 이어하기 RUN_ID
```

재개할 때는 현재 설정이 아니라 최초 run에 저장된 분석 recipe를 사용합니다. URL만 다시 입력해도 동일한 분석이 완료되어 있다면 run-id 없이 Knowledge Pack을 찾아 재조립합니다.

불변 transcript·요약·Knowledge Pack·출력 캐시는 canonical JSON의 SHA-256 digest를 주소로 사용하고 zstd로 압축합니다. 같은 내용은 한 번만 저장됩니다. 기본 데이터 위치는 운영체제의 사용자 application-data 디렉터리이며, 사용자가 지정한 출력 폴더는 자동 정리하지 않습니다.

---

## 저장 및 삭제 정책

- `compact`(기본): 참조 중인 자료를 보호하고 24시간 지난 임시 미디어, 30일 지난 로그, 7일 지난 미참조 객체를 정리합니다.
- `private`: 내보낸 파일이 실제로 존재하는지 확인한 뒤 관련 내부 자막과 중간 산출물을 정리할 수 있습니다.
- `archive`: 분석 리비전과 중간 자료를 계속 보존합니다.

```bash
chew 저장소
chew 정리 --policy compact        # 미리보기
chew 정리 --policy compact --apply
chew 삭제 RUN_ID                  # 확인 후 특정 실행 삭제
chew 완전삭제                      # 별도 확인 문구 필요
```

`정리`는 기본적으로 미리보기만 수행합니다. 명시적 `--apply` 또는 사용자 확인 없이는 내부 자료를 삭제하지 않습니다.

---

## 벤치마크 & OpenTelemetry 시각화 대시보드

성능 프로파일링 및 관측성을 위한 선택적 기능입니다. 일반 사용자에게는 불필요하며, 벤치마킹을 원하는 개발자만 선택하여 실행합니다:

```bash
# 선택적 벤치마킹 및 대시보드 패키지 설치
pip install -e '.[telemetry]'

# OpenTelemetry 기반 실시간 대시보드 UI 구동
chew benchmark-dashboard
# 또는
chew benchmark-ui
```

관리자 전용 자막 전처리 비교는 `benchmarks/`의 고정 fixture와 스크립트를 사용합니다.
기능 개발 전 또는 이전 릴리스에서 baseline을 저장하고, 후보 기능 구현 후 최종 리포트를 실행합니다:

```bash
benchmarks/benchmark.sh baseline --preprocessing none --concurrency 5
benchmarks/benchmark.sh report allInOne \
  --baseline <baseline-run-id> \
  --target-release v0.2.0
```

저장된 근거는 `reports/performance-comparisons/transcript-preprocessing/` 아래에 남습니다. metrics 수집 단계는 LLM을 호출하지 않으며, 벤치마크 전용 의존성을 일반 패키지 설치에 추가하지 않습니다. 생성된 리포트는 전체 토큰 절감률, 영상별 그래프, stage token funnel, 품질/신뢰성/재현성 gate, 릴리스 메타데이터, 그리고 후보 경로에서 측정 가능한 변화가 없을 때의 경고를 함께 보여줍니다.

---

## 개발과 검증

```bash
# 1초 자동 설치 및 chew 터미널 명령어 등록
./setup.sh

# 개별 검증
pip install -e '.[youtube,dev]'
ruff check .
mypy src/chew
pytest -q
coverage run -m pytest
coverage report
python -m build
```

기본 테스트와 벤치마크 목록은 외부 호출을 하지 않습니다. 라이브 검증은 다음 환경 변수를 명시했을 때만 실행됩니다.
- `YTSUM_LIVE_YOUTUBE_URL`: 실제 자막 provider 통합 테스트
- `YTSUM_LIVE_HARNESS`: `codex`, `gemini`, `claude`, `ollama` 중 하나의 실행기 테스트

자세한 개발 및 테스트 지침은 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

---

## 버전 이력

버전별 변경 사항 및 릴리스 노트는 [CHANGELOG.md](CHANGELOG.md)에서 자세히 확인할 수 있습니다.
