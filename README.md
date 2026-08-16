# YouTube Summarizer Kit

**English** | [한국어](README.ko.md)

A local-first, resumable CLI (`chew`) that turns YouTube videos and local audio or video files into reusable
knowledge. It validates transcripts, analyzes chapters and topics in parallel, and compiles the
result into multiple formats instead of producing a one-off summary.

- Run with `chew <URL>` (or aliases `yts`, `ytsummarizer`, `ytsum`).
- Handles long videos with chapter-aware, topic-level parallel processing.
- Resumes from completed work after a network or AI CLI interruption.
- Reuses an existing Knowledge Pack for the same URL and analysis settings—no run ID required.
- Transcribes explicitly supplied local media in place and reuses it by content hash, even if the
  file is moved or renamed.
- Connects Codex CLI, Gemini CLI, Claude Code / Claude CLI, Ollama, and Antigravity CLI (`agy`) through one harness interface.
- Stores writing tone and study preferences in Markdown instead of long CLI option lists.

> The current pipeline is transcript-first. Videos whose essential information appears only in
> diagrams, code shown on screen, or visual scenes may lose context. Frame-based multimodal
> analysis is not yet part of the default pipeline.

## Runtime support

| Runtime | Available | Authentication check | Setup |
|---|---:|---|---|
| Codex CLI (`codex`) | Yes | Preflight check with `codex login status` | Run `codex login` if needed |
| Claude Code / Claude CLI (`claude`) | Yes | Preflight check with `claude auth status` | Sign in through `claude` if needed |
| Gemini CLI (`gemini`) | Yes | Verified on the first generation request | Sign in through `gemini` if needed |
| Ollama (`ollama`) | Yes | No login required | Start a local Ollama server |
| Antigravity CLI / AGY (`agy`) | Yes | Verified on invocation / persistent session | Install `agy` CLI |

With the default `runtime: auto`, the kit selects an installed, authenticated runtime from the
Codex → Gemini → Claude → Ollama → Antigravity candidate set. Because Gemini does not expose a reliable
non-consuming authentication-status command, it is probed by the first actual generation request
when no already-verified runtime is available.

If a runtime with a preflight authentication check is signed out, automatic selection moves to
another ready runtime. If you explicitly select a signed-out runtime, the run is saved as
`blocked_auth` and the CLI prints the login command. Sign in, then run `ytsum resume`; completed
segments are preserved.

The kit never reads or copies account files or API keys. It launches installed AI CLIs as child
processes and uses their existing Codex, Gemini, or Claude login sessions.

## Architecture

The project follows a **Ports & Adapters (Hexagonal)** modular layout. See [`AGENTS.md`](AGENTS.md) for full developer and AI agent guidelines.

```
src/ytsum/
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

## Installation

Python 3.12 or newer is required.

```bash
git clone <repository-url> youtube-summarizer-kit
cd youtube-summarizer-kit
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[youtube]'
```

Install development tools as well:

```bash
pip install -e '.[youtube,dev]'
```

The optional `faster-whisper` fallback is disabled by default so installation does not download a
speech model or video audio. To enable it, install `pip install -e '.[youtube,whisper]'` and set
`whisper_fallback: true` in `YTSUM.md`. The first enabled transcription may download a model through
`faster-whisper`.

Local audio and video file input also requires the `whisper` extra, but does not require enabling
the YouTube fallback:

```bash
pip install -e '.[youtube,whisper]'
```

Check the environment after installation:

```bash
ytsum doctor
ytsum doctor --json
```

## Videos without captions

The normal path reuses existing text and does not download video media: manually authored
subtitles, automatically generated subtitles, then `youtube-transcript-api`. If none of those
produce a usable transcript, the CLI explains how to opt in to local audio transcription instead
of silently downloading a model or video audio.

Install the optional dependencies and enable the fallback in `YTSUM.md`:

```bash
pip install -e '.[youtube,whisper]'
```

```markdown
---
whisper_fallback: true
---
```

With that setting enabled, the fourth fallback downloads the video's audio into a temporary
directory and uses `faster-whisper` to create a timestamped transcript locally. Temporary audio is
removed after transcription. A Whisper model may be downloaded on the first run, and transcription
uses local CPU/GPU time; it does not consume an AI CLI login or hosted API quota. Title and chapter
metadata already discovered through yt-dlp are preserved. Accuracy depends on audio quality,
speakers, and the configured transcript language.

## Local audio and video files

Pass an existing local media path anywhere a YouTube URL is accepted. Because supplying the path
is an explicit request to transcribe that file, `whisper_fallback` may remain `false`. The original
file is read directly by `faster-whisper`; it is not copied, modified, or deleted. HTTP media URLs
are not accepted as local inputs.

```bash
ytsum summarize ./recordings/meeting.mp3
ytsum study ./lectures/week-01.mp4

