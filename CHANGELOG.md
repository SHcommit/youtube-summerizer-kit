# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Core CLI Rebranding (`chew`)**:
  - Rebranded the primary CLI command to `chew` (`chew summarize`, `chew blog`, `chew study`, `chew obsidian`, `chew doctor`, etc.).
- **Local Audio and Video File Input**:
  - Direct transcription of local media files (`.mp3`, `.mp4`, `.m4a`, `.wav`, `.mkv`, `.mov`, `.aac`, `.flac`, `.ogg`, `.webm`, etc.) via `faster-whisper`.
  - Content-addressed SHA-256 fingerprinting for local files so Knowledge Packs are reused even after moving or renaming files.
  - Zero-copy processing: local files are never copied, altered, or deleted.
  - Command shortcut: run `chew summarize ./file.mp3`, `chew study ./lecture.mp4`, or `chew ./recording.m4a`.
  - Stored absolute source path preservation in SQLite DB for interrupted run recovery via `chew resume`.
  - Separate Korean and English error diagnostics for local media vs YouTube inputs.
- **AI Runtime Harness Adapters**:
  - Added native `Antigravity CLI (agy)` harness adapter (`AntigravityHarness`) supporting headless JSON print mode with structured schema validation.
- **Ports & Adapters Architecture Refactoring**:
  - Reorganized project into 9 clean subpackages (`core`, `pipeline`, `storage`, `harness`, `transcripts`, `app`, `retention`, `benchmark`, `cli`).
- **Architecture Diagrams**:
  - Interactive Mermaid diagram source code and high-resolution PNG visualizations for user flow and internal pipeline in both English and Korean.

## [0.1.0] - 2026-08-16

### Added
- **Core CLI (`chew`)**:
  - Local-first resumable knowledge compiler for YouTube videos.
  - Chapter-aware and adaptive 5-10 minute topic segmentation.
  - Hierarchical topic → chapter → Knowledge Pack synthesis pipeline.
- **AI Runtime Adapters**:
  - Integrated support for Codex CLI, Gemini CLI, Claude Code, and Ollama with automatic fallback and login status preflight checks.
- **Purpose-Specific Reassembly**:
  - Digest generation (with timestamped evidence), Blog post drafting, Study notes, and Obsidian vault export with `[[wikilinks]]`.
- **Durable Recovery & Caching**:
  - SQLite WAL state machine with worker claim leases and heartbeat recovery.
  - Resume interrupted runs with `chew resume [RUN_ID]`.
  - Content-addressed Knowledge Pack and output caching using canonical JSON SHA-256 digests compressed with `zstd`.
- **Storage Retention & Policy Management**:
  - Retention policies (`compact`, `private`, `archive`).
  - Management commands: `chew storage`, `chew cleanup`, `chew delete`, and `chew purge`.
- **Benchmarking Suite**:
  - Automated quality & recall benchmark framework (`chew benchmark`) comparing direct Gemini URL analysis against hierarchical pipeline synthesis.
