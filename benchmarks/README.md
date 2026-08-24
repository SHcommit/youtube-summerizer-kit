# Maintainer Benchmark Commands

This directory contains internal benchmark tools for transcript preprocessing
experiments. They are opt-in maintainer scripts, not normal `chew` user
commands, and they do not add benchmark-only dependencies to `pyproject.toml`.

Use these tools after a candidate feature has been implemented to answer one
narrow question:

> Does a candidate transcript preprocessing change reduce input cost without
> breaking quality, reliability, reproducibility, or acceptable runtime?

Do not publish mock values. Only promote reviewed real artifacts to
`reports/performance-comparisons/transcript-preprocessing/latest.md`.

## Files

| File | Purpose |
|---|---|
| `videos.lock.json` | Canonical locked benchmark-video catalog |
| `benchmark.sh` | Friendly shell wrapper around the long `uv run --isolated --with ...` commands |
| `run_preprocessing.py` | Metrics-only baseline/current run; no LLM calls |
| `benchmark_report.py` | One-command current run + report rendering |
| `evaluate_quality.py` | Attach reviewed quality-gate results |
| `render_report.py` | Render `report.md` and `report.html` from saved JSON |
| `benchmark_metrics.py` | Shared parsing, validation, comparison, and decision logic |

Reports are written under:

```text
reports/performance-comparisons/transcript-preprocessing/<run-id>/
```

Each run directory is immutable. If a target artifact already exists, the
command fails instead of overwriting it.

## Locked Videos

The canonical catalog is `benchmarks/videos.lock.json`. It contains five
verified English videos from about five minutes to just under three hours and
two verified Korean fixtures (lecture and conversational). Each entry declares
the caption language the runner requests; a catalog-wide language override is
deliberately not used.

Unavailable transcripts must remain visible as failed entries in `metrics.json`.
Do not silently substitute another video or transcript source.

## Quality Reference Review

Live Frontier comparisons require a separate, human-reviewed JSON reference for
the exact normalized YouTube URL. The project deliberately ships no completed
reference answers and never generates them from an LLM. A reviewer must inspect
the source transcript and record at least one independently supported claim:

- `source_id`, `language`, and positive `duration_ms`
- non-empty `claims` entries with `text`, transcript `evidence`, and
  `timestamp_ms`
- a positive `tolerance_ms` when the default 30 seconds is unsuitable

The parser rejects empty claims, blank text or evidence, invalid numeric values,
and timestamps outside the reference duration before a `--live` run can create
a provider call. This validates the review artifact's structure, not the truth
of its content; the reviewer remains responsible for that judgment.

AI-assisted candidates for the current locked videos live in
`reference-drafts/`. They are Markdown review queues, deliberately separate
from executable JSON references, and remain unusable for a live benchmark until
a human reviewer approves and transcribes them.

## Recommended Workflow

### 1. Capture the baseline first

Run this before implementing the candidate preprocessing behavior, or from a
checked-out baseline commit/tag.

```bash
benchmarks/benchmark.sh baseline \
  --preprocessing none \
  --concurrency 5
```

Output:

```text
reports/performance-comparisons/transcript-preprocessing/baseline-<timestamp>/metrics.json
```

Keep this directory. Future candidate reports compare against it.

### 2. Run current candidate and render the report

Once the candidate implementation exists, use the one-command report flow:

```bash
benchmarks/benchmark.sh report allInOne \
  --baseline <baseline-run-id> \
  --target-release v0.2.0
```

This runs all locked videos with bounded concurrency, writes a new current
`metrics.json`, then renders:

```text
report.md
report.html
```

The command records release/tag metadata, locked video metadata, aggregate
summary values, and shallow stage metrics:

- `raw_transcript`: characters, tokens, segment count
- `processed_transcript`: characters, tokens, segment count
- `segmentation`: topic count, chapter count

It does not call an LLM.

The benchmark does not implement transcript preprocessing itself. For
post-feature validation, `--preprocessing current` uses the product hook
`chew.pipeline.preprocessing.preprocess_transcript(transcript, mode=...)` when
that module exists. If the feature has not been implemented or the hook is not
enabled, the report should show no measurable effect and surface a warning.

The final report highlights:

- total baseline/current input tokens and reduction ratio
- per-video token and latency deltas
- stage token funnel for the current candidate path
- quality/reliability/reproducibility gates
- a warning when `--preprocessing current` shows no measurable token or
  segmentation effect, which usually means the candidate path was not enabled

If `--baseline` is omitted, the wrapper uses the latest `baseline-*` directory
under `reports/performance-comparisons/transcript-preprocessing/`.

Use explicit release metadata when preparing a release comparison:

```bash
benchmarks/benchmark.sh report allInOne \
  --baseline baseline-20260821T010000Z \
  --baseline-tag v0.1.0 \
  --baseline-commit bad0e62 \
  --candidate-ref feat/transcript-preprocessing \
  --candidate-commit "$(git rev-parse HEAD)" \
  --target-release v0.2.0 \
  --preprocessing current \
  --concurrency 5
```

### 3. Attach quality results when available

Quality evaluation is explicit and separate from metrics collection. Use this
shape for reviewed quality data:

```json
{
  "videos": [
    {
      "key": "youtube_en_4m35s_for_benchmark",
      "evidence_recall": 0.95,
      "timestamp_accuracy": 0.9,
      "unsupported_claims": 0
    }
  ]
}
```

