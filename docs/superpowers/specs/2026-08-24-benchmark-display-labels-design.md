# Benchmark Display Labels Design

## Goal

Make benchmark reports readable by replacing internal fixture keys in human-facing tables and Plotly axes with language-and-duration labels.

## Scope

- Preserve every fixture `key` unchanged in lock files, metrics, quality references, and comparison logic.
- Derive a display label from the existing key format: `youtube_<language>_<duration>_for_benchmark`.
- Render English labels as `English · 2h 00m`, Korean labels as `Korean · 45m 46s`; omit zero-value hours or minutes.
- Use the label in the Markdown results table, HTML comparison table, and both per-video Plotly charts.
- Fall back to the original key for unknown or malformed fixture keys so historical/custom metrics remain renderable.

## Design

`benchmarks/render_report.py` owns presentation-only formatting. A small pure `display_video_label(key: str) -> str` helper will parse the known catalog key pattern, map supported language codes, and normalize duration parts. The report data remains untouched: display labels are calculated only while rendering.

This isolates the change from fixture identity, quality-gate matching, and reproducibility hashes. It also ensures previously persisted metrics can be re-rendered without migration.

## Error Handling

The helper must never reject a report. It returns the original key when the expected prefix/suffix, language code, or duration pattern is absent.

## Verification

- Add focused renderer tests for English/Korean durations and malformed-key fallback.
- Assert both Markdown and Plotly HTML contain readable labels and do not expose the known internal key in per-video presentation.
- Run the focused benchmark foundation tests, then the repository verification suite.
