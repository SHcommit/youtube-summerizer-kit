# Transcript Preprocessing Benchmark

## Reviewed conclusion — 2026-08-25

Keep transcript preprocessing opt-in. Do not change the default from this
measurement.

The compared seven-fixture metrics-only run reduced tokenizer input from
132,312 to 118,716 tokens (13,596 tokens, **10.3%**). All fixtures completed
without substitution, and baseline/current use the same locked-video hash.
The comparison also recorded 0.373 seconds of aggregate preprocessing latency.

This is reproducible local measurement evidence only. It has no provider
billing or Frontier quality result, and quality was intentionally not evaluated.
It must not be used as an adoption or marketing claim.

| Evidence | Run |
|---|---|
| Baseline | `baseline-20260825T052411Z` |
| Candidate | `current-20260825T052533Z` |
| Locked fixtures | 7 (English 5, Korean 2) |
| Report status | `revise` |

The immutable source artifacts remain local under
`reports/performance-comparisons/transcript-preprocessing/`. The reviewed
candidate report is `current-20260825T052533Z/report.md` and its companion
`report.html` uses the standard benchmark UI.
