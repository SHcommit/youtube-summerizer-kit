"""One-command maintainer benchmark report orchestration."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks import run_preprocessing
from benchmarks.benchmark_metrics import build_report_data, load_metrics, write_text_once
from benchmarks.render_report import render_html, render_markdown


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    report = subcommands.add_parser("report", help="Run current metrics and render baseline/current report.")
    report.add_argument("--baseline-dir", type=Path, required=True)
    report.add_argument("--lock-file", type=Path, default=Path("benchmarks/videos.lock.json"))
    report.add_argument("--output-root", type=Path, default=run_preprocessing.REPORT_ROOT)
    report.add_argument("--quality", type=Path)
    report.add_argument("--depth", default="detailed")
    report.add_argument("--concurrency", type=int, default=5)
    report.add_argument("--preprocessing", default="current")
    report.add_argument("--baseline-tag", default="unknown")
    report.add_argument("--baseline-commit", default="unknown")
    report.add_argument("--candidate-ref", default="unknown")
    report.add_argument("--candidate-commit", default="unknown")
    report.add_argument("--target-release", default="unknown")
    args = parser.parse_args(argv)
    if args.command == "report":
        return asyncio.run(_run_report(args))
    return 2


async def _run_report(args: argparse.Namespace) -> int:
    release = {
        "baseline_tag": args.baseline_tag,
        "baseline_commit": args.baseline_commit,
        "candidate_ref": args.candidate_ref,
        "candidate_commit": args.candidate_commit,
        "target_release": args.target_release,
        "report_version": "benchmark-report/v1",
    }
    current_dir = await run_preprocessing.run(
        "current",
        args.lock_file,
        args.output_root,
        args.depth,
        concurrency=args.concurrency,
        release=release,
        preprocessing=args.preprocessing,
    )
    quality = json.loads(args.quality.read_text(encoding="utf-8")) if args.quality else None
    data = build_report_data(
        load_metrics(args.baseline_dir),
        load_metrics(current_dir),
        quality,
    )
    write_text_once(current_dir / "report.md", render_markdown(data))
    write_text_once(current_dir / "report.html", render_html(data))
    print(current_dir / "report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
