from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from benchmarks import benchmark_report, render_report, run_preprocessing  # noqa: E402
from benchmarks.benchmark_metrics import (  # noqa: E402
    ComparisonEligibility,
    QualityFloor,
    build_report_data,
    evaluate_quality_gate,
    load_metrics,
    load_video_lock,
    write_metrics_run,
)
from chew.core.models import Provenance, SourceIdentity, Transcript, TranscriptSegment  # noqa: E402
from chew.transcripts.service import TranscriptResolution  # noqa: E402


class ResolvingTranscriptService:
    def __init__(self) -> None:
        self.calls: list[tuple[SourceIdentity, str, bool]] = []

    async def resolve(
        self, source: SourceIdentity, language: str, *, include_optional: bool = False
    ) -> TranscriptResolution:
        self.calls.append((source, language, include_optional))
        transcript = Transcript(
            source=source,
            language="en",
            duration_ms=10_000,
            provenance=Provenance.TRANSCRIPT_API,
            segments=(TranscriptSegment(start_ms=0, end_ms=10_000, text="Um useful benchmark text."),),
            title="Benchmark video",
        )
        return TranscriptResolution(transcript, "fake-provider", ())


def test_documented_benchmark_scripts_show_help_from_repo_root() -> None:
    for script in (
        "benchmarks/run_preprocessing.py",
        "benchmarks/render_report.py",
        "benchmarks/evaluate_quality.py",
    ):
        result = subprocess.run(
            [sys.executable, script, "--help"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "usage:" in result.stdout


def test_canonical_lock_includes_the_korean_lecture_with_its_caption_language() -> None:
    locked = load_video_lock(REPO_ROOT / "benchmarks" / "videos.lock.json")
    korean_lecture = next(
        video
        for video in locked.videos
        if video.key == "youtube_ko_45m46s_for_benchmark"
    )

    assert korean_lecture.youtube_id == "YcA31dmSNMk"
    assert korean_lecture.language == "ko"
    assert korean_lecture.duration_seconds == 2746


def test_metrics_runner_counts_korean_and_english_fillers() -> None:
    assert run_preprocessing._count_fillers("음 어 um you know") == 4


@pytest.mark.asyncio
async def test_metrics_runner_uses_transcript_resolution_service() -> None:
    service = ResolvingTranscriptService()

    row = await run_preprocessing._measure_video(
        "youtube_en_4m35s_for_benchmark",
        "c4GaJKprGEs",
        "en",
        service,
        "detailed",
    )

    assert row["status"] == "success"
    assert row["transcript_provider"] == "fake-provider"
    assert row["raw_input_tokens"] > 0
    assert service.calls[0][1] == "en"
    assert service.calls[0][2] is False


@pytest.mark.asyncio
async def test_metrics_runner_uses_the_locked_korean_language() -> None:
    service = ResolvingTranscriptService()

    await run_preprocessing._measure_video(
        "youtube_ko_45m46s_for_benchmark",
        "YcA31dmSNMk",
        "ko",
        service,
        "detailed",
    )

    assert service.calls[0][1] == "ko"


@pytest.mark.asyncio
async def test_metrics_runner_records_stage_latencies_for_post_feature_validation() -> None:
    service = ResolvingTranscriptService()

    row = await run_preprocessing._measure_video(
        "youtube_en_4m35s_for_benchmark",
        "c4GaJKprGEs",
        "en",
        service,
        "detailed",
        preprocessing="current",
    )

    assert row["fetch_latency_seconds"] >= 0
    assert row["preprocessing_latency_seconds"] >= 0
    assert row["segmentation_latency_seconds"] >= 0
    assert row["total_latency_seconds"] >= row["fetch_latency_seconds"]
    stages = {stage["name"]: stage for stage in row["stages"]}
    assert "latency_seconds" in stages["raw_transcript"]
    assert "latency_seconds" in stages["processed_transcript"]
    assert "latency_seconds" in stages["segmentation"]


def test_report_and_quality_scripts_refuse_to_overwrite_artifacts(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    current_dir = tmp_path / "current"
    baseline_dir.mkdir()
    current_dir.mkdir()
    _write_metrics_fixture(baseline_dir, "baseline-1", 1000)
    _write_metrics_fixture(current_dir, "current-1", 900)
    quality_path = tmp_path / "quality.json"
    quality_path.write_text(
        json.dumps(
            {
                "videos": [
                    {
                        "key": "youtube_en_4m35s_for_benchmark",
                        "evidence_recall": 1.0,
                        "timestamp_accuracy": 1.0,
                        "unsupported_claims": 0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report_args = [
        sys.executable,
        "benchmarks/render_report.py",
        "--baseline",
        str(baseline_dir),
        "--current",
        str(current_dir),
    ]
    quality_args = [
        sys.executable,
        "benchmarks/evaluate_quality.py",
        "--quality",
        str(quality_path),
        "--current",
        str(current_dir),
    ]

    first_report = subprocess.run(report_args, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    second_report = subprocess.run(report_args, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    first_quality = subprocess.run(quality_args, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    second_quality = subprocess.run(quality_args, cwd=REPO_ROOT, check=False, capture_output=True, text=True)

    assert first_report.returncode == 0, first_report.stderr
    assert second_report.returncode != 0
    assert "already exists" in second_report.stderr
    assert first_quality.returncode == 0, first_quality.stderr
    assert second_quality.returncode != 0
    assert "already exists" in second_quality.stderr


def test_video_lock_rejects_duplicate_video_keys(tmp_path: Path) -> None:
    lock_path = tmp_path / "videos.lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "locked_at": "2026-08-21",
                "verification_method": "yt-dlp",
                "videos": [
                    {
                        "key": "youtube_en_4m35s_for_benchmark",
                        "youtube_id": "c4GaJKprGEs",
                        "title": "First",
                        "language": "en",
                        "duration_seconds": 275,
                    },
                    {
                        "key": "youtube_en_4m35s_for_benchmark",
                        "youtube_id": "ZIaOBAjvc38",
                        "title": "Second",
                        "language": "en",
                        "duration_seconds": 2340,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate video key"):
        load_video_lock(lock_path)


def test_video_lock_requires_a_language(tmp_path: Path) -> None:
    lock_path = tmp_path / "videos.lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "locked_at": "2026-08-24",
                "verification_method": "yt-dlp",
                "videos": [
                    {
                        "key": "youtube_ko_45m46s_for_benchmark",
                        "youtube_id": "YcA31dmSNMk",
                        "title": "Korean lecture",
                        "duration_seconds": 2746,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="language"):
        load_video_lock(lock_path)


def test_metrics_run_directory_is_immutable(tmp_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "run_id": "baseline-20260821T000000Z",
        "label": "baseline",
        "lock_file_sha256": "abc",
        "videos": [],
    }

    run_dir = write_metrics_run(tmp_path, "baseline-20260821T000000Z", payload)

    assert (run_dir / "metrics.json").is_file()
    with pytest.raises(FileExistsError):
        write_metrics_run(tmp_path, "baseline-20260821T000000Z", payload)


def test_comparison_requires_matching_lock_hash_and_successful_videos(tmp_path: Path) -> None:
    baseline = {
        "schema_version": 1,
        "run_id": "baseline-1",
        "label": "baseline",
        "lock_file_sha256": "same-lock",
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "status": "success",
                "substituted": False,
            }
        ],
    }
    current = {
        "schema_version": 1,
        "run_id": "current-1",
        "label": "current",
        "lock_file_sha256": "different-lock",
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "status": "failed",
                "substituted": False,
            }
        ],
    }

    eligibility = ComparisonEligibility.from_metrics(baseline, current)

    assert eligibility.eligible is False
    assert eligibility.reasons == (
        "lock_file_sha256 differs",
        "current video youtube_en_4m35s_for_benchmark status is failed",
    )


def test_quality_gate_fails_for_low_recall_and_unsupported_claims() -> None:
    result = evaluate_quality_gate(
        {
            "videos": [
                {
                    "key": "youtube_en_4m35s_for_benchmark",
                    "evidence_recall": 0.75,
                    "timestamp_accuracy": 0.95,
                    "unsupported_claims": 1,
                }
            ]
        },
        QualityFloor(evidence_recall=0.9, timestamp_accuracy=0.8, unsupported_claims=0),
    )

    assert result.passed is False
    assert result.failures == (
        "youtube_en_4m35s_for_benchmark evidence_recall 0.7500 below floor 0.9000",
        "youtube_en_4m35s_for_benchmark unsupported_claims 1 above floor 0",
    )


def test_report_data_calculates_token_reduction_from_saved_metrics(tmp_path: Path) -> None:
    baseline_dir = tmp_path / "baseline"
    current_dir = tmp_path / "current"
    baseline_dir.mkdir()
    current_dir.mkdir()
    (baseline_dir / "metrics.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "baseline-1",
                "label": "baseline",
                "lock_file_sha256": "same-lock",
                "videos": [
                    {
                        "key": "youtube_en_4m35s_for_benchmark",
                        "status": "success",
                        "substituted": False,
                        "raw_input_tokens": 1000,
                        "processed_input_tokens": 1000,
                        "preprocessing_latency_seconds": 1.5,
                        "segmentation_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (current_dir / "metrics.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "run_id": "current-1",
                "label": "current",
                "lock_file_sha256": "same-lock",
                "videos": [
                    {
                        "key": "youtube_en_4m35s_for_benchmark",
                        "status": "success",
                        "substituted": False,
                        "raw_input_tokens": 1000,
                        "processed_input_tokens": 700,
                        "preprocessing_latency_seconds": 1.2,
                        "segmentation_count": 2,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = build_report_data(load_metrics(baseline_dir), load_metrics(current_dir))

    assert report["eligible"] is True
    assert report["videos"] == [
        {
            "key": "youtube_en_4m35s_for_benchmark",
            "baseline_tokens": 1000,
            "current_tokens": 700,
            "token_delta": -300,
            "token_reduction_ratio": 0.3,
            "baseline_latency_seconds": 1.5,
            "current_latency_seconds": 1.2,
            "latency_delta_seconds": -0.3,
            "baseline_segmentation_count": 2,
            "current_segmentation_count": 2,
            "stages": [],
            "status": "success",
        }
    ]


def test_report_data_summarizes_totals_and_warns_when_candidate_has_no_measurable_effect() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    baseline["runtime_config"] = {"preprocessing": "none"}
    current = _metrics_payload("current-1", 1000, 1.0)
    current["runtime_config"] = {"preprocessing": "current"}
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 1.0,
                "timestamp_accuracy": 1.0,
                "unsupported_claims": 0,
            }
        ],
        "quality_gate": {"passed": True, "failures": []},
    }

    report = build_report_data(baseline, current, quality)

    assert report["summary"]["baseline_total_tokens"] == 1000
    assert report["summary"]["current_total_tokens"] == 1000
    assert report["summary"]["total_token_reduction_ratio"] == 0
    assert report["summary"]["candidate_effect_detected"] is False
    assert any("No measurable preprocessing effect" in risk for risk in report["risks"])
    assert report["decision"]["status"] == "revise"


def test_report_data_detects_per_video_effect_even_when_totals_cancel_out() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    current = _metrics_payload("current-1", 900, 1.0)
    baseline["videos"].append(
        {
            "key": "youtube_en_39m00s_for_benchmark",
            "status": "success",
            "substituted": False,
            "raw_input_tokens": 1000,
            "processed_input_tokens": 1000,
            "preprocessing_latency_seconds": 1.0,
            "segmentation_count": 1,
        }
    )
    current["videos"].append(
        {
            "key": "youtube_en_39m00s_for_benchmark",
            "status": "success",
            "substituted": False,
            "raw_input_tokens": 1000,
            "processed_input_tokens": 1100,
            "preprocessing_latency_seconds": 1.0,
            "segmentation_count": 1,
        }
    )

    report = build_report_data(baseline, current)

    assert report["summary"]["total_token_delta"] == 0
    assert report["summary"]["candidate_effect_detected"] is True
    assert not any("No measurable preprocessing effect" in risk for risk in report["risks"])


def test_report_data_marks_quality_failure_as_reject() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    current = _metrics_payload("current-1", 700, 1.1)
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 0.72,
                "timestamp_accuracy": 0.91,
                "unsupported_claims": 0,
            }
        ]
    }

    report = build_report_data(baseline, current, quality)

    assert report["decision"]["status"] == "reject"
    assert report["dimensions"][2]["name"] == "Quality"
    assert report["dimensions"][2]["status"] == "fail"
    assert any("Quality gate failed" in item for item in report["risks"])


def test_report_data_marks_speed_regression_as_revise_despite_token_win() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    current = _metrics_payload("current-1", 700, 1.45)
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 0.96,
                "timestamp_accuracy": 0.91,
                "unsupported_claims": 0,
            }
        ]
    }

    report = build_report_data(baseline, current, quality)
    markdown = render_report.render_markdown(report)

    assert report["decision"]["status"] == "revise"
    assert report["dimensions"][0]["status"] == "better"
    assert report["dimensions"][1]["status"] == "risk"
    assert "## Better / Risk" in markdown
    assert "Speed" in markdown


def test_decision_summary_does_not_claim_token_win_when_speed_regresses_without_cost_improvement() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    current = _metrics_payload("current-1", 1000, 1.3)
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 1.0,
                "timestamp_accuracy": 1.0,
                "unsupported_claims": 0,
            }
        ],
        "quality_gate": {"passed": True, "failures": []},
    }

    report = build_report_data(baseline, current, quality)

    assert report["decision"]["status"] == "revise"
    assert "Token cost improved" not in report["decision"]["summary"]


def test_report_data_uses_saved_quality_gate_decision() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    current = _metrics_payload("current-1", 700, 0.9)
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 0.96,
                "timestamp_accuracy": 0.91,
                "unsupported_claims": 0,
            }
        ],
        "quality_floor": {
            "evidence_recall": 0.99,
            "timestamp_accuracy": 0.95,
            "unsupported_claims": 0,
        },
        "quality_gate": {
            "passed": False,
            "failures": ["youtube_en_4m35s_for_benchmark evidence_recall 0.9600 below floor 0.9900"],
        },
    }

    report = build_report_data(baseline, current, quality)

    assert report["decision"]["status"] == "reject"
    assert report["quality_gate"] == {
        "passed": False,
        "failures": ["youtube_en_4m35s_for_benchmark evidence_recall 0.9600 below floor 0.9900"],
    }
    assert report["dimensions"][2]["status"] == "fail"


