# YouTube Summarizer Kit (`chew`) Performance & Trace Execution Report

## 1. Summary Metrics

- **Total Runtime**: 0.01 seconds
- **Recorded Spans**: 3 spans
- **Error Spans**: 0

## 2. OpenTelemetry Span Execution Table

| Span Name | Duration (ms) | Relative Start | Status | Attributes |
| :--- | :--- | :--- | :--- | :--- |
| `chew.transcript_acquisition` | 1.7 ms | +0.0 ms | OK | source: https://www.youtube.com/watch?v=abcDEF_1234 |
| `chew.segmentation` | 0.1 ms | +1.8 ms | OK | raw_chapters: 0, selected_chapters: 0, depth: detailed |
| `chew.dag_scheduler` | 13.7 ms | +4.8 ms | OK | total_jobs: 3, concurrency: 2, runtime: fake |

## 3. OpenTelemetry Jaeger Integration

- Open http://localhost:16686 to view real-time OpenTelemetry trace graphs in Jaeger UI.
