# YouTube Summarizer Kit (`chew`)

[![CI](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/SHcommit/youtube-summerizer-kit/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**English** | [한국어](README.ko.md)

> **Don't watch, let AI chew it!**  
> A local-first CLI tool (`chew`) that digests YouTube videos and local audio/video media into reusable **Knowledge Packs**, reassembling them in 1 second into Tech Blogs, Study Notes, or Obsidian Vault wikis.

---

## 💡 Why I Built This (Motivation)

Watching 1–2 hour tech keynotes, podcasts, or lectures takes too much time, and generic AI summarizers output lazy 5-line bullet points that lose all technical context, code examples, and timestamped evidence.

`chew` was built to solve this problem:

- **Don't Watch, Let AI Chew It**: Long media is adaptively segmented into chapters and subtopics so AI can deeply analyze (Chew) and structure every insight.
- **Analyze Once, Reassemble Anywhere**: Analyze a video once into a **Knowledge Pack**, then reassemble it into a Tech Blog, Study Guide, or Obsidian Wiki Note in 1 second without re-calling LLMs or paying API fees.
- **Zero API Cost & Privacy-First**: Leverages your existing local AI CLI sessions (Codex, Gemini, Claude, Ollama, Antigravity CLI) without copying or reading your private credentials or API keys.

---

## ✨ Key Features

- ⚡ **Adaptive Chapter & Subtopic Parallel Analysis**: Dynamically segments long videos based on duration and processes independent subtopics in parallel async queues.
- 🎚️ **3-Level Summary Depth Control (`--depth`)**: Easily choose between `quick` (short/brief), balanced `detailed` (default), or packed `deep` analysis.
- 🔄 **Resumable Runs & 1-Second Reassembly**: SQLite WAL state machine tracks progress for instant resumption after interruptions and 1-second format switching.
- 🎙️ **Automatic Caption Acquisition & Local Whisper Fallback**: Collects YouTube captions first and falls back to local `faster-whisper` transcription for captionless videos or local media files.
- 🚀 **16.3x Performance Boost & OpenTelemetry Observability**: Reduced 25-min video analysis from 30 minutes to **1m 50s**, with OpenTelemetry Jaeger UI trace dashboards.

---

## ⚙️ Installation & Getting Started

**Installation is required once before running `chew`.** Running the **1-Click Auto Setup** in Python 3.12+ installs dependencies, registers the global `chew` CLI command, and initializes default configuration files (`CHEW.md` & `.chew/profiles/`).

### Step 1: 1-Click Auto Setup

```bash
git clone https://github.com/SHcommit/youtube-summerizer-kit.git
cd youtube-summarizer-kit

# 1-Click Auto Setup (installs packages, registers 'chew' alias, and initializes config)
./setup.sh
```

### Step 2: Running `chew`

Once installed, run **`chew 'URL'`** directly from any terminal window:

```bash
# Default detailed summary (automatically saves Markdown and exits Python cleanly)
chew 'https://www.youtube.com/watch?v=VIDEO_ID'

# Packed deep-dive summary (--depth deep)
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth deep

# Quick high-level summary (--depth quick / short / brief)
chew 'https://www.youtube.com/watch?v=VIDEO_ID' --depth quick

# Instant 1-second format reassembly
chew blog 'https://www.youtube.com/watch?v=VIDEO_ID'
chew study 'https://www.youtube.com/watch?v=VIDEO_ID'
chew obsidian 'https://www.youtube.com/watch?v=VIDEO_ID'

# Local audio / video file input (recording.mp3)
chew ./recordings/meeting.mp3
```

Manual Developer Setup:
```bash
pip install -e '.[youtube,dev]'
```

---

## 🛠️ How It Works (Pipeline Architecture)

The `chew` processing engine operates across 4 core layers:

![User Input and Output Flow](assets/architecture/en/user-flow.png)

```text
[Input URL / Local Media]
       │
       ▼
 1. Transcript Extraction & Validation (Captions with local Whisper fallback)
       │
       ▼
 2. Preprocessing & Dynamic Segmentation (Adaptive chapter & 5-10 min subtopic splitting)
       │
       ▼
 3. Parallel Async LLM Synthesis (Bounded Concurrency DAG Scheduler & AI Harness)
       │
       ▼
 4. Knowledge Pack Compilation (Content-addressed zstd artifact storage)
       │
       ▼
 [Multi-Format Output: Digest / Blog / Study / Obsidian Markdown]
```

![Internal Pipeline Architecture Flow](assets/architecture/en/internal-pipeline.png)

### 1. Transcript Extraction & Validation
- Tries manual captions → auto captions → `youtube-transcript-api` in order and checks quality metrics (coverage, repetitions, silences).
- If captions are missing or fail validation, falls back to local `faster-whisper` when `whisper_fallback: true` is enabled.

### 2. Adaptive Dynamic Segmentation
- Coalesces chapters relative to video duration (capped at 5 chapters for <30m videos) and splits text into 5–10 min subtopics.

### 3. Parallel Async LLM Synthesis
- Bounded Concurrency DAG scheduler executes independent subtopics in parallel background worker tasks.
- Controls local CLI sessions (Codex, Gemini, Claude, Ollama, AGY) through unified Harness adapters.

### 4. Knowledge Pack & Multi-Format Output
- Stores comprehensive analysis in a content-addressed **Knowledge Pack** zstd artifact.
- Once generated, reassembles into Blogs, Study Notes, or Obsidian Vaults in 1 second.

---

## 🎚️ Configuration & Customization

### Summary Depth Intensity (`--depth`)

Select your preferred summary detail level via CLI flag (`--depth` / `-d`) or inside `CHEW.md`:

- **`quick`** (`short` / `brief`): High-level milestone summary for fast scanning
- **`detailed`** (default): Balanced detailed summary with chapter subtopics and timestamp evidence
- **`deep`**: Comprehensive deep-dive analysis capturing every chapter, technical detail, and argument

### Tone & Output Customization (`CHEW.md` & `.chew/profiles/`)

Modify tone of voice, audience level, and layout format in auto-generated config files:

```text
CHEW.md               # Global project settings & shared LLM prompts
.chew/profiles/
├── blog.md           # Blog tone of voice & document layout format
├── study.md          # Study guide structure & Q&A format
└── obsidian.md       # Obsidian [[wikilink]] formatting
```

---

## 🚀 Performance Boost & OpenTelemetry Dashboard

### 16.3x Performance Improvement

Optimized pipeline segmentation and harness concurrency for a **16.3x speed boost**:

| Metric | Baseline | Optimized | Improvement |
|---|---|---|---|
| 25-min Tech Video Analysis | 30m 00s (1,800s) | **1m 50s (110s)** | **16.3x Faster** |
| Pipeline Tasks Generated | 61 fine tasks | **11 condensed tasks** | 82% Reduction |
| AI Harness Concurrency | 2 workers | **8 parallel workers** | 4x Increase |

Detailed Performance Report: [`reports/performance_analysis.md`](reports/performance_analysis.md)

### OpenTelemetry Jaeger UI Dashboard

Developers can inspect real-time span latency graphs in open-source Jaeger UI:

```bash
# Install optional telemetry package
pip install -e '.[telemetry]'

# Generate OpenTelemetry Trace report and Jaeger UI link
chew benchmark-dashboard
```

---

## 🛠️ Command Line Reference

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

---

## 🧩 Architecture Layout

Follows strict **Ports & Adapters (Hexagonal)** architecture rules. See [`AGENTS.md`](AGENTS.md) for full guidelines.

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

## 📄 License & Community

- **License**: [MIT License](LICENSE)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