Attach it to a candidate run:

```bash
benchmarks/benchmark.sh quality \
  --quality reviewed-quality.json \
  --current reports/performance-comparisons/transcript-preprocessing/<current-run-id>
```

Then render the report with quality included:

```bash
benchmarks/benchmark.sh render \
  --baseline reports/performance-comparisons/transcript-preprocessing/<baseline-run-id> \
  --current reports/performance-comparisons/transcript-preprocessing/<current-run-id> \
  --quality reports/performance-comparisons/transcript-preprocessing/<current-run-id>/quality.json
```

Quality keys must match the compared video keys. A missing or unrelated quality
entry rejects the quality dimension so the final decision cannot falsely adopt.
Saved `quality.json` also records `current_run_id`; if it does not match the
current metrics run, the report rejects the quality gate.

## Command Reference

### `benchmark.sh`

Friendly wrapper for the maintainer workflow. Prefer this unless you need to
debug the underlying Python command.

```bash
benchmarks/benchmark.sh --help
benchmarks/benchmark.sh baseline --preprocessing none --concurrency 5
benchmarks/benchmark.sh current --preprocessing current --concurrency 5
benchmarks/benchmark.sh report allInOne --baseline <baseline-run-id>
benchmarks/benchmark.sh run report --baseline-dir <baseline-run-dir>
benchmarks/benchmark.sh quality --quality reviewed-quality.json --current <current-run-dir>
benchmarks/benchmark.sh render --baseline <baseline-run-dir> --current <current-run-dir>
```

The wrapper expands to the required `uv run --isolated --with ...` commands.
Prefer `report allInOne` for normal report generation; `run report` remains as
the lower-level pass-through command.

### `run_preprocessing.py`

Metrics-only transcript run.

```bash
uv run --isolated --with tiktoken --with yt-dlp \
  python benchmarks/run_preprocessing.py baseline \
  --lock-file benchmarks/videos.lock.json \
  --output-root reports/performance-comparisons/transcript-preprocessing \
  --depth detailed \
  --preprocessing none \
  --concurrency 5
```

Arguments:

| Argument | Meaning |
|---|---|
| `baseline` / `current` | Run label used in the run id |
| `--lock-file` | Locked video fixture |
| `--output-root` | Parent directory for immutable run directories |
| `--depth` | Segmentation depth passed to the pipeline |
| `--preprocessing` | Measured preprocessing path label; `none` is baseline, `current` is the post-feature candidate hook |
| `--concurrency` | Number of locked videos measured concurrently |

### `benchmark_report.py report`

Runs a current metrics pass and renders the comparison report.

```bash
uv run --isolated --with tiktoken --with yt-dlp --with plotly \
  python benchmarks/benchmark_report.py report \
  --baseline-dir <baseline-run-dir> \
  --baseline-tag v0.1.0 \
  --baseline-commit bad0e62 \
  --candidate-ref feat/transcript-preprocessing \
  --candidate-commit "$(git rev-parse HEAD)" \
  --target-release v0.2.0 \
  --preprocessing current \
  --concurrency 5
```

Optional:

```bash
  --quality reports/performance-comparisons/transcript-preprocessing/<current-run-id>/quality.json
```

### `evaluate_quality.py`

Validates and stores reviewed quality data.

```bash
uv run --isolated \
  python benchmarks/evaluate_quality.py \
  --quality reviewed-quality.json \
  --current <current-run-dir> \
  --evidence-recall 0.9 \
  --timestamp-accuracy 0.8 \
  --unsupported-claims 0
```

Exit code is `0` when the gate passes and `1` when it fails. In both cases the
validated `quality.json` is written unless the file already exists.

### `render_report.py`

Renders reports from saved JSON only.

```bash
uv run --isolated --with plotly \
  python benchmarks/render_report.py \
  --baseline <baseline-run-dir> \
  --current <current-run-dir> \
  --quality <current-run-dir>/quality.json
```

Outputs:

- `report.md`: GitHub/Wiki-friendly decision report
- `report.html`: visual report with scorecard and graphs

## Decision Rules

The rendered report uses these rules:

- Lock hash mismatch or failed/substituted videos make the comparison invalid.
- Quality failure rejects the candidate.
- Missing quality for any compared video rejects the quality dimension.
- Token reduction alone never adopts a candidate.
- Speed regression is marked as a revise risk.
- Adoption requires cost improvement plus passing quality, reliability, and
  reproducibility gates.

## What Gets Stored

`metrics.json` preserves:

- run id, timestamp, git SHA
- release/tag metadata
- lock-file path and hash
- runtime/preprocessing label
- locked video title and duration
- transcript provider and status
- raw/processed character and token counts
- fetch/preprocessing/segmentation/total latency values
- filler count and ratio
- segmentation count
- shallow stage metrics and stage-level latency values

`quality.json` preserves:

- current run id
- reviewed per-video quality values
- quality floor
- saved quality gate result

`report.md` and `report.html` are generated from saved evidence only.
The HTML report includes an executive metric strip, dimension scorecard,
stage token funnel, per-video graphs, and saved state/release metadata.

## Publication

Before promoting a report:

- Confirm baseline/current lock hashes match.
- Confirm every locked video succeeded.
- Confirm no substitutions occurred.
- Confirm quality covers every compared video.
- Confirm the report is based on real artifacts, not mock data.
- Copy the reviewed conclusion into `latest.md`.

Do not commit generated mock run directories.
