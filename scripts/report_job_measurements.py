"""Render a read-only Markdown profile from a completed chew SQLite run."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Aggregate:
    attempts: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_duration_ns: int = 0
    input_chars: int = 0
    input_segments: int = 0
    repairs: int = 0
    retries: int = 0
    schema_chars: int = 0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _integer(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _render(database: Path, run_id: str) -> str:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT m.task, m.runtime_id, m.model, m.usage_json, m.details_json "
            "FROM job_measurements m JOIN jobs j ON j.job_id = m.job_id "
            "WHERE j.run_id = ? ORDER BY m.measurement_id",
            (run_id,),
        ).fetchall()
    groups: dict[tuple[str, str, str], Aggregate] = defaultdict(Aggregate)
    for task, runtime, model, usage_json, details_json in rows:
        usage = json.loads(str(usage_json))
        details = json.loads(str(details_json))
        aggregate = groups[(str(task), str(runtime), str(model or "unknown"))]
        aggregate.attempts += 1
        aggregate.input_tokens += _integer(usage.get("input_tokens"))
        aggregate.output_tokens += _integer(usage.get("output_tokens"))
        aggregate.total_duration_ns += _integer(usage.get("total_duration_ns"))
        aggregate.input_chars += _integer(details.get("input_chars"))
        aggregate.input_segments += _integer(details.get("input_segment_count"))
        aggregate.schema_chars += _integer(details.get("output_schema_chars"))
        aggregate.repairs += int(details.get("is_repair") is True)
        aggregate.retries += int(details.get("retry") is True)
    lines = [
        f"# Generation Profile: {run_id}",
        "",
        "Provider usage is reported only when the runtime supplied it. Request-size fields are structural diagnostics, not billing tokens.",
        "",
        "| Task | Runtime | Model | Attempts | Input / output tokens | Total duration | Input chars | Segments | Schema chars | Repairs | Retries |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for (task, runtime, model), value in sorted(groups.items()):
        duration = f"{value.total_duration_ns / 1_000_000_000:.3f}s" if value.total_duration_ns else "unknown"
        tokens = f"{value.input_tokens:,} / {value.output_tokens:,}" if value.input_tokens or value.output_tokens else "unknown"
        lines.append(
            f"| {task} | {runtime} | {model} | {value.attempts} | {tokens} | {duration} | "
            f"{value.input_chars:,} | {value.input_segments:,} | {value.schema_chars:,} | {value.repairs} | {value.retries} |"
        )
    if not rows:
        lines.extend(("| No measurements | - | - | 0 | unknown | unknown | 0 | 0 | 0 | 0 | 0 |", "", "No generation attempt records exist for this run."))
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = _arguments()
    report = _render(args.database, args.run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
