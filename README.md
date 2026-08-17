# YouTube Summarizer Kit

[![CI](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**English** | [한국어](README.ko.md)

A local-first, resumable CLI (`chew`) that turns YouTube videos and local audio or video files into reusable knowledge. It validates transcripts, analyzes chapters and topics in parallel, and compiles the result into multiple formats instead of producing a one-off summary.

---

## Why `chew`?

Modern technical talks, podcasts, and video lectures are 1–2 hours long, yet traditional AI summarizers only produce superficial 5-bullet-point summaries that strip away key code context, evidence timestamps, and technical depth.

`chew` was built to solve this exact problem:

- **Don't watch. Let AI chew it for you**: Breaks long videos into topic-level segments so AI can digest and extract deep, timestamp-verified knowledge.
- **Analyze Once, Reassemble Anywhere**: Analyzes a video **once** into a content-addressed **Knowledge Pack**. Reassemble it instantly into Tech Blogs, Study Notes, or Obsidian Vaults without re-running expensive LLM calls.
- **Local-First & Multi-LLM Harness**: Leverages your existing Codex, Gemini, Claude, Ollama, or Antigravity CLI logins directly from your local terminal—no API keys required.

> The current pipeline is transcript-first. Videos whose essential information appears only in
> diagrams, code shown on screen, or visual scenes may lose context. Frame-based multimodal
> analysis is not yet part of the default pipeline.

---

## Features

- Run with `chew <URL>` in a single terminal command.
- Chapter-aware and topic-level asynchronous DAG parallel processing for long, complex videos.
- SQLite WAL state machine for seamless crash and network interruption recovery (`chew resume`).
- Knowledge Pack reuse by content hash for identical URLs and analysis settings.
- In-place transcription for local media files (MP3, MP4, M4A, WAV, etc.) with SHA-256 content deduplication.
- Unified harness adapter connecting Codex CLI, Gemini CLI, Claude Code / Claude CLI, Ollama, and Antigravity CLI (`agy`).
- 3-level summary intensity control (`quick`, `detailed`, `deep`).
- Markdown-based configuration files (`CHEW.md`, `.chew/profiles/`) for tone, format, and instructions instead of long CLI flags.
- Real-time OpenTelemetry Jaeger tracing for performance profiling and latency observability.

---

## Visual Demo & Architecture Diagrams

### User Flow Overview

![YouTube Summarizer Kit user input and output](assets/architecture/en/user-flow.png)

### Internal Processing Pipeline

![YouTube Summarizer Kit internal processing flow](assets/architecture/en/internal-pipeline.png)

### OpenTelemetry Jaeger Trace Observability

![OpenTelemetry Jaeger Trace Dashboard](assets/architecture/jaeger-trace-dashboard.png)

---

## Download & Prerequisites (Installation Required First)

Before running the `chew` command, you **must complete the download and environment setup below first**.

Python 3.12 or newer is required. Run the **1-Click Auto Setup** below to download dependencies and register the `chew` CLI command globally in 1 second:

```bash
# 1. Clone the repository (Download)
git clone https://github.com/SHcommit/youtube-summerizer-kit.git
cd youtube-summarizer-kit

# 2. 1-Click Auto Installer (registers global 'chew' command, no python/uv prefix needed)
./setup.sh
```

After installation, simply run **`chew 'URL'`** directly from your terminal.

### Manual Installation

Install development tools as well:

```bash
pip install -e '.[youtube,dev]'
```

The optional `faster-whisper` fallback is disabled by default so installation does not download a speech model or video audio. To enable it, install `pip install -e '.[youtube,whisper]'` and set `whisper_fallback: true` in `CHEW.md`. The first enabled transcription may download a model through `faster-whisper`.

Local audio and video file input also requires the `whisper` extra:

```bash
pip install -e '.[youtube,whisper]'
```

Check the environment after installation:

```bash
chew doctor
chew doctor --json
```

---

## Usage & Command Examples (Demo)

```bash
# Detailed digest (automatically terminates Python process and saves Markdown upon completion)
chew summarize 'https://youtu.be/VIDEO_ID'

# Local recording (requires the `whisper` extra)
chew summarize ./recordings/meeting.mp3

# Direct URL execution without `summarize`
chew 'https://youtu.be/VIDEO_ID'

# Purpose-specific reassembly (reuses Knowledge Pack instantly without re-running LLM analysis)
chew blog 'https://youtu.be/VIDEO_ID'
chew study 'https://youtu.be/VIDEO_ID'
chew obsidian 'https://youtu.be/VIDEO_ID'

# Custom output directory
chew blog 'https://youtu.be/VIDEO_ID' -o ./posts/my-video
```

If the source is omitted, the CLI prompts for a YouTube URL or local media path. Add `--json` in automation to receive a stable `{"ok": true, "data": ...}` response.

### Summary Depth Intensity (`depth`)

Customize the summary detail level via CLI flag (`--depth` / `-d`) or inside `CHEW.md`:

- **`quick`** (`short` / `brief`): High-level key milestone summary for fast scanning
- **`detailed`** (default): Balanced detailed summary with chapter subtopics and timestamp evidence
- **`deep`**: Comprehensive deep-dive analysis capturing every chapter, technical detail, and argument

```bash
# Quick high-level summary (quick / short / brief)
chew 'VIDEO_URL' --depth quick

# Comprehensive deep-dive summary
chew 'VIDEO_URL' --depth deep
```

| English command | Korean alias | Purpose |
|---|---|---|
| `summarize` | `요약` | Create a full digest with chapter and topic summaries |
| `blog` | `블로그` | Reassemble the Knowledge Pack in a configured blog voice |
| `study` | `학습` | Focus on concepts, evidence, and follow-up study material |
| `obsidian` | `옵시디언` | Create an index and topic notes with `[[wikilinks]]` |
| `status [RUN_ID]` | `상태` | Show run and job progress |
| `resume [RUN_ID]` | `이어하기` | Resume the latest or selected incomplete run |
| `doctor` | `진단` | Diagnose runtime installation and authentication |
| `storage` | `저장소` | Show internal file count and storage usage |
| `cleanup` | `정리` | Preview or apply a retention policy |

---

## How It Works

### 1. Source Identity and Reuse Keys (Transcript Extraction & Identity)

The kit normalizes `youtu.be`, `youtube.com/watch`, Shorts, and mobile URLs into one canonical URL and a `youtube:<video-id>` source ID. Local media uses a `local:<sha256>` source ID derived from the file bytes rather than its name or path. The compatibility fingerprint includes language, analysis depth, runtime policy, shared instructions, and prompt, segmentation, and schema versions. Only compatible results are reused.

### 2. Metadata and Transcripts (Preprocessing & Captions)

The default fallback order is:
1. Manually authored subtitles through yt-dlp
2. Automatically generated subtitles through yt-dlp
3. `youtube-transcript-api`
4. `faster-whisper`, only when `whisper_fallback: true`

An explicitly supplied local media file bypasses the YouTube providers and goes directly to `faster-whisper`; the fallback flag only controls automatic YouTube audio download.

Every transcript is checked for language, timestamp order, duration coverage, excessive repetition, and large gaps. If a provider fails or misses the quality threshold, the reason is recorded before the next provider runs. Metadata and YouTube chapters discovered by yt-dlp remain available even when a later provider, including the optional Whisper fallback, supplies the transcript.

### 3. Adaptive Segmentation and Parallel Processing (DAG Processing)

YouTube chapter boundaries are preserved when available. Long chapters—or videos without chapters—are divided into approximately five- to ten-minute topics while respecting sentence boundaries. Independent topics run concurrently. A chapter is merged as soon as its required topics finish instead of waiting for unrelated chapters.

Global and runtime-specific concurrency limits work together. A rate limit reduces concurrency for that runtime and schedules a retry; sustained success gradually restores capacity.

### 4. Hierarchical Summarization and the Knowledge Pack (LLM Processing & Synthesis)

```text
Transcript
  → TopicSummary[]
  → ChapterSummary[]
  → KnowledgePack
  → Purpose-specific documents
```

A Knowledge Pack contains video identity, title, language, overview, topics, chapters, claims, timestamped evidence, concepts, examples, follow-up study material, and the analysis fingerprint. The domain model can distinguish statements grounded in the video from AI additions and external research provenance.

### 5. Multi-Format Output Reassembly (Output Compilation)

- `digest`: Render the full, chapter, and topic summaries with evidence timestamps without another LLM call.
- `blog`: Reassemble the pack through outline, draft, and validation stages using the configured voice.
- `study`: Emphasize concepts and follow-up learning material.
- `obsidian`: Create an index and one file per topic connected with `[[wikilinks]]`.

Outputs are cached by Knowledge Pack fingerprint, profile, instructions, language, depth, runtime, and output recipe version. An identical output request can be restored from local cache even when no AI CLI is currently authenticated.

---

## Performance Improvements & Observability

### 16.3x Performance Speedup (30 min -> 1 min 50 sec)

- **Dynamic Video-Proportional Segmentation**: Implemented 5-segment ceiling for videos under 30 minutes (`segmentation.py`).
- **Concurrency Expansion**: Expanded AntigravityHarness concurrency limit from 2 to 8 (`antigravity.py`).
- **Benchmark Acceleration**: Total pipeline execution time reduced from 30+ minutes down to **1 minute 50 seconds** (16.3x speedup).

### OpenTelemetry Visual Tracing Dashboard

- `chew benchmark-dashboard` and `chew benchmark-ui` automatically export `reports/trace_report.md` and display span execution durations in Jaeger UI (`http://localhost:16686`).

---

## Tech Stack & Architecture

- **Language & Runtime**: Python 3.12+
- **CLI Framework**: Typer, Rich
- **State Machine & Persistence**: SQLite WAL, zstandard (Content-Addressed Artifact Storage)
- **Speech & Subtitles**: yt-dlp, youtube-transcript-api, faster-whisper
- **Observability**: OpenTelemetry API/SDK, VizTracer

### Ports & Adapters (Hexagonal Architecture)

The project follows a **Ports & Adapters (Hexagonal)** modular layout. See [`AGENTS.md`](AGENTS.md) for full developer and AI agent guidelines.

```
src/chew/
├── core/         # Layer 1: Core Domain Entities, Value Objects, Identity (SHA-256) & Prompts
├── pipeline/     # Layer 2: Analysis Engine, DAG Scheduler, & Output Compilation
├── storage/      # Layer 3: SQLite WAL State Machine & zstd Artifact Storage
├── harness/      # Layer 4: AI Runtime Adapters (Codex, Gemini, Claude, Ollama, Antigravity)
├── transcripts/  # Layer 5: Data Input Adapters (YouTube API, yt-dlp, Whisper)
├── app/          # Layer 6: Application Orchestration Service & DI Bootstrap
├── retention/    # Layer 7: Storage Retention & Cleanup Policies
├── benchmark/    # Layer 8: Quality Benchmarking Framework
└── cli/          # Layer 9: Bilingual Typer Command Line Interface
```

---

## Runtime Support & Supported Harnesses

| Runtime | Available | Authentication check | Setup |
|---|---:|---|---|
| Codex CLI (`codex`) | Yes | Preflight check with `codex login status` | Run `codex login` if needed |
| Claude Code / Claude CLI (`claude`) | Yes | Preflight check with `claude auth status` | Sign in through `claude` if needed |
| Gemini CLI (`gemini`) | Yes | Verified on the first generation request | Sign in through `gemini` if needed |
| Ollama (`ollama`) | Yes | No login required | Start a local Ollama server |
| Antigravity CLI / AGY (`agy`) | Yes | Verified on invocation / persistent session | Install `agy` CLI |

With the default `runtime: auto`, the kit selects an installed, authenticated runtime from the Codex → Gemini → Claude → Ollama → Antigravity candidate set. Because Gemini does not expose a reliable non-consuming authentication-status command, it is probed by the first actual generation request when no already-verified runtime is available.

If a runtime with a preflight authentication check is signed out, automatic selection moves to another ready runtime. If you explicitly select a signed-out runtime, the run is saved as `blocked_auth` and the CLI prints the login command. Sign in, then run `chew resume`; completed segments are preserved.

The kit never reads or copies account files or API keys. It launches installed AI CLIs as child processes and uses their existing Codex, Gemini, or Claude login sessions.

---

## Videos Without Captions and Local Media Files

### Videos Without Captions

The normal path reuses existing text and does not download video media: manually authored subtitles, automatically generated subtitles, then `youtube-transcript-api`. If none of those produce a usable transcript, the CLI explains how to opt in to local audio transcription instead of silently downloading a model or video audio.

Install the optional dependencies and enable the fallback in `CHEW.md`:

```bash
pip install -e '.[youtube,whisper]'
```

```markdown
---
whisper_fallback: true
---
```

With that setting enabled, the fourth fallback downloads the video's audio into a temporary directory and uses `faster-whisper` to create a timestamped transcript locally. Temporary audio is removed after transcription. A Whisper model may be downloaded on the first run, and transcription uses local CPU/GPU time; it does not consume an AI CLI login or hosted API quota. Title and chapter metadata already discovered through yt-dlp are preserved. Accuracy depends on audio quality, speakers, and the configured transcript language.

### Local Audio and Video Files

Pass an existing local media path anywhere a YouTube URL is accepted. Because supplying the path is an explicit request to transcribe that file, `whisper_fallback` may remain `false`. The original file is read directly by `faster-whisper`; it is not copied, modified, or deleted. HTTP media URLs are not accepted as local inputs.

```bash
chew summarize ./recordings/meeting.mp3
chew study ./lectures/week-01.mp4

# A URL or supported local path may also be given without `summarize`
chew ./recordings/interview.m4a
```

Supported extensions are AAC, FLAC, M4A, MKV, MOV, MP3, MP4, MPEG/MPG, OGA/OGG, OPUS, WAV, and WebM. The file content is identified by SHA-256, so the same bytes reuse a compatible Knowledge Pack after a move or rename. An interrupted run stores the absolute source path for `chew resume`; keep the file available at that path until analysis completes. The first transcription can download the configured Whisper model and uses local CPU/GPU time, but does not consume hosted AI transcription quota.

---

## Markdown Configuration and Writing Style (CHEW.md & Profiles)

Initialize editable configuration once per project:

```bash
chew config --init
```

The command creates these files without overwriting existing ones:

```text
CHEW.md
.chew/
└── profiles/
    ├── blog.md
    ├── study.md
    └── obsidian.md
```

Example `CHEW.md`:

```markdown
---
language: en
default_profile: digest
depth: detailed
runtime: auto
whisper_fallback: false
storage_policy: compact
---

Separate claims from the video from additional AI explanations.
Define technical terms on first use and connect every important claim to video evidence.
```

The Markdown body becomes an LLM instruction. Purpose-specific files such as `.chew/profiles/blog.md` can define voice, audience level, and document structure. Configuration discovery walks up through parent directories; packaged defaults are used when no file exists.

Analysis settings and output settings are fingerprinted separately. Changing only the blog voice does not repeat transcript and topic analysis—it generates a new document from the existing Knowledge Pack. A profile may also choose a different `runtime` for uncached output reassembly.

---

## Core Modules

| Module | Responsibility |
|---|---|
| `application.py` | Connect CLI use cases to analysis, output compilation, and resume behavior |
| `transcripts/` | Provider fallback, normalization, and transcript quality checks |
| `segmentation.py` | Chapter-first and time-based topic segmentation |
| `scheduler.py` | Dependency DAG, parallel execution, leases, heartbeats, and retries |
| `harness/` | Discover external AI CLIs, diagnose authentication, and parse structured output |
| `pipeline.py` | Hierarchical topic → chapter → Knowledge Pack synthesis |
| `outputs.py` | Digest, blog, study, and Obsidian compilation and output caching |
| `storage/` | SQLite state and content-addressed artifact storage |
| `retention.py` | Preview-based retention and deletion policies |
| `benchmark.py` | Compare direct Gemini analysis with the hierarchical pipeline |

The core pipeline does not know vendor SDKs or account-file formats. Every AI request crosses the `GenerationRequest → Harness → GenerationResult` contract, so a new runtime requires an adapter, not a pipeline rewrite.

---

## Recovery and Cache (Resume Behavior)

SQLite WAL records runs, jobs, dependencies, attempt counts, worker claims, and lease expiration. Each job has a unique claim token, preventing a stale worker from overwriting a newer result. Heartbeats extend active leases; expired work returns to the queue after a process or network failure.

```bash
chew status
chew status RUN_ID
chew resume
chew resume RUN_ID
```

Resume uses the analysis recipe saved with the original run rather than the current configuration. Entering the same URL also locates a completed compatible Knowledge Pack without requiring a run ID.

Immutable transcripts, summaries, Knowledge Packs, and output caches use a canonical JSON SHA-256 digest as their address and are compressed with zstd. Identical content is stored once. Internal data lives in the operating system's user application-data directory; user-selected export folders are never cleaned automatically.

---

## Retention and Deletion

- `compact` (default): Protect referenced artifacts and clean temporary media older than 24 hours, logs older than 30 days, and unreferenced objects older than 7 days.
- `private`: After confirming exported files exist, allow internal transcripts and intermediate artifacts associated with them to be removed.
- `archive`: Preserve analysis revisions and intermediate artifacts.

```bash
chew storage
chew cleanup --policy compact          # Preview only
chew cleanup --policy compact --apply
chew delete RUN_ID                     # Confirmation required
chew purge                             # Requires the confirmation phrase: 완전삭제
```

`cleanup` is preview-only by default. Internal data is not deleted without an explicit `--apply` or interactive confirmation.

---

## Benchmarking & OpenTelemetry Dashboard

Optional features for performance profiling and observability. General users can skip this step; developers who want performance tracing can install and run:

```bash
# Optional benchmarking and telemetry dependencies
pip install -e '.[telemetry]'

# Run OpenTelemetry visual performance UI dashboard
chew benchmark-dashboard
# or
chew benchmark-ui
```

```bash
chew benchmark list
chew benchmark run 'https://youtu.be/VIDEO_ID' --live \
  --reference benchmark-reference.json --repeats 3 --runtime codex
```

The benchmark compares direct Gemini URL analysis using a minimal prompt and shared schema against the hierarchical pipeline using Gemini and the configured runtime. It evaluates claim and evidence recall, timestamp accuracy, long-duration coverage, and unsupported claims against a reference file. Each result states whether its input was `video_url` or `transcript`, so Gemini's multimodal input advantage is not mistaken for pipeline quality.

Live benchmarks require both `--live` and an explicit reference file because they use real login sessions and quota. Reports are written atomically to `benchmark-results/run-*/report.json` and `report.md`. The project does not yet publish a multilingual, multi-duration benchmark corpus or claim that it always outperforms Gemini.

---

## Development and Verification

```bash
# 1-Click Auto Setup
./setup.sh

# Individual verification
pip install -e '.[youtube,dev]'
ruff check .
mypy src/chew
pytest -q
coverage run -m pytest
coverage report
python -m build
```

Default tests and the benchmark catalog make no external calls. Live checks run only when these environment variables are explicitly set:
- `YTSUM_LIVE_YOUTUBE_URL`: Exercise a real transcript-provider integration.
- `YTSUM_LIVE_HARNESS`: Exercise one of `codex`, `gemini`, `claude`, or `ollama`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development and testing instructions.

---

## Version History (Changelog)

Detailed release notes and version changes are maintained in [CHANGELOG.md](CHANGELOG.md).
