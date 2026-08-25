"""Render Markdown and Plotly HTML from saved benchmark metrics."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.benchmark_metrics import build_report_data, load_metrics, write_text_once

_BENCHMARK_VIDEO_KEY = re.compile(
    r"^youtube_(?P<language>en|ko)_(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+)s)?_for_benchmark$"
)
_DISPLAY_LANGUAGE = {"en": "English", "ko": "Korean"}


def display_video_label(key: str) -> str:
    """Return a compact report label while preserving unknown fixture keys."""
    match = _BENCHMARK_VIDEO_KEY.fullmatch(key)
    if match is None:
        return key

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    if hours:
        duration = f"{hours}h {minutes:02d}m"
    elif minutes:
        duration = f"{minutes}m {seconds:02d}s"
    elif seconds:
        duration = f"{seconds}s"
    else:
        return key
    return f"{_DISPLAY_LANGUAGE[match.group('language')]} · {duration}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--quality", type=Path)
    args = parser.parse_args()
    quality = json.loads(args.quality.read_text(encoding="utf-8")) if args.quality else None
    data = build_report_data(load_metrics(args.baseline), load_metrics(args.current), quality)
    markdown = render_markdown(data)
    output_dir = args.current
    write_text_once(output_dir / "report.md", markdown)
    write_text_once(output_dir / "report.html", render_html(data))
    print(output_dir / "report.md")


def render_markdown(data: dict[str, Any]) -> str:
    decision = data["decision"]
    lines = [
        "# Transcript Preprocessing Benchmark",
        "",
        "## Decision",
        "",
        f"- Status: `{decision['status']}`",
        f"- Summary: {decision['summary']}",
        "",
        "## Executive Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Baseline total tokens | {data['summary']['baseline_total_tokens']:,} |",
        f"| Current total tokens | {data['summary']['current_total_tokens']:,} |",
        f"| Token delta | {data['summary']['total_token_delta']:,} |",
        f"| Token reduction | {data['summary']['total_token_reduction_ratio']:.1%} |",
        f"| Latency delta | {data['summary']['total_latency_delta_seconds']:.3f}s |",
        f"| Candidate effect detected | `{data['summary']['candidate_effect_detected']}` |",
        "",
        "## Previous vs Current",
        "",
        f"### {data['change_summary']['previous']['label']}",
        "",
        f"- Mode: `{data['change_summary']['previous']['mode']}`",
        f"- Flow: {data['change_summary']['previous']['flow']}",
        f"- Summary: {data['change_summary']['previous']['summary']}",
        "",
        f"### {data['change_summary']['current']['label']}",
        "",
        f"- Mode: `{data['change_summary']['current']['mode']}`",
        f"- Flow: {data['change_summary']['current']['flow']}",
        f"- Summary: {data['change_summary']['current']['summary']}",
        "",
        "## Dimension Scorecard",
        "",
        "| Dimension | Status | Summary |",
        "|---|---|---|",
    ]
    for dimension in data["dimensions"]:
        lines.append(f"| {dimension['name']} | `{dimension['status']}` | {dimension['summary']} |")
    lines.extend(
        [
            "",
            "## Better / Risk",
            "",
            "### Better",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in data["better"]) if data["better"] else lines.append("- None recorded.")
    lines.extend(["", "### Risk", ""])
    lines.extend(f"- {item}" for item in data["risks"]) if data["risks"] else lines.append("- None recorded.")
    lines.extend(
        [
            "",
            "## State and Evidence",
            "",
            "| Field | Value |",
            "|---|---|",
            f"| Baseline run | `{data['state']['baseline_run_id']}` |",
            f"| Current run | `{data['state']['current_run_id']}` |",
            f"| Baseline git SHA | `{data['state']['baseline_git_sha']}` |",
            f"| Current git SHA | `{data['state']['current_git_sha']}` |",
            f"| Baseline lock hash | `{data['state']['baseline_lock_hash']}` |",
            f"| Current lock hash | `{data['state']['current_lock_hash']}` |",
            f"| Video count | `{data['state']['video_count']}` |",
            f"| Eligible comparison | `{data['state']['eligible']}` |",
            f"| Quality gate recorded | `{data['state']['quality_gate_recorded']}` |",
            "",
            "---",
            "",
            "## Question",
            "",
            "Does the candidate transcript preprocessing path reduce input cost or latency without violating quality gates?",
            "",
            "## Method",
            "",
            f"- Baseline run: `{data['baseline_run_id']}`",
            f"- Current run: `{data['current_run_id']}`",
            f"- Eligible comparison: `{data['eligible']}`",
        ]
    )
    for reason in data["eligibility_reasons"]:
        lines.append(f"- Ineligibility: {reason}")
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Video | Baseline tokens | Current tokens | Token delta | Reduction | Latency delta | Status |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in data["videos"]:
        lines.append(
            "| {key} | {baseline_tokens} | {current_tokens} | {token_delta} | {reduction:.1%} | {latency_delta:.3f}s | {status} |".format(
                key=display_video_label(row["key"]),
                baseline_tokens=row["baseline_tokens"],
                current_tokens=row["current_tokens"],
                token_delta=row["token_delta"],
                reduction=row["token_reduction_ratio"],
                latency_delta=row["latency_delta_seconds"],
                status=row["status"],
            )
        )
    quality_gate = data.get("quality_gate")
    lines.extend(["", "## Quality Gate", ""])
    if quality_gate is None:
        lines.append("Quality was not evaluated. Do not claim adoption from token reduction alone.")
    elif quality_gate["passed"]:
        lines.append("Quality gate passed. Review regressions before adopting.")
    else:
        lines.append("Quality gate failed. Revise before adopting.")
        for failure in quality_gate["failures"]:
            lines.append(f"- {failure}")
    return "\n".join(lines).rstrip() + "\n"


def render_html(data: dict[str, Any]) -> str:
    try:
        import plotly.graph_objects as go
        from plotly.offline import plot
    except ImportError:
        return _fallback_html(data)

    labels = [display_video_label(row["key"]) for row in data["videos"]]
    token_figure = go.Figure()
    token_figure.add_bar(name="Baseline tokens", x=labels, y=[row["baseline_tokens"] for row in data["videos"]])
    token_figure.add_bar(name="Current tokens", x=labels, y=[row["current_tokens"] for row in data["videos"]])
    token_figure.update_layout(
        title="Input tokens by video",
        barmode="group",
        yaxis={"title": "Input tokens"},
        template="plotly_white",
        height=360,
        margin={"l": 56, "r": 24, "t": 64, "b": 56},
    )
    stage_totals = _stage_token_totals(data)
    stage_figure = go.Figure()
    stage_figure.add_trace(
        go.Funnel(
            name="Current stage tokens",
            y=list(stage_totals),
            x=list(stage_totals.values()),
            marker={"color": ["#355c7d", "#4f7da5", "#79a7cf"]},
        )
    )
    stage_figure.update_layout(
        title="Stage Token Funnel",
        template="plotly_white",
        height=320,
        margin={"l": 56, "r": 24, "t": 64, "b": 40},
    )
    latency_figure = go.Figure()
    latency_figure.add_bar(
        name="Latency delta seconds",
        x=labels,
        y=[row["latency_delta_seconds"] for row in data["videos"]],
        marker={"color": ["#b45309" if row["latency_delta_seconds"] > 0 else "#047857" for row in data["videos"]]},
    )
    latency_figure.update_layout(
        title="Preprocessing latency delta",
        yaxis={"title": "Seconds vs baseline"},
        template="plotly_white",
        height=320,
        margin={"l": 56, "r": 24, "t": 64, "b": 56},
    )
    token_chart = plot(token_figure, output_type="div", include_plotlyjs=True)
    stage_chart = plot(stage_figure, output_type="div", include_plotlyjs=False)
    latency_chart = plot(latency_figure, output_type="div", include_plotlyjs=False)
    return _report_html(data, token_chart, latency_chart, stage_chart)


def _fallback_html(data: dict[str, Any]) -> str:
    presentation_data = {
        **data,
        "videos": [{**row, "key": display_video_label(row["key"])} for row in data["videos"]],
    }
    escaped = html.escape(json.dumps(presentation_data, ensure_ascii=False, indent=2))
    return _report_html(data, f"<pre>{escaped}</pre>", "", "<h3>Stage Token Funnel</h3>")


def _report_html(data: dict[str, Any], token_chart: str, latency_chart: str, stage_chart: str) -> str:
    decision = data["decision"]
    return f"""<!doctype html>