def test_report_data_rejects_quality_from_a_different_current_run() -> None:
    quality = {
        "current_run_id": "current-other",
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 1.0,
                "timestamp_accuracy": 1.0,
                "unsupported_claims": 0,
            }
        ],
        "quality_gate": {"passed": True, "failures": []},
    }

    report = build_report_data(
        _metrics_payload("baseline-1", 1000, 1.0),
        _metrics_payload("current-1", 800, 0.9),
        quality,
    )

    assert report["decision"]["status"] == "reject"
    assert any("Quality current_run_id current-other does not match current run current-1" in risk for risk in report["risks"])


def test_report_data_rejects_quality_with_missing_video_keys() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    current = _metrics_payload("current-1", 700, 0.9)
    baseline["videos"].append(
        {
            "key": "youtube_en_39m00s_for_benchmark",
            "status": "success",
            "substituted": False,
            "raw_input_tokens": 2000,
            "processed_input_tokens": 2000,
            "preprocessing_latency_seconds": 2.0,
            "segmentation_count": 2,
        }
    )
    current["videos"].append(
        {
            "key": "youtube_en_39m00s_for_benchmark",
            "status": "success",
            "substituted": False,
            "raw_input_tokens": 2000,
            "processed_input_tokens": 1600,
            "preprocessing_latency_seconds": 1.8,
            "segmentation_count": 2,
        }
    )
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 0.96,
                "timestamp_accuracy": 0.91,
                "unsupported_claims": 0,
            }
        ],
        "quality_gate": {"passed": True, "failures": []},
    }

    report = build_report_data(baseline, current, quality)

    assert report["decision"]["status"] == "reject"
    assert report["dimensions"][2]["status"] == "fail"
    assert any("Quality keys differ: missing youtube_en_39m00s_for_benchmark" in risk for risk in report["risks"])


