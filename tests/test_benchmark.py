from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from chew.benchmark import (
    BenchmarkCondition,
    BenchmarkObservation,
    BenchmarkReference,
    BenchmarkRunner,
    BenchmarkSpec,
    ReferenceClaim,
    _score_output,
)
from chew.cli import app


class Runner:
    def __init__(self, values: list[float]) -> None:
        self.values = values
        self.calls = 0

    async def __call__(self, _: str) -> BenchmarkObservation:
        value = self.values[self.calls]
        self.calls += 1
        return BenchmarkObservation(
            metrics={"coverage": value},
            latency_seconds=value * 2,
            usage=round(value * 10),
            unsupported_claims=1 if value < 0.5 else 0,
        )


@pytest.mark.asyncio
async def test_three_repeat_aggregation_and_anonymized_ordering() -> None:
    direct = Runner([0.2, 0.4, 0.6])
    hierarchical = Runner([0.7, 0.9, 0.8])
    report = await BenchmarkRunner().run(
        BenchmarkSpec(
            source_id="youtube:abc",
            conditions=(
                BenchmarkCondition("direct", "Gemini direct", "video_url", direct),
                BenchmarkCondition("kit", "Hierarchical", "transcript", hierarchical),
            ),
        )
    )
    assert direct.calls == hierarchical.calls == 3
    assert {result.code for result in report.results} == {"Condition A", "Condition B"}
    by_id = {result.condition_id: result for result in report.results}
    assert by_id["direct"].median_metrics["coverage"] == 0.4
    assert by_id["kit"].variance_metrics["coverage"] == pytest.approx(0.01)
    assert by_id["direct"].unsupported_claims == 1


@pytest.mark.asyncio
async def test_reports_preserve_input_modality_labels() -> None:
    report = await BenchmarkRunner().run(
        BenchmarkSpec(
            source_id="youtube:abc",
            repeats=1,
            conditions=(BenchmarkCondition("direct", "Direct", "video_url", Runner([1.0])),),
        )
    )
    markdown = report.to_markdown()
    payload = json.loads(report.to_json())
    assert "video_url" in markdown
    assert payload["results"][0]["input_method"] == "video_url"


def test_constructing_default_runner_makes_no_live_calls() -> None:
    runner = BenchmarkRunner()
    assert runner.live_calls == 0


def test_benchmark_catalog_command_is_offline() -> None:
    result = CliRunner().invoke(app, ["벤치마크", "목록", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert {item["input_method"] for item in data} == {"video_url", "transcript"}


def test_live_benchmark_requires_explicit_opt_in() -> None:
    result = CliRunner().invoke(app, ["벤치마크", "실행", "https://youtu.be/abcDEF_1234"])
    assert result.exit_code == 2
    assert "--live" in result.stdout


def test_reference_scoring_penalizes_hallucinations_and_wrong_timestamps() -> None:
    reference = BenchmarkReference(
        source_id="youtube:abc",
        language="ko",
        duration_ms=600_000,
        claims=(ReferenceClaim("큐로 병렬 처리한다", "챕터 작업을 큐에 넣는다", 120_000),),
    )
    metrics, unsupported = _score_output(
        {
            "overview": "요약",
            "key_points": [
                {
                    "text": "큐로 병렬 처리한다",
                    "evidence": "전혀 다른 근거",
                    "timestamp_ms": 500_000,
                },
                {
                    "text": "영상은 양자 컴퓨터를 판매한다",
                    "evidence": "없는 주장",
                    "timestamp_ms": 1,
                },
            ],
        },
        reference,
    )
    assert metrics["key_point_recall"] == 1
    assert metrics["evidence_coverage"] == 0
    assert metrics["timestamp_accuracy"] == 0
    assert unsupported == 1