<meta charset="utf-8">
<title>Transcript Preprocessing Benchmark</title>
<style>
  :root {{
    color-scheme: light;
    --ink: #1f2933;
    --muted: #667085;
    --rule: #d8dee7;
    --paper: #f7f9fc;
    --panel: #ffffff;
    --good: #047857;
    --risk: #b45309;
    --bad: #b42318;
    --accent: #355c7d;
  }}
  body {{
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }}
  main {{
    max-width: 1180px;
    margin: 0 auto;
    padding: 40px 28px 56px;
  }}
  header {{
    border-bottom: 2px solid var(--ink);
    padding-bottom: 22px;
    margin-bottom: 28px;
  }}
  h1 {{
    margin: 0 0 10px;
    font-size: 34px;
    line-height: 1.05;
    letter-spacing: 0;
  }}
  h2 {{
    margin: 34px 0 14px;
    font-size: 18px;
    letter-spacing: 0;
  }}
  .decision {{
    display: grid;
    grid-template-columns: minmax(180px, 0.35fr) 1fr;
    gap: 18px;
    align-items: stretch;
  }}
  .verdict {{
    background: var(--ink);
    color: white;
    padding: 20px;
  }}
  .verdict span {{
    display: block;
    color: #c8d2df;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}
  .verdict strong {{
    display: block;
    margin-top: 10px;
    font-size: 34px;
    text-transform: uppercase;
    letter-spacing: 0;
  }}
  .summary {{
    padding: 10px 0 0;
    font-size: 18px;
    line-height: 1.45;
  }}
  .metric-strip {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    margin: 22px 0 4px;
  }}
  .metric {{
    background: linear-gradient(135deg, #ffffff 0%, #eef4fb 100%);
    border: 1px solid #dce7f3;
    border-radius: 14px;
    box-shadow: 0 10px 26px rgba(31, 41, 51, 0.07);
    padding: 14px;
  }}
  .metric span {{
    display: block;
    color: var(--muted);
    font-size: 12px;
  }}
  .metric strong {{
    display: block;
    margin-top: 6px;
    font-size: 20px;
  }}
  .scorecard {{
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
  }}
  .score {{
    background: var(--panel);
    border: 1px solid var(--rule);
    padding: 14px;
    min-height: 112px;
  }}
  .score .name {{
    font-weight: 700;
    margin-bottom: 8px;
  }}
  .status {{
    display: inline-block;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 700;
  }}
  .status.better, .status.pass, .status.adopt {{ color: var(--good); }}
  .status.risk, .status.revise, .status.not_evaluated, .status.neutral {{ color: var(--risk); }}
  .status.fail, .status.reject, .status.invalid, .status.worse {{ color: var(--bad); }}
  .score p, .summary p {{
    margin: 8px 0 0;
    color: var(--muted);
    line-height: 1.4;
  }}
  .tradeoffs {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .pipeline {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .tradeoffs section, .pipeline article {{
    background: var(--panel);
    border: 1px solid var(--rule);
    padding: 16px;
  }}
  .flow {{
    margin-top: 12px;
    padding: 10px;
    background: #eef3f8;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px;
    line-height: 1.45;
  }}
  ul {{
    margin: 10px 0 0;
    padding-left: 20px;
  }}
  li {{ margin: 7px 0; }}
  .charts {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .chart {{
    background: linear-gradient(135deg, #ffffff 0%, #f2f7fd 100%);
    border: 1px solid #dce7f3;
    border-radius: 16px;
    box-shadow: 0 14px 34px rgba(31, 41, 51, 0.08);
    padding: 10px;
    overflow: hidden;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: var(--panel);
    border: 1px solid var(--rule);
  }}
  th, td {{
    padding: 10px 12px;
    border-bottom: 1px solid var(--rule);
    text-align: right;
    font-size: 14px;
  }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{
    color: var(--muted);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}
  @media (max-width: 860px) {{
    main {{ padding: 24px 16px 40px; }}
    .decision, .scorecard, .tradeoffs, .pipeline, .charts, .metric-strip {{ grid-template-columns: 1fr; }}
  }}
</style>
<main>
  <header>
    <h1>Transcript Preprocessing Benchmark</h1>
    <div class="decision">
      <div class="verdict"><span>Decision</span><strong>{_escape(decision["status"])}</strong></div>
      <div class="summary"><p>{_escape(decision["summary"])}</p></div>
    </div>
    <section class="metric-strip">
      {_metric_card("Baseline tokens", f"{data["summary"]["baseline_total_tokens"]:,}")}
      {_metric_card("Current tokens", f"{data["summary"]["current_total_tokens"]:,}")}
      {_metric_card("Token reduction", f"{data["summary"]["total_token_reduction_ratio"]:.1%}")}
      {_metric_card("Latency delta", f"{data["summary"]["total_latency_delta_seconds"]:.3f}s")}
      {_metric_card("Effect detected", data["summary"]["candidate_effect_detected"])}
    </section>
  </header>
  <h2>Previous vs Current</h2>
  <section class="pipeline">
    {_pipeline_card(data["change_summary"]["previous"])}
    {_pipeline_card(data["change_summary"]["current"])}
  </section>
  <h2>Dimension Scorecard</h2>
  <section class="scorecard">
    {_dimension_cards(data["dimensions"])}
  </section>
  <h2>Better / Risk</h2>
  <section class="tradeoffs">
    <section><h3>Better</h3>{_list_html(data["better"])}</section>
    <section><h3>Risk</h3>{_list_html(data["risks"])}</section>
  </section>
  <h2>Per-Video Evidence</h2>
  <section class="charts">
    <div class="chart">{token_chart}</div>
    <div class="chart">{stage_chart}</div>
    <div class="chart">{latency_chart}</div>
  </section>
  <h2>Comparison Table</h2>
  {_video_table(data["videos"])}
  <h2>State and Evidence</h2>
  {_state_table(data["state"])}
</main>
"""


def _metric_card(label: str, value: object) -> str:
    return f"""<article class="metric">
  <span>{_escape(label)}</span>
  <strong>{_escape(value)}</strong>
</article>"""


def _dimension_cards(dimensions: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"""<article class="score">
  <div class="name">{_escape(item["name"])}</div>
  <div class="status {_escape(item["status"])}">{_escape(item["status"])}</div>
  <p>{_escape(item["summary"])}</p>
</article>"""
        for item in dimensions
    )


def _pipeline_card(item: dict[str, Any]) -> str:
    return f"""<article>
  <h3>{_escape(item["label"])}</h3>
  <div class="status neutral">{_escape(item["mode"])}</div>
  <div class="flow">{_escape(item["flow"])}</div>
  <p>{_escape(item["summary"])}</p>
</article>"""


def _list_html(items: list[str]) -> str:
    if not items:
        return "<p>None recorded.</p>"
    return "<ul>" + "".join(f"<li>{_escape(item)}</li>" for item in items) + "</ul>"


def _video_table(rows: list[dict[str, Any]]) -> str:
    body = "\n".join(
        "<tr>"
        f"<td>{_escape(display_video_label(row['key']))}</td>"
        f"<td>{row['baseline_tokens']:,}</td>"
        f"<td>{row['current_tokens']:,}</td>"
        f"<td>{row['token_delta']:,}</td>"
        f"<td>{row['token_reduction_ratio']:.1%}</td>"
        f"<td>{row['latency_delta_seconds']:.3f}s</td>"
        f"<td>{_escape(row['status'])}</td>"
        "</tr>"
        for row in rows
    )
    return f"""<table>
  <thead><tr><th>Video</th><th>Baseline tokens</th><th>Current tokens</th><th>Token delta</th><th>Reduction</th><th>Latency delta</th><th>Status</th></tr></thead>
  <tbody>{body}</tbody>
</table>"""


def _state_table(state: dict[str, Any]) -> str:
    rows = (
        ("Baseline run", state["baseline_run_id"]),
        ("Current run", state["current_run_id"]),
        ("Baseline tag", state["baseline_tag"]),
        ("Baseline commit", state["baseline_commit"]),
        ("Candidate ref", state["candidate_ref"]),
        ("Candidate commit", state["candidate_commit"]),
        ("Target release", state["target_release"]),
        ("Report version", state["report_version"]),
        ("Baseline git SHA", state["baseline_git_sha"]),
        ("Current git SHA", state["current_git_sha"]),
        ("Baseline lock hash", state["baseline_lock_hash"]),
        ("Current lock hash", state["current_lock_hash"]),
        ("Video count", state["video_count"]),
        ("Eligible comparison", state["eligible"]),
        ("Quality gate recorded", state["quality_gate_recorded"]),
    )
    body = "\n".join(f"<tr><td>{_escape(label)}</td><td>{_escape(value)}</td></tr>" for label, value in rows)
    return f"""<table>
  <thead><tr><th>State</th><th>Saved value</th></tr></thead>
  <tbody>{body}</tbody>
</table>"""


def _escape(value: object) -> str:
    return html.escape(str(value))


def _stage_token_totals(data: dict[str, Any]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in data["videos"]:
        for stage in row.get("stages", []):
            if not isinstance(stage, dict) or "tokens" not in stage:
                continue
            name = str(stage.get("name", "unknown"))
            totals[name] = totals.get(name, 0) + int(stage["tokens"])
    if not totals:
        return {"raw_transcript": 0, "processed_transcript": 0}
    return totals


if __name__ == "__main__":
    main()