def test_report_renders_previous_current_change_and_state_sections() -> None:
    baseline = _metrics_payload("baseline-1", 1000, 1.0)
    baseline["git_sha"] = "base-sha"
    baseline["lock_file_sha256"] = "same-lock"
    baseline["runtime_config"] = {"preprocessing": "none", "depth": "detailed", "llm_calls": 0}
    current = _metrics_payload("current-1", 700, 0.9)
    current["git_sha"] = "current-sha"
    current["lock_file_sha256"] = "same-lock"
    current["runtime_config"] = {"preprocessing": "mock-filler-filter", "depth": "detailed", "llm_calls": 0}
    quality = {
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "evidence_recall": 0.96,
                "timestamp_accuracy": 0.91,
                "unsupported_claims": 0,
            }
        ],
        "quality_gate": {"passed": True, "failures": []},
    }

    report = build_report_data(baseline, current, quality)
    markdown = render_report.render_markdown(report)
    html = render_report.render_html(report)

    assert report["change_summary"]["previous"]["label"] == "Previous pipeline"
    assert report["change_summary"]["current"]["label"] == "Current candidate"
    assert report["state"]["baseline_git_sha"] == "base-sha"
    assert "## Previous vs Current" in markdown
    assert "Raw transcript -> segmentation -> LLM-ready transcript" in markdown
    assert "## State and Evidence" in markdown
    assert "baseline-1" in markdown
    assert "Previous vs Current" in html
    assert "State and Evidence" in html
    assert "mock-filler-filter" in html
    assert "Stage Token Funnel" in html
    assert "Target release" in html
    assert "border-left" not in html


