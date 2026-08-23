"""Measure raw YouTube subtitle token baselines for the preprocessing spike.

This is deliberately a maintainer tool.  It obtains subtitle segments directly
from the yt-dlp adapter and never invokes a harness or persists an analysis.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from chew.benchmark.metrics import TranscriptMetrics, lock_hash, measure_text
from chew.core.identity import normalize_youtube_url
from chew.core.models import Transcript
from chew.pipeline.preprocessing import PreprocessingStats, TranscriptPreprocessor
from chew.pipeline.segmentation import SegmentationPolicy, segment_transcript
from chew.transcripts.yt_dlp import YtDlpSubtitleProvider

ROOT = Path(__file__).resolve().parents[1]


class TokenEncoder(Protocol):
    def encode(self, text: str) -> list[int]: ...


@dataclass(frozen=True)
class BaselineRow:
    key: str
    title: str
    expected_duration_seconds: int
    actual_duration_seconds: int
    transcript_source: str
    metrics: TranscriptMetrics


@dataclass(frozen=True)
class ComparisonRow:
    baseline: BaselineRow
    processed_metrics: TranscriptMetrics
    stats: PreprocessingStats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("baseline", "compare"), required=True)
    parser.add_argument("--language", default="en", help="Caption language requested from YouTube (default: en).")
    parser.add_argument("--lock-file", type=Path, default=ROOT / "reports" / "benchmark-videos.lock.json")
    parser.add_argument("--output", type=Path, help="Override the generated Markdown report path.")
    return parser.parse_args()


def _encoder() -> TokenEncoder:
    try:
        import tiktoken
    except ImportError as error:
        raise SystemExit(
            "This maintainer spike needs tiktoken. Run with: "
            "uv run --extra youtube --with tiktoken python scripts/spike_token_baseline.py --mode baseline"
        ) from error
    return tiktoken.get_encoding("cl100k_base")


def _load_videos(lock_file: Path) -> list[dict[str, Any]]:
    payload = json.loads(lock_file.read_text(encoding="utf-8"))
    videos = payload.get("videos")
    if not isinstance(videos, list) or not all(isinstance(video, dict) for video in videos):
        raise ValueError(f"Invalid benchmark lock file: {lock_file}")
    return videos


async def _fetch_transcript(video: dict[str, Any], language: str) -> Transcript:
    video_id = video["youtube_id"]
    source = normalize_youtube_url(f"https://www.youtube.com/watch?v={video_id}")
    transcript = await YtDlpSubtitleProvider(caption_kind="both").fetch(source, language)
    if transcript is None:
        raise RuntimeError(f"No subtitle track available for {video_id}")
    return transcript


def _baseline_row(video: dict[str, Any], transcript: Transcript, encoder: TokenEncoder) -> BaselineRow:
    raw_segments = [segment.text for segment in transcript.segments]
    token_count = len(encoder.encode(" ".join(raw_segments)))
    metrics = measure_text(video["key"], raw_segments, token_count)
    topic_count = len(segment_transcript(transcript, transcript.chapters, SegmentationPolicy()).topics)
    metrics = TranscriptMetrics(
        key=metrics.key,
        raw_chars=metrics.raw_chars,
        raw_tokens=metrics.raw_tokens,
        filler_count=metrics.filler_count,
        filler_ratio=metrics.filler_ratio,
        segment_count=topic_count,
    )
    return BaselineRow(
        key=video["key"],
        title=transcript.title or str(video.get("title") or video["youtube_id"]),
        expected_duration_seconds=int(video["duration_seconds"]),
        actual_duration_seconds=round(transcript.duration_ms / 1_000),
        transcript_source=transcript.provenance.value,
        metrics=metrics,
    )


async def _compare_video(video: dict[str, Any], language: str, encoder: TokenEncoder) -> ComparisonRow:
    transcript = await _fetch_transcript(video, language)
    baseline = _baseline_row(video, transcript, encoder)
    processed, stats = TranscriptPreprocessor().process(transcript)
    segments = [segment.text for segment in processed.segments]
    metrics = measure_text(video["key"], segments, len(encoder.encode(" ".join(segments))))
    topics = len(segment_transcript(processed, processed.chapters, SegmentationPolicy()).topics)
    processed_metrics = TranscriptMetrics(
        key=metrics.key,
        raw_chars=metrics.raw_chars,
        raw_tokens=metrics.raw_tokens,
        filler_count=metrics.filler_count,
        filler_ratio=metrics.filler_ratio,
        segment_count=topics,
    )
    return ComparisonRow(baseline, processed_metrics, stats)


def _render_baseline(lock_file: Path, rows: list[BaselineRow]) -> str:
    lines = [
        "# Transcript Token Baseline",
        "",
        "This report measures raw caption text before the Phase 1 preprocessing pipeline.",
        f"Benchmark lock SHA-256: `{lock_hash(lock_file)}`",
        "",
        "| Key | Duration (locked/actual) | Raw chars | cl100k tokens | Fillers | Filler ratio | Topics | Source |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        metrics = row.metrics
        duration = f"{row.expected_duration_seconds}s / {row.actual_duration_seconds}s"
        lines.append(
            f"| {row.key} | {duration} | {metrics.raw_chars:,} | {metrics.raw_tokens:,} | "
            f"{metrics.filler_count:,} | {metrics.filler_ratio:.2%} | {metrics.segment_count} | "
            f"{row.transcript_source} |"
        )
    lines.extend(("", "Duration differences should be reviewed before treating a run as comparable.", ""))
    return "\n".join(lines)


def _render_comparison(lock_file: Path, rows: list[ComparisonRow]) -> str:
    lines = [
        "# Transcript Preprocessing Comparison",
        "",
        "This report compares raw caption text with the current opt-in local preprocessing recipe.",
        f"Benchmark lock SHA-256: `{lock_hash(lock_file)}`",
        "",
        "| Key | Raw tokens | Processed tokens | Reduction | Raw topics | Processed topics | Applied stages |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        before = row.baseline.metrics.raw_tokens
        after = row.processed_metrics.raw_tokens
        reduction = (1 - after / before) * 100 if before else 0.0
        lines.append(
            f"| {row.baseline.key} | {before:,} | {after:,} | {reduction:.2f}% | "
            f"{row.baseline.metrics.segment_count} | {row.processed_metrics.segment_count} | "
            f"{', '.join(row.stats.applied_strategies)} |"
        )
    lines.extend(("", "These are tokenizer comparison figures, not provider billing or quality claims.", ""))
    return "\n".join(lines)


async def _run() -> int:
    args = _parse_args()
    encoder = _encoder()
    videos = _load_videos(args.lock_file)
    if args.mode == "baseline":
        rows = [
            _baseline_row(video, await _fetch_transcript(video, args.language), encoder)
            for video in videos
        ]
        report = _render_baseline(args.lock_file, rows)
        output = args.output or ROOT / "reports" / "token-baseline.md"
    else:
        rows = [await _compare_video(video, args.language, encoder) for video in videos]
        report = _render_comparison(args.lock_file, rows)
        output = args.output or ROOT / "reports" / "token-comparison.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
