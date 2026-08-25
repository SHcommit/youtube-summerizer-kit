"""Run metrics-only transcript preprocessing benchmarks for locked videos."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from time import monotonic
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.benchmark_metrics import load_video_lock, lock_file_sha256, write_metrics_run
from chew.core.identity import normalize_youtube_url
from chew.pipeline.preprocessing import count_fillers
from chew.pipeline.segmentation import SegmentationPolicy, segment_transcript
from chew.transcripts import TranscriptService, default_providers

REPORT_ROOT = Path("reports/performance-comparisons/transcript-preprocessing")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label", choices=("baseline", "current"))
    parser.add_argument("--lock-file", type=Path, default=Path("benchmarks/videos.lock.json"))
    parser.add_argument("--output-root", type=Path, default=REPORT_ROOT)
    parser.add_argument("--depth", default="detailed")
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--preprocessing", default="current")
    args = parser.parse_args()
    run_dir = asyncio.run(
        run(
            args.label,
            args.lock_file,
            args.output_root,
            args.depth,
            concurrency=args.concurrency,
            preprocessing=args.preprocessing,
        )
    )
    print(run_dir)


async def run(
    label: str,
    lock_file: Path,
    output_root: Path,
    depth: str,
    *,
    concurrency: int = 1,
    release: dict[str, object] | None = None,
    preprocessing: str = "current",
) -> Path:
    locked = load_video_lock(lock_file)
    run_id = f"{label}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    service = TranscriptService(default_providers())
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def measure(video: Any) -> dict[str, Any]:
        async with semaphore:
            row = await _measure_video(
                video.key,
                video.youtube_id,
                video.language,
                service,
                depth,
                preprocessing=preprocessing,
            )
            row["locked_title"] = video.title
            row["locked_language"] = video.language
            row["locked_duration_seconds"] = video.duration_seconds
            return row

    videos = list(await asyncio.gather(*(measure(video) for video in locked.videos)))
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "label": label,
        "created_at": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "lock_file": str(lock_file),
        "lock_file_sha256": lock_file_sha256(lock_file),
        "runtime_config": {
            "depth": depth,
            "llm_calls": 0,
            "preprocessing": preprocessing,
        },
        "release": release or {},
        "videos": videos,
    }
    return write_metrics_run(output_root, run_id, payload)


async def _measure_video(
    key: str,
    youtube_id: str,
    language: str,
    service: TranscriptService,
    depth: str,
    *,
    preprocessing: str = "current",
) -> dict[str, Any]:
    source = normalize_youtube_url(f"https://www.youtube.com/watch?v={youtube_id}")
    started = monotonic()
    try:
        fetch_started = monotonic()
        resolution = await service.resolve(source, language, include_optional=False)
        fetch_latency = monotonic() - fetch_started
        transcript = resolution.transcript
        text = "\n".join(segment.text for segment in transcript.segments)

        preprocessing_started = monotonic()
        processed_transcript = _apply_preprocessing(transcript, preprocessing)
        preprocessing_latency = monotonic() - preprocessing_started
        processed_text = "\n".join(segment.text for segment in processed_transcript.segments)

        segmentation_started = monotonic()
        manifest = segment_transcript(
            processed_transcript,
            processed_transcript.chapters,
            SegmentationPolicy(),
            depth=depth,
        )
        segmentation_latency = monotonic() - segmentation_started
        total_latency = monotonic() - started
        raw_tokens = _count_tokens(text)
        processed_tokens = _count_tokens(processed_text)
        filler_count = _count_fillers(text)
        return {
            "key": key,
            "youtube_id": youtube_id,
            "requested_language": language,
            "status": "success",
            "substituted": False,
            "transcript_provider": resolution.provider,
            "language": transcript.language,
            "duration_seconds": round(transcript.duration_ms / 1000),
            "segment_count": len(transcript.segments),
            "segmentation_count": len(manifest.topics),
            "raw_characters": len(text),
            "processed_characters": len(processed_text),
            "raw_input_tokens": raw_tokens,
            "processed_input_tokens": processed_tokens,
            "fetch_latency_seconds": round(fetch_latency, 6),
            "preprocessing_latency_seconds": round(preprocessing_latency, 6),
            "segmentation_latency_seconds": round(segmentation_latency, 6),
            "total_latency_seconds": round(total_latency, 6),
            "stages": [
                {
                    "name": "raw_transcript",
                    "characters": len(text),
                    "tokens": raw_tokens,
                    "segments": len(transcript.segments),
                    "latency_seconds": round(fetch_latency, 6),
                },
                {
                    "name": "processed_transcript",
                    "characters": len(processed_text),
                    "tokens": processed_tokens,
                    "segments": len(processed_transcript.segments),
                    "latency_seconds": round(preprocessing_latency, 6),
                },
                {
                    "name": "segmentation",
                    "topic_count": len(manifest.topics),
                    "chapter_count": len(manifest.chapters),
                    "latency_seconds": round(segmentation_latency, 6),
                },
            ],
            "filler_count": filler_count,
            "filler_ratio": round(filler_count / max(1, raw_tokens), 6),
            "retries": 0,
            "failures": 0,
        }
    except Exception as error:
        return {
            "key": key,
            "youtube_id": youtube_id,
            "requested_language": language,
            "status": "failed",
            "substituted": False,
            "error": f"{type(error).__name__}: {error}",
            "fetch_latency_seconds": 0.0,
            "preprocessing_latency_seconds": 0.0,
            "segmentation_latency_seconds": 0.0,
            "total_latency_seconds": round(monotonic() - started, 6),
            "retries": 0,
            "failures": 1,
        }


def _apply_preprocessing(transcript: Any, preprocessing: str) -> Any:
    """Benchmark hook for post-feature validation.

    The benchmark does not implement product preprocessing itself. It records
    which path was selected and provides the single integration point where a
    future transcript-preprocessing feature should be invoked.
    """
    if preprocessing == "none":
        return transcript
    try:
        module = import_module("chew.pipeline.preprocessing")
    except ModuleNotFoundError as error:
        if error.name == "chew.pipeline.preprocessing":
            return transcript
        raise
    processed, _ = module.preprocess_transcript(transcript)
    return processed


def _count_tokens(text: str) -> int:
    try:
        import tiktoken
    except ImportError:
        return len(text.split())
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def _count_fillers(text: str) -> int:
    return count_fillers(text)


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


if __name__ == "__main__":
    main()