def test_metrics_payload_preserves_release_metadata_and_stage_counts(tmp_path: Path) -> None:
    lock_path = tmp_path / "videos.lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "locked_at": "2026-08-21",
                "verification_method": "fixture",
                "videos": [
                    {
                        "key": "youtube_en_4m35s_for_benchmark",
                        "youtube_id": "c4GaJKprGEs",
                        "title": "Locked title",
                        "language": "en",
                        "duration_seconds": 275,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    payload = {
        "schema_version": 1,
        "run_id": "current-1",
        "label": "current",
        "created_at": "2026-08-21T00:00:00+00:00",
        "git_sha": "candidate-sha",
        "lock_file": str(lock_path),
        "lock_file_sha256": "same-lock",
        "runtime_config": {"depth": "detailed", "llm_calls": 0, "preprocessing": "candidate"},
        "release": {
            "baseline_tag": "v0.1.0",
            "baseline_commit": "base-sha",
            "candidate_ref": "feat/preprocess",
            "candidate_commit": "candidate-sha",
            "target_release": "v0.2.0",
            "report_version": "benchmark-report/v1",
        },
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "youtube_id": "c4GaJKprGEs",
                "locked_title": "Locked title",
                "locked_duration_seconds": 275,
                "status": "success",
                "substituted": False,
                "raw_input_tokens": 1000,
                "processed_input_tokens": 700,
                "preprocessing_latency_seconds": 0.9,
                "segmentation_count": 1,
                "stages": [
                    {"name": "raw_transcript", "tokens": 1000, "characters": 4000},
                    {"name": "processed_transcript", "tokens": 700, "characters": 2800},
                    {"name": "segmentation", "topic_count": 1},
                ],
            }
        ],
    }

    report = build_report_data(_metrics_payload("baseline-1", 1000, 1.0), payload)

    assert report["state"]["baseline_tag"] == "v0.1.0"
    assert report["state"]["candidate_ref"] == "feat/preprocess"
    assert report["state"]["target_release"] == "v0.2.0"
    assert report["videos"][0]["stages"][1]["tokens"] == 700


