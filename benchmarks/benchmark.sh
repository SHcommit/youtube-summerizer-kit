#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Maintainer benchmark wrapper

Usage:
  benchmarks/benchmark.sh baseline [args...]
  benchmarks/benchmark.sh current [args...]
  benchmarks/benchmark.sh quality [args...]
  benchmarks/benchmark.sh render [args...]
  benchmarks/benchmark.sh report allInOne [--baseline <baseline-run-id-or-dir>]
  benchmarks/benchmark.sh run report [args...]

Examples:
  benchmarks/benchmark.sh baseline --preprocessing none --concurrency 5

  benchmarks/benchmark.sh report allInOne \
    --baseline baseline-20260821T010000Z \
    --target-release v0.2.0

  benchmarks/benchmark.sh run report \
    --baseline-dir reports/performance-comparisons/transcript-preprocessing/<baseline-run-id> \
    --baseline-tag v0.1.0 \
    --baseline-commit bad0e62 \
    --candidate-ref feat/transcript-preprocessing \
    --candidate-commit "$(git rev-parse HEAD)" \
    --target-release v0.2.0 \
    --preprocessing current \
    --concurrency 5

  benchmarks/benchmark.sh quality \
    --quality reviewed-quality.json \
    --current reports/performance-comparisons/transcript-preprocessing/<current-run-id>

  benchmarks/benchmark.sh render \
    --baseline reports/performance-comparisons/transcript-preprocessing/<baseline-run-id> \
    --current reports/performance-comparisons/transcript-preprocessing/<current-run-id> \
    --quality reports/performance-comparisons/transcript-preprocessing/<current-run-id>/quality.json
EOF
}

REPORT_ROOT="${BENCHMARK_REPORT_ROOT:-reports/performance-comparisons/transcript-preprocessing}"

run_cmd() {
  if [[ "${BENCHMARK_DRY_RUN:-0}" == "1" ]]; then
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi

  exec "$@"
}

current_ref() {
  git branch --show-current 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo "unknown"
}

current_commit() {
  git rev-parse HEAD 2>/dev/null || echo "unknown"
}

latest_baseline_dir() {
  local root="$1"
  local latest
  latest="$(find "$root" -maxdepth 1 -type d -name 'baseline-*' 2>/dev/null | sort | tail -n 1)"
  if [[ -z "$latest" || ! -f "$latest/metrics.json" ]]; then
    echo "No baseline metrics found under $root. Pass --baseline <run-id-or-dir>." >&2
    exit 2
  fi

  echo "$latest"
}

resolve_baseline_dir() {
  local value="${1:-}"
  local root="$2"
  local candidate

  if [[ -z "$value" ]]; then
    latest_baseline_dir "$root"
    return
  fi

  if [[ -d "$value" ]]; then
    candidate="$value"
  else
    candidate="$root/$value"
  fi

  if [[ ! -f "$candidate/metrics.json" ]]; then
    echo "Baseline metrics not found: $candidate/metrics.json" >&2
    exit 2
  fi

  echo "$candidate"
}

require_value() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" || "$value" == --* ]]; then
    echo "Missing value for $option" >&2
    exit 2
  fi
}

if [[ $# -eq 0 || "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi

command="$1"
shift

case "$command" in
  baseline)
    run_cmd uv run --isolated --with tiktoken --with yt-dlp \
      python benchmarks/run_preprocessing.py baseline "$@"
    ;;
  current)
    run_cmd uv run --isolated --with tiktoken --with yt-dlp \
      python benchmarks/run_preprocessing.py current "$@"
    ;;
  quality)
    run_cmd uv run --isolated \
      python benchmarks/evaluate_quality.py "$@"
    ;;
  render)
    run_cmd uv run --isolated --with plotly \
      python benchmarks/render_report.py "$@"
    ;;
  report)
    mode="${1:-}"
    if [[ "$mode" != "allInOne" ]]; then
      echo "Unknown report mode: ${mode:-<empty>}" >&2
      usage >&2
      exit 2
    fi
    shift

    baseline=""
    baseline_tag="unknown"
    baseline_commit="unknown"
    candidate_ref="$(current_ref)"
    candidate_commit="$(current_commit)"
    target_release="unknown"
    quality=""
    preprocessing="current"
    concurrency="5"
    depth="detailed"
    lock_file="benchmarks/videos.lock.json"
    output_root="$REPORT_ROOT"

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --baseline|--baseline-dir)
          require_value "$1" "${2:-}"
          baseline="$2"
          shift 2
          ;;
        --baseline-tag)
          require_value "$1" "${2:-}"
          baseline_tag="$2"
          shift 2
          ;;
        --baseline-commit)
          require_value "$1" "${2:-}"
          baseline_commit="$2"
          shift 2
          ;;
        --candidate-ref)
          require_value "$1" "${2:-}"
          candidate_ref="$2"
          shift 2
          ;;
        --candidate-commit)
          require_value "$1" "${2:-}"
          candidate_commit="$2"
          shift 2
          ;;
        --target-release)
          require_value "$1" "${2:-}"
          target_release="$2"
          shift 2
          ;;
        --quality)
          require_value "$1" "${2:-}"
          quality="$2"
          shift 2
          ;;
        --preprocessing)
          require_value "$1" "${2:-}"
          preprocessing="$2"
          shift 2
          ;;
        --concurrency)
          require_value "$1" "${2:-}"
          concurrency="$2"
          shift 2
          ;;
        --depth)
          require_value "$1" "${2:-}"
          depth="$2"
          shift 2
          ;;
        --lock-file)
          require_value "$1" "${2:-}"
          lock_file="$2"
          shift 2
          ;;
        --output-root)
          require_value "$1" "${2:-}"
          output_root="$2"
          shift 2
          ;;
        *)
          echo "Unknown report allInOne option: $1" >&2
          usage >&2
          exit 2
          ;;
      esac
    done

    baseline_dir="$(resolve_baseline_dir "$baseline" "$output_root")"
    report_command=(
      uv run --isolated --with tiktoken --with yt-dlp --with plotly
      python benchmarks/benchmark_report.py report
      --baseline-dir "$baseline_dir"
      --lock-file "$lock_file"
      --output-root "$output_root"
      --depth "$depth"
      --concurrency "$concurrency"
      --preprocessing "$preprocessing"
      --baseline-tag "$baseline_tag"
      --baseline-commit "$baseline_commit"
      --candidate-ref "$candidate_ref"
      --candidate-commit "$candidate_commit"
      --target-release "$target_release"
    )
    if [[ -n "$quality" ]]; then
      report_command+=(--quality "$quality")
    fi

    run_cmd "${report_command[@]}"
    ;;
  run)
    subcommand="${1:-}"
    if [[ "$subcommand" != "report" ]]; then
      echo "Unknown run subcommand: ${subcommand:-<empty>}" >&2
      usage >&2
      exit 2
    fi
    shift
    run_cmd uv run --isolated --with tiktoken --with yt-dlp --with plotly \
      python benchmarks/benchmark_report.py report "$@"
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage >&2
    exit 2
    ;;
esac
