from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chew.benchmark import (
    BenchmarkCondition,
    BenchmarkObservation,
    BenchmarkProgress,
    BenchmarkReference,
    BenchmarkReport,
    BenchmarkRunner,
    BenchmarkSpec,
    ReferenceClaim,
    _score_output,
    short_video_benchmark_spec,
)
from chew.cli import app
from chew.core.models import (
    GenerationRequest,
    GenerationResult,
    Provenance,
    SourceIdentity,
    Transcript,
    TranscriptSegment,
)
from chew.harness.base import HarnessCapabilities, HarnessProbe
from chew.transcripts.service import TranscriptResolution

cli_main = import_module("chew.cli.main")


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


@pytest.mark.asyncio
async def test_runner_reports_progress_before_each_repeat() -> None:
    events: list[BenchmarkProgress] = []
    await BenchmarkRunner(progress_callback=events.append).run(
        BenchmarkSpec(
            source_id="youtube:abc",
            repeats=2,
            conditions=(BenchmarkCondition("direct", "Direct", "video_url", Runner([0.2, 0.4])),),
        )
    )

    assert [(event.condition_id, event.repeat, event.total_repeats) for event in events] == [
        ("direct", 1, 2),
        ("direct", 2, 2),
    ]


def test_constructing_default_runner_makes_no_live_calls() -> None:
    runner = BenchmarkRunner()
    assert runner.live_calls == 0


