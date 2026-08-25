"""Pure helpers for maintainer benchmark runs and reports."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class BenchmarkVideo:
    key: str
    youtube_id: str
    title: str
    language: str
    duration_seconds: int

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.youtube_id}"


@dataclass(frozen=True, slots=True)
class VideoLock:
    locked_at: str
    verification_method: str
    videos: tuple[BenchmarkVideo, ...]


@dataclass(frozen=True, slots=True)
class ComparisonEligibility:
    eligible: bool
    reasons: tuple[str, ...]

    @classmethod
    def from_metrics(cls, baseline: dict[str, Any], current: dict[str, Any]) -> ComparisonEligibility:
        reasons: list[str] = []
        if baseline.get("lock_file_sha256") != current.get("lock_file_sha256"):
            reasons.append("lock_file_sha256 differs")

        baseline_by_key = _videos_by_key(baseline)
        current_by_key = _videos_by_key(current)
        if set(baseline_by_key) != set(current_by_key):
            reasons.append("video key set differs")

        for label, videos in (("baseline", baseline_by_key), ("current", current_by_key)):
            for key, video in sorted(videos.items()):
                status = video.get("status")
                if status != "success":
                    reasons.append(f"{label} video {key} status is {status}")
                if video.get("substituted") is True:
                    reasons.append(f"{label} video {key} used a substituted input")
        return cls(not reasons, tuple(reasons))


@dataclass(frozen=True, slots=True)
class QualityFloor:
    evidence_recall: float = 0.9
    timestamp_accuracy: float = 0.8
    unsupported_claims: int = 0


@dataclass(frozen=True, slots=True)
class QualityGateResult:
    passed: bool
    failures: tuple[str, ...]


DEFAULT_QUALITY_FLOOR = QualityFloor()


def load_video_lock(path: Path) -> VideoLock:
    payload = json.loads(path.read_text(encoding="utf-8"))
    locked_at = _required_string(payload, "locked_at")
    verification_method = _required_string(payload, "verification_method")
    raw_videos = payload.get("videos")
    if not isinstance(raw_videos, list) or not raw_videos:
        raise ValueError("videos must be a non-empty list")

    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    videos: list[BenchmarkVideo] = []
    for raw_video in raw_videos:
        if not isinstance(raw_video, dict):
            raise ValueError("video entries must be objects")
        key = _required_string(raw_video, "key")
        youtube_id = _required_string(raw_video, "youtube_id")
        title = _required_string(raw_video, "title")
        language = _required_string(raw_video, "language")
        duration_seconds = raw_video.get("duration_seconds")
        if not isinstance(duration_seconds, int) or duration_seconds <= 0:
            raise ValueError(f"video {key} duration_seconds must be a positive integer")
        if key in seen_keys:
            raise ValueError(f"duplicate video key: {key}")
        if youtube_id in seen_ids:
            raise ValueError(f"duplicate youtube_id: {youtube_id}")
        seen_keys.add(key)
        seen_ids.add(youtube_id)
        videos.append(BenchmarkVideo(key, youtube_id, title, language, duration_seconds))
    return VideoLock(locked_at, verification_method, tuple(videos))


def lock_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_metrics_run(report_root: Path, run_id: str, payload: dict[str, Any]) -> Path:
    run_dir = report_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json_once(run_dir / "metrics.json", payload)
    return run_dir


def load_metrics(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "metrics.json"
    if not path.is_file():
        raise FileNotFoundError(f"metrics.json not found in {run_dir}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("metrics.json must contain an object")
    return payload


def evaluate_quality_gate(quality: dict[str, Any], floor: QualityFloor = DEFAULT_QUALITY_FLOOR) -> QualityGateResult:
    videos = quality.get("videos")
    if not isinstance(videos, list):
        raise ValueError("quality videos must be a list")
    failures: list[str] = []
    for item in videos:
        if not isinstance(item, dict):
            raise ValueError("quality video entries must be objects")
        key = _required_string(item, "key")
        evidence_recall = _required_number(item, "evidence_recall")
        timestamp_accuracy = _required_number(item, "timestamp_accuracy")
        unsupported_claims = item.get("unsupported_claims")
        if not isinstance(unsupported_claims, int) or unsupported_claims < 0:
            raise ValueError(f"{key} unsupported_claims must be a non-negative integer")
        if evidence_recall < floor.evidence_recall:
            failures.append(
                f"{key} evidence_recall {evidence_recall:.4f} below floor {floor.evidence_recall:.4f}"
            )
        if timestamp_accuracy < floor.timestamp_accuracy:
            failures.append(
                f"{key} timestamp_accuracy {timestamp_accuracy:.4f} below floor {floor.timestamp_accuracy:.4f}"
            )
        if unsupported_claims > floor.unsupported_claims:
            failures.append(f"{key} unsupported_claims {unsupported_claims} above floor {floor.unsupported_claims}")
    return QualityGateResult(not failures, tuple(failures))


def build_report_data(
    baseline: dict[str, Any],
    current: dict[str, Any],
    quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    eligibility = ComparisonEligibility.from_metrics(baseline, current)
    baseline_by_key = _videos_by_key(baseline)
    current_by_key = _videos_by_key(current)
    rows: list[dict[str, Any]] = []
    for key in sorted(set(baseline_by_key) & set(current_by_key)):
        base = baseline_by_key[key]
        cur = current_by_key[key]
        baseline_tokens = int(base.get("processed_input_tokens", 0))
        current_tokens = int(cur.get("processed_input_tokens", 0))
        baseline_latency = float(base.get("preprocessing_latency_seconds", 0.0))
        current_latency = float(cur.get("preprocessing_latency_seconds", 0.0))
        rows.append(
            {
                "key": key,
                "baseline_tokens": baseline_tokens,
                "current_tokens": current_tokens,
                "token_delta": current_tokens - baseline_tokens,
                "token_reduction_ratio": _reduction_ratio(baseline_tokens, current_tokens),
                "baseline_latency_seconds": baseline_latency,
                "current_latency_seconds": current_latency,
                "latency_delta_seconds": round(current_latency - baseline_latency, 6),
                "baseline_segmentation_count": int(base.get("segmentation_count", 0)),
                "current_segmentation_count": int(cur.get("segmentation_count", 0)),
                "stages": cur.get("stages", []),
                "status": "success" if base.get("status") == cur.get("status") == "success" else "invalid",
            }
        )
    quality_result = (
        _quality_result_for_report(quality, set(rows_by_key(rows)), current_run_id=str(current.get("run_id", "")))
        if quality is not None
        else None
    )
    summary = _aggregate_summary(rows, baseline, current)
    dimensions, better, risks = _dimension_summary(rows, eligibility, quality_result, summary)
    decision = _decision_summary(eligibility, quality_result, dimensions, better, risks)
    change_summary = _change_summary(baseline, current)
    state = _state_summary(baseline, current, quality, rows, eligibility)
    return {
        "baseline_run_id": baseline.get("run_id"),
        "current_run_id": current.get("run_id"),
        "eligible": eligibility.eligible,
        "eligibility_reasons": list(eligibility.reasons),
        "quality_gate": None
        if quality_result is None
        else {"passed": quality_result.passed, "failures": list(quality_result.failures)},
        "decision": decision,
        "dimensions": dimensions,
        "better": better,
        "risks": risks,
        "summary": summary,
        "change_summary": change_summary,
        "state": state,
        "videos": rows,
    }


def write_json_once(path: Path, payload: dict[str, Any]) -> None:
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    write_text_once(path, content)


def write_text_once(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as error:
        raise FileExistsError(f"{path} already exists") from error
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _dimension_summary(
    rows: list[dict[str, Any]],
    eligibility: ComparisonEligibility,
    quality_result: QualityGateResult | None,
    summary: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    baseline_tokens = int(summary["baseline_total_tokens"])
    current_tokens = int(summary["current_total_tokens"])
    token_delta = int(summary["total_token_delta"])
    token_reduction = float(summary["total_token_reduction_ratio"])
    baseline_latency = float(summary["baseline_total_latency_seconds"])
    current_latency = float(summary["current_total_latency_seconds"])
    latency_delta = float(summary["total_latency_delta_seconds"])
    latency_ratio = _increase_ratio(baseline_latency, current_latency)
    segment_delta = int(summary["total_segmentation_delta"])

    better: list[str] = []
    risks: list[str] = []

    cost_status = "better" if token_delta < 0 else "worse" if token_delta > 0 else "neutral"
    if token_delta < 0:
        better.append(f"Cost: input tokens fell by {abs(token_delta):,} ({token_reduction:.1%}).")
    elif token_delta > 0:
        risks.append(f"Cost: input tokens increased by {token_delta:,}.")

    speed_status = "risk" if latency_ratio > 0.10 else "better" if latency_delta < 0 else "neutral"
    if latency_ratio > 0.10:
        risks.append(f"Speed: preprocessing latency rose by {latency_delta:.3f}s ({latency_ratio:.1%}).")
    elif latency_delta < 0:
        better.append(f"Speed: preprocessing latency fell by {abs(latency_delta):.3f}s.")
    if segment_delta < 0:
        better.append(f"Speed: segmentation count fell by {abs(segment_delta)}.")
    elif segment_delta > 0:
        risks.append(f"Speed: segmentation count increased by {segment_delta}.")
    if not summary["candidate_effect_detected"] and summary["current_preprocessing"] != "none":
        risks.append(
            "No measurable preprocessing effect was detected; verify that the candidate preprocessing path is enabled."
        )

    if quality_result is None:
        quality_status = "not_evaluated"
        risks.append("Quality: quality gate was not evaluated; do not adopt from token reduction alone.")
    elif quality_result.passed:
        quality_status = "pass"
        better.append("Quality: evidence, timestamp, and unsupported-claim gates passed.")
    else:
        quality_status = "fail"
        risks.append("Quality gate failed: " + "; ".join(quality_result.failures))

    reliability_status = "pass" if eligibility.eligible else "fail"
    if eligibility.eligible:
        better.append("Reliability: all compared videos succeeded without substitutions.")
    else:
        risks.append("Reliability: " + "; ".join(eligibility.reasons))

    reproducibility_status = "pass" if "lock_file_sha256 differs" not in eligibility.reasons else "fail"
    if reproducibility_status == "pass":
        better.append("Reproducibility: baseline and current use the same lock hash.")
    else:
        risks.append("Reproducibility: lock hash differs, so direct comparison is invalid.")

    dimensions = [
        {
            "name": "Cost",
            "status": cost_status,
            "baseline": baseline_tokens,
            "current": current_tokens,
            "delta": token_delta,
            "summary": f"{baseline_tokens:,} -> {current_tokens:,} tokens ({token_reduction:.1%} reduction)",
        },
        {
            "name": "Speed",
            "status": speed_status,
            "baseline": round(baseline_latency, 6),
            "current": round(current_latency, 6),
            "delta": latency_delta,
            "summary": f"{baseline_latency:.3f}s -> {current_latency:.3f}s preprocessing latency",
        },
        {
            "name": "Quality",
            "status": quality_status,
            "baseline": None,
            "current": None,
            "delta": None,
            "summary": _quality_summary(quality_result),
        },
        {
            "name": "Reliability",
            "status": reliability_status,
            "baseline": None,
            "current": None,
            "delta": None,
            "summary": "All videos comparable" if eligibility.eligible else "; ".join(eligibility.reasons),
        },
        {
            "name": "Reproducibility",
            "status": reproducibility_status,
            "baseline": None,
            "current": None,
            "delta": None,
            "summary": "Matching lock hash" if reproducibility_status == "pass" else "Lock hash mismatch",
        },
    ]
    return dimensions, better, risks


def _aggregate_summary(
    rows: list[dict[str, Any]],
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    baseline_tokens = sum(int(row["baseline_tokens"]) for row in rows)
    current_tokens = sum(int(row["current_tokens"]) for row in rows)
    baseline_latency = sum(float(row["baseline_latency_seconds"]) for row in rows)
    current_latency = sum(float(row["current_latency_seconds"]) for row in rows)
    baseline_segments = sum(int(row["baseline_segmentation_count"]) for row in rows)
    current_segments = sum(int(row["current_segmentation_count"]) for row in rows)
    token_delta = current_tokens - baseline_tokens
    segment_delta = current_segments - baseline_segments
    latency_delta = round(current_latency - baseline_latency, 6)
    candidate_effect_detected = any(
        int(row["token_delta"]) != 0
        or int(row["current_segmentation_count"]) != int(row["baseline_segmentation_count"])
        for row in rows
    )
    return {
        "baseline_total_tokens": baseline_tokens,
        "current_total_tokens": current_tokens,
        "total_token_delta": token_delta,
        "total_token_reduction_ratio": _reduction_ratio(baseline_tokens, current_tokens),
        "baseline_total_latency_seconds": round(baseline_latency, 6),
        "current_total_latency_seconds": round(current_latency, 6),
        "total_latency_delta_seconds": latency_delta,
        "baseline_total_segments": baseline_segments,
        "current_total_segments": current_segments,
        "total_segmentation_delta": segment_delta,
        "baseline_preprocessing": _runtime_preprocessing(baseline),
        "current_preprocessing": _runtime_preprocessing(current),
        "candidate_effect_detected": candidate_effect_detected,
    }


def _decision_summary(
    eligibility: ComparisonEligibility,
    quality_result: QualityGateResult | None,
    dimensions: list[dict[str, Any]],
    better: list[str],
    risks: list[str],
) -> dict[str, str]:
    by_name = {str(item["name"]): item for item in dimensions}
    if not eligibility.eligible:
        return {
            "status": "invalid",
            "summary": "Comparison is invalid until lock hash, status, and substitutions match.",
        }
    if quality_result is None:
        return {
            "status": "revise",
            "summary": "Quality was not evaluated; keep this as evidence, not an adoption decision.",
        }
    if not quality_result.passed:
        return {
            "status": "reject",
            "summary": "Quality floor failed, so the candidate cannot be adopted.",
        }
    if by_name["Speed"]["status"] == "risk":
        if by_name["Cost"]["status"] == "better":
            summary = "Token cost improved, but speed regression needs review before adoption."
        else:
            summary = "Speed regressed without a confirmed cost improvement; revise before adoption."
        return {
            "status": "revise",
            "summary": summary,
        }
    if by_name["Cost"]["status"] == "better" and better and not risks:
        return {
            "status": "adopt",
            "summary": "Candidate improves cost while passing quality, reliability, and reproducibility gates.",
        }
    return {
        "status": "revise",
        "summary": "Evidence is mixed; review the listed risks before deciding.",
    }


def _quality_summary(quality_result: QualityGateResult | None) -> str:
    if quality_result is None:
        return "Not evaluated"
    if quality_result.passed:
        return "Quality gate passed"
    return "Quality gate failed"


def _change_summary(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    baseline_config = baseline.get("runtime_config") if isinstance(baseline.get("runtime_config"), dict) else {}
    current_config = current.get("runtime_config") if isinstance(current.get("runtime_config"), dict) else {}
    previous_preprocessing = str(baseline_config.get("preprocessing", "none"))
    current_preprocessing = str(current_config.get("preprocessing", "current"))
    return {
        "previous": {
            "label": "Previous pipeline",
            "mode": previous_preprocessing,
            "flow": "Raw transcript -> segmentation -> LLM-ready transcript",
            "summary": "Baseline preserves the transcript mostly as acquired and measures the current segmentation path without extra preprocessing.",
        },
        "current": {
            "label": "Current candidate",
            "mode": current_preprocessing,
            "flow": "Transcript preprocessing -> processed transcript -> segmentation -> LLM-ready transcript",
            "summary": f"Candidate runs `{current_preprocessing}` before segmentation and records cost, speed, quality, reliability, and reproducibility evidence.",
        },
    }


def _state_summary(
    baseline: dict[str, Any],
    current: dict[str, Any],
    quality: dict[str, Any] | None,
    rows: list[dict[str, Any]],
    eligibility: ComparisonEligibility,
) -> dict[str, Any]:
    quality_gate = quality.get("quality_gate") if isinstance(quality, dict) else None
    quality_floor = quality.get("quality_floor") if isinstance(quality, dict) else None
    return {
        "baseline_run_id": baseline.get("run_id"),
        "current_run_id": current.get("run_id"),
        "baseline_git_sha": baseline.get("git_sha", "unknown"),
        "current_git_sha": current.get("git_sha", "unknown"),
        "baseline_lock_hash": baseline.get("lock_file_sha256", "unknown"),
        "current_lock_hash": current.get("lock_file_sha256", "unknown"),
        "baseline_tag": _release_value(baseline, "baseline_tag", fallback_metrics=current),
        "baseline_commit": _release_value(baseline, "baseline_commit", fallback_metrics=current),
        "candidate_ref": _release_value(current, "candidate_ref"),
        "candidate_commit": _release_value(current, "candidate_commit"),
        "target_release": _release_value(current, "target_release"),
        "report_version": _release_value(current, "report_version"),
        "video_count": len(rows),
        "eligible": eligibility.eligible,
        "quality_gate_recorded": isinstance(quality_gate, dict),
        "quality_floor": quality_floor if isinstance(quality_floor, dict) else None,
    }


def _release_value(metrics: dict[str, Any], key: str, *, fallback_metrics: dict[str, Any] | None = None) -> object:
    release = metrics.get("release")
    if isinstance(release, dict) and key in release:
        return release[key]
    fallback_release = fallback_metrics.get("release") if fallback_metrics is not None else None
    if isinstance(fallback_release, dict) and key in fallback_release:
        return fallback_release[key]
    return "unknown"


def _runtime_preprocessing(metrics: dict[str, Any]) -> str:
    config = metrics.get("runtime_config")
    if isinstance(config, dict):
        return str(config.get("preprocessing", "unknown"))
    return "unknown"


def _quality_result_for_report(
    quality: dict[str, Any],
    expected_keys: set[str],
    *,
    current_run_id: str,
) -> QualityGateResult:
    gate = quality.get("quality_gate")
    if isinstance(gate, dict) and isinstance(gate.get("passed"), bool) and isinstance(gate.get("failures"), list):
        result = QualityGateResult(
            bool(gate["passed"]),
            tuple(str(failure) for failure in gate["failures"]),
        )
    else:
        result = evaluate_quality_gate(quality, _quality_floor_from_payload(quality))

    quality_keys = _quality_video_keys(quality)
    failures = list(result.failures)
    quality_current_run_id = quality.get("current_run_id")
    if isinstance(quality_current_run_id, str) and quality_current_run_id != current_run_id:
        failures.append(
            f"Quality current_run_id {quality_current_run_id} does not match current run {current_run_id}"
        )
    if quality_keys != expected_keys:
        missing = sorted(expected_keys - quality_keys)
        unexpected = sorted(quality_keys - expected_keys)
        parts: list[str] = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if unexpected:
            parts.append("unexpected " + ", ".join(unexpected))
        failures.append("Quality keys differ: " + "; ".join(parts))
    return QualityGateResult(result.passed and not failures, tuple(failures))


def _quality_floor_from_payload(quality: dict[str, Any]) -> QualityFloor:
    floor = quality.get("quality_floor")
    if not isinstance(floor, dict):
        return DEFAULT_QUALITY_FLOOR
    return QualityFloor(
        evidence_recall=float(floor.get("evidence_recall", DEFAULT_QUALITY_FLOOR.evidence_recall)),
        timestamp_accuracy=float(floor.get("timestamp_accuracy", DEFAULT_QUALITY_FLOOR.timestamp_accuracy)),
        unsupported_claims=int(floor.get("unsupported_claims", DEFAULT_QUALITY_FLOOR.unsupported_claims)),
    )


def _quality_video_keys(quality: dict[str, Any]) -> set[str]:
    videos = quality.get("videos")
    if not isinstance(videos, list):
        return set()
    return {item["key"] for item in videos if isinstance(item, dict) and isinstance(item.get("key"), str)}


def rows_by_key(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["key"]): row for row in rows}


def _required_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if not isinstance(value, int | float):
        raise ValueError(f"{key} must be numeric")
    return float(value)


def _videos_by_key(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_videos = metrics.get("videos")
    if not isinstance(raw_videos, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in raw_videos:
        if not isinstance(item, dict) or not isinstance(item.get("key"), str):
            continue
        result[item["key"]] = item
    return result


def _reduction_ratio(baseline: int, current: int) -> float:
    if baseline <= 0:
        return 0.0
    return round((baseline - current) / baseline, 6)


def _increase_ratio(baseline: float, current: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((current - baseline) / baseline, 6)
