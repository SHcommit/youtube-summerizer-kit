# Handoff — Phase 1 Benchmark Baseline and Preprocessing

## Current state

- Working branch: `feat/agentic-layered-harness`
- Integration target: `develop`
- This branch contains the completed Steps 1–9 improvements plus the
  maintainer benchmark foundation design:
  `docs/superpowers/specs/2026-08-21-maintainer-benchmark-foundation-design.md`
- The benchmark foundation is designed but not implemented. No real baseline
  result has been recorded yet.

## Immediate decision

**Do not implement Phase 1 preprocessing before preserving the current
baseline.** The current behavior is the control group. If it is changed first,
we cannot credibly calculate cost, speed, or quality improvement later.

The required sequence is:

```text
1. Lock benchmark inputs and run current implementation (baseline)
2. Preserve immutable raw results and the human-readable baseline report
3. Implement the selected IMPROVEMENTS.md Phase 1 stages
4. Run the identical locked inputs and configuration (candidate)
5. Compare baseline vs candidate; run explicit LLM quality evaluation if needed
6. Make an adoption decision, then publish reviewed results
```

## Benchmark scope

The first comparison uses these verified English videos:

| Key | YouTube ID | Duration |
|---|---|---:|
| `5m_en` | `c4GaJKprGEs` | 4m 35s |
| `39m_en` | `ZIaOBAjvc38` | 39m |
| `1h_en` | `XDB5beon4DY` | 55m 48s |
| `2h_en` | `RcYjXbSJBN8` | 2h 00m 09s |
| `2h50m_en` | `BYXbuik3dgA` | 2h 49m 45s |

The final canonical fixture will live in `benchmarks/videos.lock.json`.

## Implementation direction

Implement only maintainer-facing tools; do not add MLflow, Plotly, benchmark
packages, or benchmark UI to the normal `chew` dependency set or user workflow.

```text
benchmarks/
├── README.md
├── videos.lock.json
├── run_preprocessing.py       # local metrics, never calls an LLM
├── evaluate_quality.py        # explicit, credentialed LLM quality check
├── render_report.py           # Markdown + Plotly HTML from saved results
└── benchmark_metrics.py

reports/performance-comparisons/transcript-preprocessing/
├── README.md
├── latest.md                  # reviewed, publishable summary
└── <run-id>/                  # immutable JSON, Markdown, HTML, artifacts
```

Use `uv run --isolated --with ...` for benchmark-only dependencies. This keeps
the normal package install clean. `uv` download cache must not be purged by a
script because it may be shared by other local projects.

## What to measure

| Area | Measurements to preserve |
|---|---|
| Cost | raw/processed input tokens, output tokens where available, optional versioned cost estimate |
| Speed | preprocessing latency, segmentation count, end-to-end time, retries/failures |
| Quality | evidence recall, timestamp accuracy, unsupported claims |
| Reliability | transcript provider, availability, run status, substitutions |
| Reproducibility | Git SHA, model/runtime, concurrency, lock-file hash, timestamp |

Token reduction alone is not an adoption criterion. The candidate must meet the
quality floor and must not hide unavailable or substituted transcript inputs.

## Report, Wiki, and Tech Blog flow

1. `metrics.json` is the immutable evidence for a run.
2. `report.md` and Plotly `report.html` compare previous/current values by
   video with paired slope charts, grouped bars, and a quality-gate table.
3. A maintainer reviews matching configuration, status, and quality gates.
4. The reviewed conclusion is promoted to `latest.md` and linked from
   `reports/BENCHMARK.md`.
5. The existing Wiki sync workflow publishes the curated report after merge to
   `master`.
6. A Tech Blog post is written from the reviewed report, including the problem,
   implementation, measured outcome, limitations, and adoption decision.

Never publish mock values or claim improvement before the baseline and
candidate runs exist.

## Handoff checklist

- [ ] Merge the committed feature branch into `develop` after confirming the
      intended commit range.
- [ ] Implement the maintainer benchmark foundation from the approved design.
- [ ] Execute and preserve the baseline before modifying Phase 1 behavior.
- [ ] Implement Phase 1 preprocessing according to `IMPROVEMENTS.md`.
- [ ] Execute candidate and optional LLM quality evaluation with the same lock
      file and configuration.
- [ ] Review comparison, update `reports/BENCHMARK.md`, Wiki, changelog, and
      Tech Blog only after measured evidence supports the conclusion.

## Existing uncommitted worktree changes

This handoff intentionally does not absorb unrelated or uncommitted changes.
Before merging or continuing implementation, inspect and separately decide on
the current modifications to `IMPROVEMENTS.md`, `reports/trace_report.md`,
`reports/benchmark-videos.lock.json`, and local `.superpowers/` artifacts.
