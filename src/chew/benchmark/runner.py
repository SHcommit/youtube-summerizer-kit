"""Repeatable, provider-neutral benchmark aggregation and reports."""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import tempfile
from asyncio import Lock
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path
from time import monotonic
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class BenchmarkObservation:
    metrics: dict[str, float]
    latency_seconds: float
    usage: int
    unsupported_claims: int
    metadata: dict[str, str] = field(default_factory=dict)


ConditionRunner = Callable[[str], Awaitable[BenchmarkObservation]]


@dataclass(frozen=True, slots=True)
class ReferenceClaim:
    text: str
    evidence: str
    timestamp_ms: int
    tolerance_ms: int = 30_000

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("reference claim text must be non-empty")
        if not isinstance(self.evidence, str) or not self.evidence.strip():
            raise ValueError("reference claim evidence must be non-empty")
        if isinstance(self.timestamp_ms, bool) or not isinstance(self.timestamp_ms, int) or self.timestamp_ms < 0:
            raise ValueError("reference claim timestamp_ms must be a non-negative integer")
        if isinstance(self.tolerance_ms, bool) or not isinstance(self.tolerance_ms, int) or self.tolerance_ms <= 0:
            raise ValueError("reference claim tolerance_ms must be a positive integer")


@dataclass(frozen=True, slots=True)
class BenchmarkReference:
    source_id: str
    language: str
    duration_ms: int
    claims: tuple[ReferenceClaim, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("reference source_id must be non-empty")
        if not isinstance(self.language, str) or not self.language.strip():
            raise ValueError("reference language must be non-empty")
        if isinstance(self.duration_ms, bool) or not isinstance(self.duration_ms, int) or self.duration_ms <= 0:
            raise ValueError("reference duration_ms must be a positive integer")
        if not self.claims:
            raise ValueError("reference requires at least one claim")
        if any(claim.timestamp_ms > self.duration_ms for claim in self.claims):
            raise ValueError("reference claim timestamp_ms must be within the reference duration")

    @classmethod
    def from_json(cls, value: str) -> BenchmarkReference:
        payload = json.loads(value)
        if not isinstance(payload, dict):
            raise ValueError("benchmark reference must be a JSON object")
        claims = payload.get("claims")
        if not isinstance(claims, list):
            raise ValueError("reference claims must be a list")
        source_id = payload.get("source_id")
        language = payload.get("language")
        duration_ms = payload.get("duration_ms")
        if not isinstance(source_id, str) or not isinstance(language, str):
            raise ValueError("reference source_id and language must be strings")
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, int):
            raise ValueError("reference duration_ms must be an integer")
        try:
            parsed_claims = tuple(ReferenceClaim(**claim) for claim in claims if isinstance(claim, dict))
        except TypeError as error:
            raise ValueError("reference claims must contain text, evidence, and timestamp_ms") from error
        if len(parsed_claims) != len(claims):
            raise ValueError("reference claims must be objects")
        return cls(
            source_id=source_id,
            language=language,
            duration_ms=duration_ms,
            claims=parsed_claims,
        )


@dataclass(frozen=True, slots=True)
class BenchmarkCondition:
    condition_id: str
    label: str
    input_method: str
    runner: ConditionRunner
    live: bool = False


@dataclass(frozen=True, slots=True)
class BenchmarkSpec:
    source_id: str
    conditions: tuple[BenchmarkCondition, ...]
    repeats: int = 3


@dataclass(frozen=True, slots=True)
class ConditionResult:
    code: str
    condition_id: str
    label: str
    input_method: str
    repeats: int
    median_metrics: dict[str, float]
    variance_metrics: dict[str, float]
    median_latency_seconds: float
    median_usage: float
    unsupported_claims: int
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    source_id: str
    results: tuple[ConditionResult, ...]
    generated_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [f"# Benchmark: {self.source_id}", ""]
        for result in self.results:
            lines.extend(
                (
                    f"## {result.code}",
                    "",
                    f"- Input method: `{result.input_method}`",
                    f"- Repeats: {result.repeats}",
                    f"- Median latency: {result.median_latency_seconds:.3f}s",
                    f"- Median usage: {result.median_usage:g}",
                    f"- Unsupported claims: {result.unsupported_claims}",
                    "",
                    "| Metric | Median | Variance |",
                    "|---|---:|---:|",
                )
            )
            for metric in sorted(result.median_metrics):
                lines.append(
                    f"| {metric} | {result.median_metrics[metric]:.4f} | {result.variance_metrics[metric]:.4f} |"
                )
            lines.append("")
            for key, value in sorted(result.metadata.items()):
                lines.append(f"- {key}: `{value}`")
            if result.metadata:
                lines.append("")
        lines.extend(("## Reveal", ""))
        lines.extend(f"- {result.code}: {result.label}" for result in self.results)
        return "\n".join(lines).rstrip() + "\n"


