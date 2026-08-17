# YouTube Summarizer Kit (`chew`)

[![CI](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**English** | [한국어](README.ko.md)

A local-first CLI tool (`chew`) that turns YouTube videos and local audio/video files into reusable knowledge.
Instead of producing one-off summary text, it validates captions, analyzes chapters and subtopics in parallel, and compiles them into structured documents for different goals.

- Run with `chew <URL>`.
- Recognizes video chapters and processes subtopics in parallel for reliable analysis of long videos.
- Resumes automatically from completed tasks if interrupted by network errors or AI CLI disconnections.
- Reuses existing Knowledge Packs for identical URLs and analysis settings without needing run-ids.
- Transcribes explicitly specified local media in-place and reuses previous analyses by content hash even if files are moved or renamed.
- Connects Codex CLI, Gemini CLI, Claude Code / Claude CLI, Ollama, and Antigravity CLI (`agy`) through a unified Harness interface.
- Manages writing voices and study styles via Markdown files instead of long CLI flags.

## Why `chew`?

Watching 1–2 hour tech keynotes, podcasts, or lectures takes too much time, and generic AI summarizers output lazy 5-line bullet points that lose all technical context, code examples, and timestamped evidence.

`chew` was built to solve this problem:

- **Don't Watch, Let AI Chew It**: Long media is adaptively segmented into chapters and subtopics so AI can deeply analyze (Chew) and structure every insight.
- **Analyze Once, Reassemble Anywhere**: Analyze a video once into a **Knowledge Pack**, then reassemble it into a Tech Blog, Study Guide, or Obsidian Wiki Note in 1 second without re-calling LLMs or paying API fees.
- **Zero API Cost & Privacy-First**: Leverages your existing local AI CLI sessions (Codex, Gemini, Claude, Ollama, Antigravity CLI) without copying or reading your private credentials or API keys.

> Current analysis is caption-centric. Videos where visual charts, code, or scenes are essential may lose details, as frame-based multimodal analysis is not yet included in the core pipeline.

## Support Matrix

| Harness | Supported | Auth Verification | Login / Launch Method |
|---|---|---|---|
| Codex CLI (`codex`) | Yes | Pre-checked via `codex login status` | `codex login` if needed |
| Claude Code / Claude CLI (`claude`) | Yes | Pre-checked via `claude auth status` | Login inside `claude` if needed |
| Gemini CLI (`gemini`) | Yes | Verified on first generation request | Login inside `gemini` if needed |
| Ollama (`ollama`) | Yes | No login required | Launch local Ollama server |
| Antigravity CLI / AGY (`agy`) | Yes | Verified on first generation / Uses local session | Install `agy` CLI & login |

Default `runtime: auto` selects an available harness from installed and authenticated candidates in order: Codex → Gemini → Claude → Ollama → Antigravity. Gemini, which cannot pre-verify auth statelessly, becomes a candidate when no other harness is verified and checks actual auth during the first request.

If a harness with verifiable auth (like Codex or Claude) is logged out, the selection falls back to the next ready candidate. If a fixed runtime is configured but not logged in, `chew` guides you to the login command and preserves the run state as `blocked_auth`. Running `chew resume` after logging in resumes processing without repeating finished segments.

This project never reads or copies your account files or API keys. It launches installed CLIs as separate processes, reusing your existing local login sessions directly.

## Architecture

Follows strict **Ports & Adapters (Hexagonal)** architecture rules. See [`AGENTS.md`](AGENTS.md) for full developer and AI agent guidelines.

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

## Quick Start & Installation

Python 3.12 or newer is required. **Installation is required once before running `chew`.** Running the **1-Click Auto Setup** below installs dependencies, registers the global `chew` CLI command, and initializes default configuration files (`CHEW.md` & `.chew/profiles/`):

```bash
git clone https://github.com/SHcommit/youtube-summerizer-kit.git
cd youtube-summarizer-kit

# 1-Click Auto Setup (installs dependencies, registers 'chew' alias, initializes CHEW.md & .chew/profiles/)
./setup.sh
```

After installation, simply run **`chew 'URL'`** directly from any terminal window:

```bash
# Run default detailed summary digest
chew 'https://www.youtube.com/watch?v=VIDEO_ID'

# Run packed deep-dive summary
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth deep

# Run quick high-level summary (quick / short / brief)
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth quick

# Instant 1-second format reassembly
chew blog 'https://www.youtube.com/watch?v=VIDEO_ID'
chew study 'https://www.youtube.com/watch?v=VIDEO_ID'
chew obsidian 'https://www.youtube.com/watch?v=VIDEO_ID'

# Local audio / video file input
chew ./recordings/meeting.mp3
```

Manual Developer Installation:

```bash
pip install -e '.[youtube,dev]'
```

The optional `faster-whisper` fallback is disabled by default so installation does not download a speech model or video audio. To enable it, install `pip install -e '.[youtube,whisper]'` and set `whisper_fallback: true` in `CHEW.md`. The first enabled transcription may download a model through `faster-whisper`.

Local audio and video file input also requires the `whisper` extra, but does not require enabling the YouTube fallback:

```bash
pip install -e '.[youtube,whisper]'
```

Verify your installation:

```bash
chew doctor
chew doctor --json
```

## Captionless Videos

Standard execution downloads no media files, collecting existing text instead. It tries manual captions, auto-generated captions, and `youtube-transcript-api` in order. If all three are unavailable or fail quality checks, it will not silently download audio or models; instead, it explains how to enable local speech recognition.

Install optional dependencies and enable the fallback in `CHEW.md`:

```bash
pip install -e '.[youtube,whisper]'
```

```markdown
---
whisper_fallback: true
---
```

When enabled, the fourth fallback downloads video audio to a temporary directory and generates a timestamped transcript locally using `faster-whisper`. The temporary audio is deleted immediately after transcription. The first run may download a Whisper model and consumes local CPU/GPU time, but does not use AI CLI logins or hosted API quotas. Titles and YouTube chapters obtained via yt-dlp are preserved. Accuracy varies depending on audio quality, speaker clarity, and selected language.

## Local Audio & Video Files

Local media file paths can be passed in place of a YouTube URL. Providing a local file path acts as an explicit request for transcription, so `whisper_fallback` can remain `false`. `faster-whisper` reads the file in-place without copying, modifying, or deleting the original file. Remote HTTP media URLs are not accepted.

```bash
chew summarize ./recordings/meeting.mp3
chew study ./lectures/week-01.mp4

# Arguments can omit 'summarize' for URLs or supported local paths
chew ./recordings/interview.m4a
```

Supported extensions: AAC, FLAC, M4A, MKV, MOV, MP3, MP4, MPEG/MPG, OGA/OGG, OPUS, WAV, WebM. Inputs are identified by the SHA-256 hash of their contents, reusing compatible Knowledge Packs even if files are moved or renamed. Interrupted runs store absolute file paths for `chew resume`, so original files must remain at their locations until analysis finishes.

## Command Line Reference

| Command | Option / Usage | Purpose |
|---|---|---|
| `chew 'URL'` | `chew 'URL'` | Default summary digest (interactive prompt if URL omitted) |
| `chew 'URL' -d deep` | `chew 'URL' -d deep` | Packed deep-dive summary (`quick`, `detailed`, `deep`) |
| `chew blog 'URL'` | `chew blog 'URL'` | Reassemble into Tech Blog with configured tone |
| `chew study 'URL'` | `chew study 'URL'` | Reassemble into Study Notes & Follow-up Q&A |
| `chew obsidian 'URL'` | `chew obsidian 'URL'` | Reassemble into Obsidian Vault with `[[wikilinks]]` |
| `chew status [RUN_ID]` | `chew status [RUN_ID]` | Inspect active/past run execution progress |
| `chew resume [RUN_ID]` | `chew resume [RUN_ID]` | Instantly resume interrupted analysis from checkpoint |
| `chew doctor` | `chew doctor` | Diagnose installed AI CLIs and authentication status |
| `chew cleanup` | `chew cleanup` | Preview or apply storage retention policies |

Passing `--json` returns output in structured `{"ok": true, "data": ...}` JSON format for automation.

## Markdown Configuration & Styles

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

### Summary Depth Intensity (`depth`)

Customize the summary detail level via CLI flag (`--depth` / `-d`) or inside `CHEW.md`:

- **`quick`** (`short` / `brief`): High-level milestone summary for fast scanning
- **`detailed`** (default): Balanced detailed summary with chapter subtopics and timestamp evidence
- **`deep`**: Comprehensive deep-dive analysis capturing every chapter, technical detail, and argument

```bash
# Quick high-level summary (quick / short / brief)
chew 'VIDEO_URL' --depth quick

# Comprehensive deep-dive summary
chew 'VIDEO_URL' --depth deep
```

The Markdown body becomes an LLM instruction. Purpose-specific files such as `.chew/profiles/blog.md` can define voice, audience level, and document structure. Configuration discovery walks up through parent directories; packaged defaults are used when no file exists.

Analysis settings and output settings are fingerprinted separately. Changing only the blog voice does not repeat transcript and topic analysis—it generates a new document from the existing Knowledge Pack.

## User Input and Output

The first diagram hides internal implementation details, showing only inputs and output artifacts.

![User Input and Output Flow](assets/architecture/en/user-flow.png)

If a Knowledge Pack for the same URL and analysis settings already exists, video analysis is skipped. Changing only the output profile reassembles the existing Knowledge Pack into blogs, study guides, or Obsidian documents in 1 second.

## Internal Pipeline Architecture (How It Works)

The second diagram details the top-to-bottom flow: `INPUT → Analysis → Knowledge Pack → Reassembly → OUTPUT`. AI harnesses, storage, and auth recovery are shown as supporting sidecars.

![Internal Pipeline Architecture Flow](assets/architecture/en/internal-pipeline.png)

The yellow Knowledge Pack is the core unit of reuse. Once created, transcript and topic analysis are never repeated when switching output goals or writing voices. The dashed storage layer preserves intermediate state, and the red recovery flow highlights resume checkpoints after auth or connection failures.

### 1. Identity & Reuse Keys
Normalizes `youtu.be`, `youtube.com/watch`, Shorts, and mobile URLs into a single canonical URL and `youtube:<video-id>`. Local media produces `local:<sha256>` from file byte hashes rather than file names. Language, depth, runtime policy, shared instructions, and prompt/schema versions are hashed into fingerprints to ensure only compatible cached results are reused.

### 2. Metadata & Captions
Fallback sequence:
1. yt-dlp manual captions
2. yt-dlp auto captions
3. `youtube-transcript-api`
4. `faster-whisper` (only when `whisper_fallback: true`)

Explicit local media bypasses YouTube providers directly to `faster-whisper`. Captions are inspected for language, chronological order, coverage relative to duration, excessive repetitions, and large silent gaps.

### 3. Adaptive Segmentation & Parallel Processing
Preserves YouTube chapter boundaries when available. If chapters are absent or oversized, text is split at sentence boundaries into ~5–10 minute subtopics. Independent subtopics are processed concurrently in an async queue. Global concurrency limits and per-runtime rate limits are enforced dynamically.

### 4. Hierarchical Synthesis & Knowledge Pack
```text
Transcript
  → TopicSummary[]
  → ChapterSummary[]
  → KnowledgePack
  → Goal-Specific Document
```
The Knowledge Pack contains video identifiers, title, language, full overview, subtopics, chapters, core claims, timestamped evidence, concepts, examples, follow-up topics, and analysis fingerprints.

### 5. Output Reassembly
- `digest`: Generates full, chapter, and subtopic summaries with timestamp evidence directly from the Knowledge Pack.
- `blog`: Reassembles via three-stage outline → draft → verification pipeline.
- `study`: Reassembles around structured learning objectives and self-check Q&A.
- `obsidian`: Creates index and subtopic files linked with `[[wikilinks]]`.

## Performance Optimization

Optimized pipeline segmentation and harness concurrency for a **16.3x performance boost**:

| Metric | Baseline | Optimized | Improvement |
|---|---|---|---|
| 25-min Tech Video Analysis | 30m 00s (1,800s) | **1m 50s (110s)** | **16.3x Faster** |
| Pipeline Tasks Generated | 61 fine tasks | **11 condensed tasks** | 82% Reduction |
| AI Harness Concurrency | 2 workers | **8 parallel workers** | 4x Increase |

Detailed Analysis Report: [`reports/performance_analysis.md`](reports/performance_analysis.md)

## Core Modules

| Module | Responsibility |
|---|---|
| `application.py` | Connects CLI commands to analysis, output, and resume use cases |
| `transcripts/` | Caption provider fallbacks, normalization, and quality validation |
| `segmentation.py` | Chapter-first and time-based subtopic segmentation |
| `scheduler.py` | Dependency DAG, parallel execution, leases, heartbeats, and retries |
| `harness/` | External AI CLI discovery, auth diagnostics, and structured output parsing |
| `pipeline.py` | Topic → chapter → Knowledge Pack hierarchical synthesis |
| `outputs.py` | Reassembles digest, blog, study, and Obsidian outputs from Knowledge Pack |
| `storage/` | SQLite state machine and content-addressed zstd artifact storage |
| `retention.py` | Preview-driven retention and cleanup policies |
| `benchmark.py` | Evaluates hierarchical pipeline against direct LLM analysis |

## Resumption & Caching

Stores runs, jobs, dependencies, attempts, worker claims, and lease expiration timestamps in SQLite WAL. Each worker uses a unique claim token to prevent stale workers from overwriting new results. Runs extend leases via heartbeats and re-queue expired jobs automatically upon crashes or network disconnects.

```bash
chew status
chew status RUN_ID
chew resume
chew resume RUN_ID
```

Resumption uses the original run's stored analysis recipe rather than current settings. Re-entering an identical URL finds completed runs by fingerprint without needing a run-id.

## Storage Retention & Cleanup

- `compact` (default): Protects referenced artifacts; cleans 24h temporary media, 30d logs, and 7d unreferenced objects.
- `private`: Verifies exported files exist before cleaning internal transcripts and intermediate artifacts.
- `archive`: Retains all analysis revisions and intermediate data indefinitely.

```bash
chew storage
chew cleanup --policy compact        # Preview
chew cleanup --policy compact --apply
chew delete RUN_ID                   # Delete specific run after confirmation
chew purge                           # Purge all data (requires explicit phrase)
```

## Benchmarking & OpenTelemetry Dashboards

Optional features for performance benchmarking and trace telemetry:

```bash
# Install optional telemetry dependencies
pip install -e '.[telemetry]'

# Launch OpenTelemetry trace report & Jaeger UI guide
chew benchmark-dashboard
```

```bash
chew benchmark list
chew benchmark run 'https://youtu.be/VIDEO_ID' --live \
  --reference benchmark-reference.json --repeats 3 --runtime codex
```

## License & Community

- **License**: [MIT License](LICENSE)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
