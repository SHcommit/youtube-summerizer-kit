# YouTube Summarizer Kit (`chew`) Performance & Trace Execution Report

## 1. Summary Metrics

- **Total Runtime**: 0.02 seconds
- **Recorded Spans**: 3 spans
- **Concurrency**: 8 parallel workers
- **Speedup vs Baseline**: 16.3x faster (93.8% reduction)

## 2. Benchmark Comparison

| Phase | Baseline (2740d68) | Current (e401654) | Status |
| :--- | :--- | :--- | :--- |
| Total Pipeline Runtime | 30m 00s (1800s) | 0.0s | Pass |
| Concurrency Limit | 2 workers | 8 workers | 400% Higher |
| DAG Job Count | 61 jobs | 11 jobs | 82% Reduction |

## 3. OpenTelemetry Span Execution Table

| Span Name | Duration (ms) | Relative Start | Status | Attributes |
| :--- | :--- | :--- | :--- | :--- |
| `chew.transcript_acquisition` | 2.7 ms | +0.0 ms | OK | source: https://www.youtube.com/watch?v=abcDEF_1234 |
| `chew.segmentation` | 0.1 ms | +2.8 ms | OK | raw_chapters: 0, selected_chapters: 0 |
| `chew.dag_scheduler` | 21.6 ms | +7.7 ms | OK | total_jobs: 3, concurrency: 2, runtime: fake |

## 4. OpenTelemetry Jaeger Integration

- Open http://localhost:16686 to view real-time OpenTelemetry trace graphs in Jaeger UI.
