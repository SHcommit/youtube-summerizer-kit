# Transcript Preprocessing Comparison

This report compares raw caption text with the current opt-in local preprocessing recipe.
Benchmark lock SHA-256: `7b93100ad2f9816aaa0ea10d63e6fc719eff6d3e5686ae16efd85b8498072156`

| Key | Raw tokens | Processed tokens | Reduction | Raw topics | Processed topics | Applied stages |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 5m_en | 756 | 727 | 3.84% | 1 | 1 | filler-removal |
| 39m_en | 8,335 | 7,970 | 4.38% | 8 | 8 | filler-removal |
| 1h_en | 13,682 | 13,419 | 1.92% | 10 | 10 | filler-removal |
| 2h_en | 21,822 | 20,744 | 4.94% | 25 | 25 | filler-removal |
| 2h50m_en | 28,732 | 27,416 | 4.58% | 34 | 34 | filler-removal |

These are tokenizer comparison figures, not provider billing or quality claims.
