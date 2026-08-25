# Transcript Token Baseline

This report measures raw caption text before the Phase 1 preprocessing pipeline.
Benchmark lock SHA-256: `7b93100ad2f9816aaa0ea10d63e6fc719eff6d3e5686ae16efd85b8498072156`

| Key | Duration (locked/actual) | Raw chars | cl100k tokens | Fillers | Filler ratio | Topics | Source |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 5m_en | 275s / 275s | 3,619 | 756 | 29 | 4.07% | 1 | auto_subtitle |
| 39m_en | 2340s / 2340s | 37,544 | 8,335 | 246 | 3.36% | 8 | auto_subtitle |
| 1h_en | 3348s / 3348s | 62,161 | 13,682 | 109 | 0.93% | 10 | auto_subtitle |
| 2h_en | 7209s / 7210s | 103,790 | 21,822 | 762 | 3.79% | 25 | auto_subtitle |
| 2h50m_en | 10185s / 10185s | 126,722 | 28,732 | 16 | 0.07% | 34 | manual_subtitle |

Duration differences should be reviewed before treating a run as comparable.
