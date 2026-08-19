"""OpenTelemetry-compliant performance tracing and interactive HTML UI dashboard generator."""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import Status, StatusCode

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False


@dataclass
class SpanRecord:
    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "OK"

    def finish(self) -> None:
        if self.end_time == 0.0:
            self.end_time = time.time()
        self.duration_ms = max(0.0, (self.end_time - self.start_time) * 1000)


class TelemetryManager:
    """Manages OpenTelemetry tracing and local span collection for UI dashboard rendering."""

    def __init__(self) -> None:
        self.spans: list[SpanRecord] = []
        self._active_spans: list[SpanRecord] = []
        self.tracer = None

        if HAS_OPENTELEMETRY:
            resource = Resource.create({"service.name": "chew-pipeline"})
            provider = TracerProvider(resource=resource)
            endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
            if endpoint:
                try:
                    otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
                    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                except Exception:
                    pass
            trace.set_tracer_provider(provider)
            self.tracer = trace.get_tracer("chew.telemetry")

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any] | None = None) -> Generator[SpanRecord, None, None]:
        start_time = time.time()
        record = SpanRecord(name=name, start_time=start_time, attributes=attributes or {})
        self._active_spans.append(record)

        otel_span = None
        if self.tracer is not None:
            otel_span = self.tracer.start_span(name)
            if attributes:
                for k, v in attributes.items():
                    otel_span.set_attribute(k, str(v))

        try:
            yield record
        except Exception as exc:
            record.status = "ERROR"
            record.attributes["error"] = str(exc)
            if otel_span is not None:
                otel_span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        finally:
            record.finish()
            if record in self._active_spans:
                self._active_spans.remove(record)
            self.spans.append(record)
            if otel_span is not None:
                otel_span.end()

    def export_markdown_report(self, output_path: Path | str = "reports/trace_report.md") -> Path:
        """Generates a structured Markdown trace report based on recorded spans."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "# YouTube Summarizer Kit (`chew`) Performance & Trace Execution Report",
            "",
            *self._build_summary_metrics(),
            "",
            *self._build_span_table(),
            "",
            "## 3. OpenTelemetry Jaeger Integration",
            "",
            "- Open http://localhost:16686 to view real-time OpenTelemetry trace graphs in Jaeger UI.",
            "",
        ]

        target.write_text("\n".join(lines), encoding="utf-8")
        return target

    def _build_summary_metrics(self) -> list[str]:
        total_duration = max((s.duration_ms for s in self.spans), default=0.0) / 1000.0
        error_count = sum(1 for s in self.spans if s.status == "ERROR")

        return [
            "## 1. Summary Metrics",
            "",
            f"- **Total Runtime**: {total_duration:.2f} seconds",
            f"- **Recorded Spans**: {len(self.spans)} spans",
            f"- **Error Spans**: {error_count}",
        ]

    def _build_span_table(self) -> list[str]:
        lines = [
            "## 2. OpenTelemetry Span Execution Table",
            "",
            "| Span Name | Duration (ms) | Relative Start | Status | Attributes |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]

        if not self.spans:
            lines.append("| (No spans recorded in this run) | - | - | - | - |")
            return lines

        min_start = min(s.start_time for s in self.spans)
        for s in self.spans:
            rel_start = (s.start_time - min_start) * 1000.0
            attr_str = ", ".join(f"{k}: {v}" for k, v in s.attributes.items()) if s.attributes else "-"
            lines.append(f"| `{s.name}` | {s.duration_ms:.1f} ms | +{rel_start:.1f} ms | {s.status} | {attr_str} |")
        return lines


# Global singleton instance for easy import across chew
telemetry = TelemetryManager()