def test_benchmark_report_command_runs_current_then_renders(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    baseline_dir = tmp_path / "baseline"
    current_root = tmp_path / "reports"
    baseline_dir.mkdir()
    _write_metrics_fixture(baseline_dir, "baseline-1", 1000)

    async def fake_run(
        label: str,
        lock_file: Path,
        output_root: Path,
        depth: str,
        *,
        concurrency: int = 1,
        release: dict[str, object] | None = None,
        preprocessing: str = "current",
    ) -> Path:
        run_dir = output_root / "current-1"
        run_dir.mkdir(parents=True)
        payload = _metrics_payload("current-1", 800, 0.8)
        payload["release"] = release or {}
        (run_dir / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")
        assert label == "current"
        assert concurrency == 5
        assert preprocessing == "candidate"
        return run_dir

    monkeypatch.setattr(benchmark_report.run_preprocessing, "run", fake_run)

    exit_code = benchmark_report.main(
        [
            "report",
            "--baseline-dir",
            str(baseline_dir),
            "--output-root",
            str(current_root),
            "--baseline-tag",
            "v0.1.0",
            "--candidate-ref",
            "feat/preprocess",
            "--target-release",
            "v0.2.0",
            "--preprocessing",
            "candidate",
            "--concurrency",
            "5",
        ]
    )

    assert exit_code == 0
    assert (current_root / "current-1" / "report.md").is_file()
    assert (current_root / "current-1" / "report.html").is_file()


def test_benchmark_shell_wrapper_documents_friendly_commands() -> None:
    result = subprocess.run(
        ["bash", "benchmarks/benchmark.sh", "--help"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "benchmark.sh baseline" in result.stdout
    assert "benchmark.sh run report" in result.stdout
    assert "benchmark.sh report allInOne" in result.stdout


def test_benchmark_shell_wrapper_report_all_in_one_builds_final_report_command(tmp_path: Path) -> None:
    reports_root = tmp_path / "reports"
    baseline_dir = reports_root / "baseline-123"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "metrics.json").write_text("{}", encoding="utf-8")

    env = {
        **os.environ,
        "BENCHMARK_DRY_RUN": "1",
        "BENCHMARK_REPORT_ROOT": str(reports_root),
    }

    result = subprocess.run(
        [
            "bash",
            "benchmarks/benchmark.sh",
            "report",
            "allInOne",
            "--baseline",
            "baseline-123",
            "--target-release",
            "v0.2.0",
        ],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "uv run --isolated --with tiktoken --with yt-dlp --with plotly" in result.stdout
    assert "python benchmarks/benchmark_report.py report" in result.stdout
    assert f"--baseline-dir {baseline_dir}" in result.stdout
    assert "--candidate-ref" in result.stdout
    assert "--candidate-commit" in result.stdout
    assert "--target-release v0.2.0" in result.stdout


def test_benchmark_shell_wrapper_report_all_in_one_resolves_baseline_from_custom_output_root(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "custom-reports"
    baseline_dir = output_root / "baseline-456"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "metrics.json").write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [
            "bash",
            "benchmarks/benchmark.sh",
            "report",
            "allInOne",
            "--output-root",
            str(output_root),
            "--baseline",
            "baseline-456",
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "BENCHMARK_DRY_RUN": "1"},
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert f"--baseline-dir {baseline_dir}" in result.stdout


def test_benchmark_shell_wrapper_report_all_in_one_reports_missing_option_value() -> None:
    result = subprocess.run(
        ["bash", "benchmarks/benchmark.sh", "report", "allInOne", "--baseline"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "Missing value for --baseline" in result.stderr


def _write_metrics_fixture(run_dir: Path, run_id: str, processed_tokens: int) -> None:
    (run_dir / "metrics.json").write_text(
        json.dumps(_metrics_payload(run_id, processed_tokens, 1.0)),
        encoding="utf-8",
    )


def _metrics_payload(run_id: str, processed_tokens: int, latency_seconds: float) -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "label": run_id.split("-", 1)[0],
        "lock_file_sha256": "same-lock",
        "videos": [
            {
                "key": "youtube_en_4m35s_for_benchmark",
                "status": "success",
                "substituted": False,
                "raw_input_tokens": 1000,
                "processed_input_tokens": processed_tokens,
                "preprocessing_latency_seconds": latency_seconds,
                "segmentation_count": 1,
            }
        ],
    }