# A URL or supported local path may also be given without `summarize`
ytsum ./recordings/interview.m4a
```

Supported extensions are AAC, FLAC, M4A, MKV, MOV, MP3, MP4, MPEG/MPG, OGA/OGG, OPUS, WAV, and
WebM. The file content is identified by SHA-256, so the same bytes reuse a compatible Knowledge Pack
after a move or rename. An interrupted run stores the absolute source path for `ytsum resume`; keep
the file available at that path until analysis completes. The first transcription can download the
configured Whisper model and uses local CPU/GPU time, but does not consume hosted AI transcription
quota.

## Quick start

```bash
# Detailed digest
ytsum summarize 'https://youtu.be/VIDEO_ID'

# Local recording (requires the `whisper` extra)
ytsum summarize ./recordings/meeting.mp3

# Purpose-specific reassembly
ytsum blog 'https://youtu.be/VIDEO_ID'
ytsum study 'https://youtu.be/VIDEO_ID'
ytsum obsidian 'https://youtu.be/VIDEO_ID'

# Custom output directory
ytsum blog 'https://youtu.be/VIDEO_ID' -o ./posts/my-video
```

If the source is omitted, the CLI prompts for a YouTube URL or local media path. Add `--json` in
automation to receive a stable `{"ok": true, "data": ...}` response.

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

## Markdown configuration and writing style

Initialize editable configuration once per project:

```bash
ytsum config --init
```

The command creates these files without overwriting existing ones:

```text
YTSUM.md
.ytsum/
└── profiles/
    ├── blog.md
    ├── study.md
    └── obsidian.md
```

Example `YTSUM.md`:

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

The Markdown body becomes an LLM instruction. Purpose-specific files such as
`.ytsum/profiles/blog.md` can define voice, audience level, and document structure. Configuration
discovery walks up through parent directories; packaged defaults are used when no file exists.

Analysis settings and output settings are fingerprinted separately. Changing only the blog voice
does not repeat transcript and topic analysis—it generates a new document from the existing
Knowledge Pack. A profile may also choose a different `runtime` for uncached output reassembly.

## User input and output

This overview shows the public contract: what users provide and what the kit returns.

![YouTube Summarizer Kit user input and output](assets/architecture/en/user-flow.png)

When a compatible Knowledge Pack already exists for the URL and analysis settings, the kit skips
video analysis. A different purpose or voice reassembles that pack into a blog post, study guide,
or Obsidian vault.

## Internal processing flow

The detailed diagram follows `INPUT → analysis → Knowledge Pack → reassembly → OUTPUT`. Runtime
adapters, persistent local state, and recovery support the main path without defining it.

![YouTube Summarizer Kit internal processing flow](assets/architecture/en/internal-pipeline.png)

The yellow Knowledge Pack is the reuse boundary. Once created, the system can produce a new output
without repeating transcript and topic analysis. Dashed support nodes preserve intermediate state
and show where processing resumes after authentication or connectivity problems.

### 1. Source identity and reuse keys

The kit normalizes `youtu.be`, `youtube.com/watch`, Shorts, and mobile URLs into one canonical URL
and a `youtube:<video-id>` source ID. Local media uses a `local:<sha256>` source ID derived from the
file bytes rather than its name or path. The compatibility fingerprint includes language, analysis
depth, runtime policy, shared instructions, and prompt, segmentation, and schema versions. Only
compatible results are reused.

### 2. Metadata and transcripts

The default fallback order is:

1. Manually authored subtitles through yt-dlp
2. Automatically generated subtitles through yt-dlp
3. `youtube-transcript-api`
4. `faster-whisper`, only when `whisper_fallback: true`

An explicitly supplied local media file bypasses the YouTube providers and goes directly to
`faster-whisper`; the fallback flag only controls automatic YouTube audio download.

Every transcript is checked for language, timestamp order, duration coverage, excessive repetition,
and large gaps. If a provider fails or misses the quality threshold, the reason is recorded before
the next provider runs. Metadata and YouTube chapters discovered by yt-dlp remain available even
when a later provider, including the optional Whisper fallback, supplies the transcript.

### 3. Adaptive segmentation and parallel processing

YouTube chapter boundaries are preserved when available. Long chapters—or videos without
chapters—are divided into approximately five- to ten-minute topics while respecting sentence
boundaries. Independent topics run concurrently. A chapter is merged as soon as its required topics
finish instead of waiting for unrelated chapters.

Global and runtime-specific concurrency limits work together. A rate limit reduces concurrency for
that runtime and schedules a retry; sustained success gradually restores capacity.

### 4. Hierarchical summarization and the Knowledge Pack

```text
Transcript
  → TopicSummary[]
  → ChapterSummary[]
  → KnowledgePack
  → Purpose-specific documents