def test_benchmark_catalog_command_is_offline() -> None:
    result = CliRunner().invoke(app, ["벤치마크", "목록", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)["data"]
    assert {item["input_method"] for item in data} == {"video_url", "transcript"}


def test_live_benchmark_requires_explicit_opt_in() -> None:
    result = CliRunner().invoke(
        app,
        ["벤치마크", "실행", "https://youtu.be/abcDEF_1234", "--short-video"],
    )
    assert result.exit_code == 2
    assert "--live" in result.stdout


@pytest.mark.parametrize(
    ("payload", "message"),
    (
        (
            {
                "source_id": "youtube:abcDEF_1234",
                "language": "ko",
                "duration_ms": 60_000,
                "claims": [],
            },
            "at least one claim",
        ),
        (
            {
                "source_id": "youtube:abcDEF_1234",
                "language": "ko",
                "duration_ms": 60_000,
                "claims": [{"text": "claim", "evidence": "quote", "timestamp_ms": 60_001}],
            },
            "within the reference duration",
        ),
        (
            {
                "source_id": "youtube:abcDEF_1234",
                "language": "ko",
                "duration_ms": 60_000,
                "claims": [{"text": " ", "evidence": "quote", "timestamp_ms": 10_000}],
            },
            "text must be non-empty",
        ),
    ),
)
def test_reference_rejects_invalid_review_data(payload: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        BenchmarkReference.from_json(json.dumps(payload))


def test_live_benchmark_rejects_invalid_reference_before_a_live_call(tmp_path: Path) -> None:
    reference = tmp_path / "invalid-reference.json"
    reference.write_text(
        json.dumps(
            {
                "source_id": "youtube:abcDEF_1234",
                "language": "ko",
                "duration_ms": 60_000,
                "claims": [],
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "run",
            "https://youtu.be/abcDEF_1234",
            "--live",
            "--reference",
            str(reference),
        ],
    )

    assert result.exit_code == 2
    assert "Invalid benchmark reference" in result.stdout


def test_live_benchmark_prints_repeat_progress_before_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps(
            {
                "source_id": "youtube:abcDEF_1234",
                "language": "en",
                "duration_ms": 60_000,
                "claims": [{"text": "claim", "evidence": "quote", "timestamp_ms": 10_000}],
            }
        ),
        encoding="utf-8",
    )

    async def fake_spec(*_: object, **__: object) -> BenchmarkSpec:
        return BenchmarkSpec("youtube:abcDEF_1234", ())

    class FakeRunner:
        def __init__(self, progress_callback: object = None) -> None:
            self.progress_callback = progress_callback

        async def run(self, _: BenchmarkSpec) -> BenchmarkReport:
            assert callable(self.progress_callback)
            self.progress_callback(BenchmarkProgress("frontier-single-pass", 1, 1))
            return BenchmarkReport("youtube:abcDEF_1234", (), "2026-08-25T00:00:00+00:00")

    monkeypatch.setattr(cli_main, "short_video_benchmark_spec", fake_spec)
    monkeypatch.setattr(cli_main, "BenchmarkRunner", FakeRunner)
    monkeypatch.setattr(cli_main, "write_benchmark_report", lambda *_: (tmp_path / "report.json", tmp_path / "report.md"))

    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "run",
            "https://youtu.be/abcDEF_1234",
            "--live",
            "--short-video",
            "--reference",
            str(reference),
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.index("Running frontier-single-pass repeat 1/1") < result.stdout.index("report.md")


@pytest.mark.asyncio
async def test_short_video_benchmark_resolves_one_snapshot_for_all_conditions_and_repeats(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = BenchmarkReference(
        source_id="youtube:abcDEF_1234",
        language="en",
        duration_ms=275_000,
        claims=(ReferenceClaim("claim", "evidence", 10_000),),
    )

    source = SourceIdentity(
        source_id=reference.source_id,
        video_id="abcDEF_1234",
        canonical_url="https://www.youtube.com/watch?v=abcDEF_1234",
    )
    transcript = Transcript(
        source=source,
        language="en",
        duration_ms=275_000,
        provenance=Provenance.AUTO_SUBTITLE,
        segments=(TranscriptSegment(start_ms=0, end_ms=275_000, text="shared snapshot evidence"),),
    )

    class RecordingTranscriptService:
        calls = 0

        def __init__(self, providers: object) -> None:
            del providers

        async def resolve(
            self, source: SourceIdentity, language: str, *, include_optional: bool = False
        ) -> TranscriptResolution:
            type(self).calls += 1
            assert source == transcript.source
            assert language == transcript.language
            assert include_optional is False
            return TranscriptResolution(transcript, "fixture", ())

    class FakeHarness:
        runtime_id = "codex"

        async def probe(self) -> HarnessProbe:
            return HarnessProbe(
                runtime_id="codex",
                available=True,
                auth_ready=True,
                version="fixture",
                capabilities=HarnessCapabilities(max_concurrency=1),
                detail=None,
            )

        async def generate(self, request: GenerationRequest) -> GenerationResult:
            if request.task == "knowledge_extract":
                output: dict[str, object] = {
                    "thesis_claim_id": "claim-1",
                    "claims": [{"claim_id": "claim-1", "text": "topic", "occurrence_ids": ["occ-1"]}],
                    "occurrences": [
                        {
                            "occurrence_id": "occ-1",
                            "raw_segment_indexes": [0],
                            "quote": "shared snapshot evidence",
                        }
                    ],
                }
            elif request.task == "topic_summary":
                output: dict[str, object] = {
                    "topic_id": request.input["topic_id"],
                    "title": request.input["title"],
                    "summary": "topic",
                    "claims": [],
                    "concepts": [],
                    "examples": [],
                }
            elif request.task == "chapter_summary":
                output = {
                    "chapter_id": request.input["chapter_id"],
                    "title": request.input["title"],
                    "summary": "chapter",
                    "topic_ids": request.input["topic_ids"],
                }
            else:
                output = {"overview": "overview", "further_study": []}
            return GenerationResult(request_id=request.request_id, output=output, runtime_id="codex")

    class FakeRegistry:
        async def select(self, runtime_id: str) -> FakeHarness:
            assert runtime_id == "codex"
            return FakeHarness()

    monkeypatch.setattr("chew.transcripts.TranscriptService", RecordingTranscriptService)
    monkeypatch.setattr("chew.transcripts.default_providers", lambda: ())
    monkeypatch.setattr("chew.harness.registry.default_registry", FakeRegistry)

    spec = await short_video_benchmark_spec(
        "https://www.youtube.com/watch?v=abcDEF_1234",
        reference=reference,
        repeats=2,
        configured_runtime="codex",
    )
    report = await BenchmarkRunner().run(spec)

    assert RecordingTranscriptService.calls == 1
    assert spec.repeats == 2
    assert [(condition.condition_id, condition.input_method) for condition in spec.conditions] == [
        ("frontier-single-pass", "transcript"),
        ("frontier-hierarchical", "transcript"),
        ("gkt-deterministic", "transcript"),
    ]
    gkt = next(result for result in report.results if result.condition_id == "gkt-deterministic")
    assert gkt.median_metrics["frontier_call_count"] == 1
    assert gkt.median_metrics["grounding_coverage"] == 1
    assert gkt.median_metrics["ambiguous_anchor_count"] == 0


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