def write_benchmark_report(report: BenchmarkReport, output: Path) -> tuple[Path, Path]:
    """Atomically write a report into its own collision-resistant directory."""

    run_directory = output / f"run-{uuid4().hex[:12]}"
    run_directory.mkdir(parents=True, exist_ok=False)
    paths = (run_directory / "report.json", run_directory / "report.md")
    for path, content in zip(paths, (report.to_json(), report.to_markdown()), strict=True):
        descriptor, temporary = tempfile.mkstemp(dir=run_directory, prefix=".report-")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return paths


class BenchmarkRunner:
    def __init__(self) -> None:
        self.live_calls = 0

    async def run(self, spec: BenchmarkSpec) -> BenchmarkReport:
        if spec.repeats < 1:
            raise ValueError("benchmark repeats must be positive")
        ordered = sorted(
            spec.conditions,
            key=lambda condition: hashlib.sha256(f"{spec.source_id}:{condition.condition_id}".encode()).digest(),
        )
        results: list[ConditionResult] = []
        for index, condition in enumerate(ordered):
            observations = [await self._observe(condition, spec.source_id) for _ in range(spec.repeats)]
            metric_names = sorted(set().union(*(observation.metrics.keys() for observation in observations)))
            medians: dict[str, float] = {}
            variances: dict[str, float] = {}
            for metric in metric_names:
                values = [observation.metrics[metric] for observation in observations]
                medians[metric] = float(statistics.median(values))
                variances[metric] = float(statistics.variance(values)) if len(values) > 1 else 0.0
            results.append(
                ConditionResult(
                    code=f"Condition {chr(ord('A') + index)}",
                    condition_id=condition.condition_id,
                    label=condition.label,
                    input_method=condition.input_method,
                    repeats=spec.repeats,
                    median_metrics=medians,
                    variance_metrics=variances,
                    median_latency_seconds=float(statistics.median(item.latency_seconds for item in observations)),
                    median_usage=float(statistics.median(item.usage for item in observations)),
                    unsupported_claims=round(statistics.median(item.unsupported_claims for item in observations)),
                    metadata=observations[-1].metadata,
                )
            )
        return BenchmarkReport(spec.source_id, tuple(results), datetime.now(UTC).isoformat())

    async def _observe(self, condition: BenchmarkCondition, source_id: str) -> BenchmarkObservation:
        if condition.live:
            self.live_calls += 1
        return await condition.runner(source_id)


def benchmark_catalog() -> list[dict[str, str]]:
    """Describe fair conditions without starting any authenticated process."""

    return [
        {
            "id": "gemini-direct-simple",
            "label": "Gemini direct URL / simple prompt",
            "input_method": "video_url",
        },
        {
            "id": "gemini-direct-schema",
            "label": "Gemini direct URL / matched schema",
            "input_method": "video_url",
        },
        {
            "id": "kit-gemini",
            "label": "Hierarchical pipeline / Gemini",
            "input_method": "transcript",
        },
        {
            "id": "kit-configured",
            "label": "Hierarchical pipeline / configured runtime",
            "input_method": "transcript",
        },
    ]


_COMMON_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "key_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "timestamp_ms": {"type": "integer"},
                    "evidence": {"type": "string"},
                },
                "required": ["text", "timestamp_ms", "evidence"],
                "additionalProperties": False,
            },
        },
        "further_study": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["overview", "key_points", "further_study"],
    "additionalProperties": False,
}


