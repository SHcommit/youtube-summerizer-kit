"""Record explicit quality-gate results for a saved benchmark comparison."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.benchmark_metrics import QualityFloor, evaluate_quality_gate, load_metrics, write_json_once


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quality", type=Path, required=True, help="Reviewed quality JSON to validate and copy.")
    parser.add_argument("--current", type=Path, required=True, help="Candidate run directory receiving quality.json.")
    parser.add_argument("--evidence-recall", type=float, default=0.9)
    parser.add_argument("--timestamp-accuracy", type=float, default=0.8)
    parser.add_argument("--unsupported-claims", type=int, default=0)
    args = parser.parse_args()
    payload = json.loads(args.quality.read_text(encoding="utf-8"))
    current_metrics = load_metrics(args.current)
    floor = QualityFloor(args.evidence_recall, args.timestamp_accuracy, args.unsupported_claims)
    gate = evaluate_quality_gate(payload, floor)
    output = {
        **payload,
        "current_run_id": current_metrics.get("run_id", "unknown"),
        "quality_floor": {
            "evidence_recall": floor.evidence_recall,
            "timestamp_accuracy": floor.timestamp_accuracy,
            "unsupported_claims": floor.unsupported_claims,
        },
        "quality_gate": {"passed": gate.passed, "failures": list(gate.failures)},
    }
    output_path = args.current / "quality.json"
    write_json_once(output_path, output)
    print(output_path)
    raise SystemExit(0 if gate.passed else 1)


if __name__ == "__main__":
    main()