```

A Knowledge Pack contains video identity, title, language, overview, topics, chapters, claims,
timestamped evidence, concepts, examples, follow-up study material, and the analysis fingerprint.
The domain model can distinguish statements grounded in the video from AI additions and external
research provenance.

### 5. Output reassembly

- `digest`: Render the full, chapter, and topic summaries with evidence timestamps without another
  LLM call.
- `blog`: Reassemble the pack through outline, draft, and validation stages using the configured
  voice.
- `study`: Emphasize concepts and follow-up learning material.
- `obsidian`: Create an index and one file per topic connected with `[[wikilinks]]`.

Outputs are cached by Knowledge Pack fingerprint, profile, instructions, language, depth, runtime,
and output recipe version. An identical output request can be restored from local cache even when
no AI CLI is currently authenticated.

## Core modules

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

The core pipeline does not know vendor SDKs or account-file formats. Every AI request crosses the
`GenerationRequest → Harness → GenerationResult` contract, so a new runtime requires an adapter,
not a pipeline rewrite.

## Recovery and cache

SQLite WAL records runs, jobs, dependencies, attempt counts, worker claims, and lease expiration.
Each job has a unique claim token, preventing a stale worker from overwriting a newer result.
Heartbeats extend active leases; expired work returns to the queue after a process or network failure.

```bash
ytsum status
ytsum status RUN_ID
ytsum resume
ytsum resume RUN_ID
```

Resume uses the analysis recipe saved with the original run rather than the current configuration.
Entering the same URL also locates a completed compatible Knowledge Pack without requiring a run ID.

Immutable transcripts, summaries, Knowledge Packs, and output caches use a canonical JSON SHA-256
digest as their address and are compressed with zstd. Identical content is stored once. Internal
data lives in the operating system's user application-data directory; user-selected export folders
are never cleaned automatically.

## Retention and deletion

- `compact` (default): Protect referenced artifacts and clean temporary media older than 24 hours,
  logs older than 30 days, and unreferenced objects older than 7 days.
- `private`: After confirming exported files exist, allow internal transcripts and intermediate
  artifacts associated with them to be removed.
- `archive`: Preserve analysis revisions and intermediate artifacts.

```bash
ytsum storage
ytsum cleanup --policy compact          # Preview only
ytsum cleanup --policy compact --apply
ytsum delete RUN_ID                     # Confirmation required
ytsum purge                             # Requires the confirmation phrase: 완전삭제
```

`cleanup` is preview-only by default. Internal data is not deleted without an explicit `--apply` or
interactive confirmation.

## Benchmarking

```bash
ytsum benchmark list
ytsum benchmark run 'https://youtu.be/VIDEO_ID' --live \
  --reference benchmark-reference.json --repeats 3 --runtime codex
```

The benchmark compares direct Gemini URL analysis using a minimal prompt and shared schema against
the hierarchical pipeline using Gemini and the configured runtime. It evaluates claim and evidence
recall, timestamp accuracy, long-duration coverage, and unsupported claims against a reference file.
Each result states whether its input was `video_url` or `transcript`, so Gemini's multimodal input
advantage is not mistaken for pipeline quality.

Live benchmarks require both `--live` and an explicit reference file because they use real login
sessions and quota. Reports are written atomically to `benchmark-results/run-*/report.json` and
`report.md`. The project does not yet publish a multilingual, multi-duration benchmark corpus or
claim that it always outperforms Gemini.

## Development and verification

```bash
pip install -e '.[youtube,dev]'
ruff check .
mypy src
pytest -q
coverage run -m pytest
coverage report
python -m build
```

Default tests and the benchmark catalog make no external calls. Live checks run only when these
environment variables are explicitly set:

- `YTSUM_LIVE_YOUTUBE_URL`: Exercise a real transcript-provider integration.
- `YTSUM_LIVE_HARNESS`: Exercise one of `codex`, `gemini`, `claude`, or `ollama`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development and testing instructions.

## Version history

Detailed release notes and version changes are maintained in [CHANGELOG.md](CHANGELOG.md).