def _similarity(left: object, right: object) -> float:
    normalized_left = " ".join(str(left).casefold().split())
    normalized_right = " ".join(str(right).casefold().split())
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _score_output(output: dict[str, object], reference: BenchmarkReference) -> tuple[dict[str, float], int]:
    key_points = output.get("key_points")
    points = [point for point in key_points if isinstance(point, dict)] if isinstance(key_points, list) else []
    matches: list[tuple[ReferenceClaim, dict[str, object]]] = []
    unmatched = list(points)
    for claim in reference.claims:
        candidates = sorted(
            unmatched,
            key=lambda point: _similarity(point.get("text"), claim.text),
            reverse=True,
        )
        if candidates and _similarity(candidates[0].get("text"), claim.text) >= 0.55:
            point = candidates[0]
            matches.append((claim, point))
            unmatched.remove(point)
    expected = max(1, len(reference.claims))
    evidence_matches = sum(_similarity(point.get("evidence"), claim.evidence) >= 0.45 for claim, point in matches)
    timestamp_matches = 0
    for claim, point in matches:
        timestamp = point.get("timestamp_ms")
        if isinstance(timestamp, int) and abs(timestamp - claim.timestamp_ms) <= claim.tolerance_ms:
            timestamp_matches += 1
    covered_quarters = {min(3, claim.timestamp_ms * 4 // max(1, reference.duration_ms)) for claim, _ in matches}
    metrics = {
        "key_point_recall": len(matches) / expected,
        "evidence_coverage": evidence_matches / expected,
        "timestamp_accuracy": timestamp_matches / expected,
        "long_video_coverage": len(covered_quarters) / 4,
        "structure": 1.0 if isinstance(output.get("overview"), str) and points else 0.0,
    }
    return metrics, len(unmatched)


def live_benchmark_spec(
    url: str,
    *,
    reference: BenchmarkReference,
    repeats: int = 3,
    configured_runtime: str = "codex",
) -> BenchmarkSpec:
    """Build four explicit opt-in conditions; no process starts until the spec is run."""

    from chew.core.identity import normalize_youtube_url
    from chew.core.models import GenerationRequest
    from chew.core.prompts import PROMPT_FINGERPRINT
    from chew.harness.builtin import request_prompt
    from chew.harness.gemini import GeminiHarness
    from chew.harness.registry import default_registry
    from chew.pipeline.engine import AnalysisConfig, AnalysisPipeline
    from chew.storage.artifacts import ArtifactStore
    from chew.storage.database import Database
    from chew.transcripts import TranscriptService, default_providers

    source = normalize_youtube_url(url)
    if reference.source_id != source.source_id:
        raise ValueError("benchmark reference source_id does not match URL")
    gemini = GeminiHarness()

    def direct(mode: str) -> ConditionRunner:
        async def observe(_: str) -> BenchmarkObservation:
            started = monotonic()
            request_id = str(uuid4())
            if mode == "simple":
                prompt = (
                    "Analyze this YouTube video and return a JSON object with overview, "
                    "key_points (text, timestamp_ms, evidence), and further_study: " + url
                )
                result = await gemini.generate_prompt(
                    prompt,
                    request_id=request_id,
                )
                prompt_payload = prompt
            else:
                request = GenerationRequest(
                    request_id=request_id,
                    task="benchmark_direct_video",
                    input={"youtube_url": url, "prompt_mode": mode},
                    output_schema=_COMMON_SCHEMA,
                    trace_id=str(uuid4()),
                )
                result = await gemini.generate(request)
                prompt_payload = request_prompt(request)
            metrics, unsupported = _score_output(result.output, reference)
            return BenchmarkObservation(
                metrics,
                monotonic() - started,
                sum(result.usage.values()),
                unsupported,
                {
                    "runtime": result.runtime_id,
                    "model": result.model or "default",
                    "prompt_fingerprint": hashlib.sha256(prompt_payload.encode()).hexdigest(),
                },
            )

        return observe

    def hierarchical(runtime_id: str) -> ConditionRunner:
        lock = Lock()

        async def observe(_: str) -> BenchmarkObservation:
            async with lock:
                selected = await default_registry().select(runtime_id)
            capabilities = (await selected.probe()).capabilities
            started = monotonic()
            with tempfile.TemporaryDirectory(prefix="chew-benchmark-") as temporary:
                root = Path(temporary)
                database = Database(root / "state.sqlite3")
                database.initialize()
                pipeline = AnalysisPipeline(
                    database=database,
                    artifacts=ArtifactStore(root),
                    transcripts=TranscriptService(default_providers()),
                    harness=selected,
                    concurrency=capabilities.max_concurrency,
                )
                result = await pipeline.analyze(url, AnalysisConfig(language=reference.language, depth="detailed", instructions="", whisper_fallback=False, runtime=runtime_id, recipe_json="{}"))
            points = [
                {
                    "text": claim.text,
                    "timestamp_ms": claim.evidence[0].start_ms if claim.evidence else 0,
                    "evidence": claim.evidence[0].text if claim.evidence else "",
                }
                for topic in result.pack.topics
                for claim in topic.claims
            ]
            output: dict[str, object] = {
                "overview": result.pack.overview,
                "key_points": points,
                "further_study": list(result.pack.further_study),
            }
            metrics, unsupported = _score_output(output, reference)
            return BenchmarkObservation(
                metrics,
                monotonic() - started,
                sum((result.usage or {}).values()),
                unsupported,
                {
                    "runtime": selected.runtime_id,
                    "model": ",".join(result.models) or "default",
                    "prompt_fingerprint": PROMPT_FINGERPRINT,
                },
            )

        return observe

    return BenchmarkSpec(
        source_id=source.source_id,
        repeats=repeats,
        conditions=(
            BenchmarkCondition(
                "gemini-direct-simple",
                "Gemini direct / simple",
                "video_url",
                direct("simple"),
                True,
            ),
            BenchmarkCondition(
                "gemini-direct-schema",
                "Gemini direct / schema",
                "video_url",
                direct("schema"),
                True,
            ),
            BenchmarkCondition("kit-gemini", "Hierarchical / Gemini", "transcript", hierarchical("gemini"), True),
            BenchmarkCondition(
                "kit-configured",
                "Hierarchical / configured",
                "transcript",
                hierarchical(configured_runtime),
                True,
            ),
        ),
    )


async def short_video_benchmark_spec(
    url: str,
    *,
    reference: BenchmarkReference,
    repeats: int = 3,
    configured_runtime: str = "codex",
) -> BenchmarkSpec:
    """Compare one-pass and hierarchical synthesis with the same transcript and Frontier runtime."""

    from chew.core.identity import normalize_youtube_url
    from chew.core.models import GenerationRequest
    from chew.core.prompts import PROMPT_FINGERPRINT
    from chew.harness.base import Harness
    from chew.harness.builtin import request_prompt
    from chew.harness.registry import default_registry
    from chew.pipeline.engine import AnalysisConfig, AnalysisPipeline
    from chew.storage.artifacts import ArtifactStore
    from chew.storage.database import Database
    from chew.transcripts import TranscriptService, default_providers

    source = normalize_youtube_url(url)
    if reference.source_id != source.source_id:
        raise ValueError("benchmark reference source_id does not match URL")
    transcript = (
        await TranscriptService(default_providers()).resolve(
            source,
            reference.language,
            include_optional=False,
        )
    ).transcript
    registry = default_registry()
    runtime_lock = Lock()

    async def selected_runtime() -> Harness:
        async with runtime_lock:
            return await registry.select(configured_runtime)

    def single_pass() -> ConditionRunner:
        async def observe(_: str) -> BenchmarkObservation:
            selected = await selected_runtime()
            request = GenerationRequest(
                request_id=str(uuid4()),
                task="benchmark_single_pass_transcript",
                input={
                    "title": transcript.title or "YouTube video",
                    "language": reference.language,
                    "segments": [segment.model_dump(mode="json") for segment in transcript.segments],
                    "instruction": (
                        "Produce a concise evidence-grounded summary. Return key points with exact "
                        "timestamps and transcript quotes."
                    ),
                },
                output_schema=_COMMON_SCHEMA,
                trace_id=str(uuid4()),
            )
            started = monotonic()
            result = await selected.generate(request)
            metrics, unsupported = _score_output(result.output, reference)
            return BenchmarkObservation(
                metrics,
                monotonic() - started,
                sum(result.usage.values()),
                unsupported,
                {
                    "runtime": result.runtime_id,
                    "model": result.model or "default",
                    "prompt_fingerprint": hashlib.sha256(request_prompt(request).encode()).hexdigest(),
                    "comparison": "same_frontier_transcript",
                },
            )

        return observe

    def hierarchical() -> ConditionRunner:
        async def observe(_: str) -> BenchmarkObservation:
            selected = await selected_runtime()
            capabilities = (await selected.probe()).capabilities
            started = monotonic()
            with tempfile.TemporaryDirectory(prefix="chew-short-video-benchmark-") as temporary:
                root = Path(temporary)
                database = Database(root / "state.sqlite3")
                database.initialize()
                pipeline = AnalysisPipeline(
                    database=database,
                    artifacts=ArtifactStore(root),
                    transcripts=TranscriptService(default_providers()),
                    harness=selected,
                    concurrency=capabilities.max_concurrency,
                )
                result = await pipeline.analyze(
                    url,
                    AnalysisConfig(
                        language=reference.language,
                        depth="detailed",
                        instructions="",
                        whisper_fallback=False,
                        runtime=configured_runtime,
                        recipe_json="{}",
                    ),
                    transcript=transcript,
                )
            points = [
                {
                    "text": claim.text,
                    "timestamp_ms": claim.evidence[0].start_ms if claim.evidence else 0,
                    "evidence": claim.evidence[0].text if claim.evidence else "",
                }
                for topic in result.pack.topics
                for claim in topic.claims
            ]
            metrics, unsupported = _score_output(
                {
                    "overview": result.pack.overview,
                    "key_points": points,
                    "further_study": list(result.pack.further_study),
                },
                reference,
            )
            return BenchmarkObservation(
                metrics,
                monotonic() - started,
                sum((result.usage or {}).values()),
                unsupported,
                {
                    "runtime": selected.runtime_id,
                    "model": ",".join(result.models) or "default",
                    "prompt_fingerprint": PROMPT_FINGERPRINT,
                    "comparison": "same_frontier_transcript",
                },
            )

        return observe

    return BenchmarkSpec(
        source_id=source.source_id,
        repeats=repeats,
        conditions=(
            BenchmarkCondition(
                "frontier-single-pass",
                "Single-pass / configured Frontier",
                "transcript",
                single_pass(),
                True,
            ),
            BenchmarkCondition(
                "frontier-hierarchical",
                "Hierarchical / configured Frontier",
                "transcript",
                hierarchical(),
                True,
            ),
        ),
    )
