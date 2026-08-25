# Maintainer Benchmark Foundation Design

## Purpose

Create an internal, opt-in benchmark workflow that compares the transcript
preprocessing baseline with a candidate implementation on five locked YouTube
videos. It must produce reproducible evidence for engineering decisions and
publishable reports without adding benchmark, visualization, or MLflow
dependencies to the normal `chew` installation.

## Scope and non-goals

The workflow is for maintainers and CI only. End users continue to install and
run `chew` without knowing about benchmark tooling, MLflow, Jaeger, or report
generation. This phase does not add a user-facing benchmark command, a hosted
dashboard, a separate repository, or a Git submodule.

The first benchmark target is transcript preprocessing. The layout and result
schema must be reusable for future performance changes, but this work does not
implement the Phase 1 preprocessing pipeline itself.

## Chosen approach

Use a root-level `benchmarks/` directory for maintainer scripts and keep
runtime-only dependencies outside `pyproject.toml`:

```text
benchmarks/
├── README.md
├── videos.lock.json
├── run_preprocessing.py
├── evaluate_quality.py
├── render_report.py
└── benchmark_metrics.py

reports/
└── performance-comparisons/
    └── transcript-preprocessing/
        ├── README.md
        ├── latest.md
        └── <run-id>/
            ├── metrics.json
            ├── quality.json
            ├── report.md
            └── report.html
```

`benchmarks/videos.lock.json` becomes the canonical video fixture. It records
the five video IDs, verified durations, titles, and lock date. Existing roadmap
references point to this file rather than keeping a second independent video
list under `reports/`.

Maintainers invoke scripts using `uv run --isolated --with ...`; this creates no
project dependency or lockfile entry and its environment disappears after the
command. `uv` may retain download cache, which the scripts must never purge
automatically because that cache can be shared with unrelated projects.

### Why this approach

Keeping the scripts in `src/chew/benchmark/` would entangle a product runtime
module with optional maintainer-only tools. A new public `chew benchmark`
workflow would also make expensive, credentialed evaluation appear like an
end-user feature. A separate repository or submodule would make it harder to
test the exact candidate commit. The chosen layout keeps all code that changes
with this product in one repository while preserving a clean user install.

## Execution modes

### 1. Metrics-only baseline or candidate run

`run_preprocessing.py` downloads/fetches the locked transcript and measures
raw/processed characters, `tiktoken` token counts, filler count and ratio,
segmentation count, stage timings, transcript provider, failure/retry data,
Git SHA, runtime configuration, and the lock-file hash. It never calls an LLM.

```bash
uv run --isolated --with tiktoken --with yt-dlp \
  python benchmarks/run_preprocessing.py baseline

uv run --isolated --with tiktoken --with yt-dlp \
  python benchmarks/run_preprocessing.py current
```

Each execution writes a new immutable directory below
`reports/performance-comparisons/transcript-preprocessing/`. The script must
not overwrite a prior result.

### 2. Explicit quality evaluation

`evaluate_quality.py` is a separate, explicitly credentialed command. It reads
one baseline and one candidate metrics directory, runs the same five videos
with the requested existing `chew` runtime, and records end-to-end latency,
input/output usage where the runtime reports it, retries, evidence recall,
timestamp accuracy, and unsupported claims. It never runs as a side effect of
the metrics-only command.

```bash
uv run --isolated --with tiktoken --with yt-dlp \
  python benchmarks/evaluate_quality.py \
  --baseline <baseline-run-dir> --current <candidate-run-dir> --runtime codex
```

### 3. Report rendering

`render_report.py` consumes only saved JSON artifacts. It writes a Markdown
decision report and a standalone Plotly HTML report. Plotly is supplied only to
this rendering command through `uv run --isolated --with plotly`; it is not a
package dependency and is not used by the `chew` CLI.

```bash
uv run --isolated --with plotly \
  python benchmarks/render_report.py \
  --baseline <baseline-run-dir> --current <candidate-run-dir>
```

## Metrics and decision gates

The benchmark follows the common separation of cost, speed, quality, and
reproducibility. A candidate is not accepted solely because token count falls.

| Category | Metrics | Decision rule |
|---|---|---|
| Cost | raw/processed input tokens, output tokens when available, explicit estimated cost | Show reduction per video and aggregate; estimate cost only when a versioned price input is supplied. |
| Performance | preprocessing latency, segmentation count, full latency, retries/failures | Compare all five videos and median; flag any regression larger than the configured threshold. |
| Quality | evidence recall, timestamp accuracy, unsupported claims | Candidate must meet or exceed the defined quality floor before a cost win can be accepted. |
| Reliability | transcript provider, source availability, run status | Failed or substituted inputs invalidate direct comparison and are visibly marked. |
| Reproducibility | Git SHA, timestamp, runtime/model, concurrency, lock-file hash | Every report records these values; baseline and candidate must share the intended configuration. |

The initial quality floor uses the existing benchmark reference-claim concepts
instead of proxies such as average sentence length. If a reference fixture is
not available for a video, the report marks its quality comparison as not
evaluated rather than fabricating a score.

## Report and graph design

`report.md` is an engineering decision memo with this order:

1. **Question:** what cost, speed, or quality problem the baseline has.
2. **Change:** previous pipeline versus candidate pipeline, including enabled
   preprocessing stages.
3. **Method:** locked videos, exact configuration, run IDs, and limitations.
4. **Results:** per-video and aggregate evidence.
5. **Decision:** adopt, revise, or reject; list regressions and follow-up work.

`report.html` is a clean, report-oriented Plotly artifact rather than a
product dashboard. It contains:

- paired previous/current slope charts for input tokens and full latency across
  the five videos;
- grouped bars for token reduction and stage time by video;
- a quality gate table for evidence recall, timestamp accuracy, and unsupported
  claims;
- a visible status for each video so unavailable transcripts cannot be hidden by
  an aggregate average.

Graphs always render measured values. Before a real comparison exists, the
repository contains templates and schema documentation only, never mock values
presented as results.

## Publication flow

1. A maintainer runs the desired baseline/candidate comparison manually.
2. The generated artifacts are reviewed for matching lock hash, runtime,
   status, and quality gates.
3. The reviewed Markdown summary is promoted to `latest.md` and linked from
   `reports/BENCHMARK.md`; raw run artifacts remain run-specific evidence.
4. After merge to `master`, the existing Wiki synchronization workflow publishes
   the curated report or a dedicated Wiki page.
5. A Tech Blog post is written from the reviewed report: problem, change,
   measured outcome, limitations, and decision. It must link to the committed
   report and must not claim unmeasured improvement.

## Documentation and tests

`benchmarks/README.md` describes dependencies, credentials, data/cost warnings,
commands, output directories, and cleanup behavior. `IMPROVEMENTS.md` is
updated to point at the canonical lock file, scripts, and report location.
`reports/BENCHMARK.md` gains a link to the preprocessing comparison index.

Tests cover lock-file parsing, metric schema validation, comparison eligibility,
quality-gate behavior, and report-data construction without downloading videos
or calling LLMs. Live transcript/LLM work remains manual and opt-in.
