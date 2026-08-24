# Transcript Preprocessing Benchmark

## Decision

- Status: `revise`
- Summary: Quality was not evaluated; keep this as evidence, not an adoption decision.

## Executive Summary

| Metric | Value |
|---|---:|
| Baseline total tokens | 79,788 |
| Current total tokens | 78,056 |
| Token delta | -1,732 |
| Token reduction | 2.2% |
| Latency delta | 0.232s |
| Candidate effect detected | `True` |

## Previous vs Current

### Previous pipeline

- Mode: `none`
- Flow: Raw transcript -> segmentation -> LLM-ready transcript
- Summary: Baseline preserves the transcript mostly as acquired and measures the current segmentation path without extra preprocessing.

### Current candidate

- Mode: `current`
- Flow: Transcript preprocessing -> processed transcript -> segmentation -> LLM-ready transcript
- Summary: Candidate runs `current` before segmentation and records cost, speed, quality, reliability, and reproducibility evidence.

## Dimension Scorecard

| Dimension | Status | Summary |
|---|---|---|
| Cost | `better` | 79,788 -> 78,056 tokens (2.2% reduction) |
| Speed | `risk` | 0.000s -> 0.232s preprocessing latency |
| Quality | `not_evaluated` | Not evaluated |
| Reliability | `pass` | All videos comparable |
| Reproducibility | `pass` | Matching lock hash |

## Better / Risk

### Better

- Cost: input tokens fell by 1,732 (2.2%).
- Reliability: all compared videos succeeded without substitutions.
- Reproducibility: baseline and current use the same lock hash.

### Risk

- Speed: preprocessing latency rose by 0.232s (2110163.6%).
- Quality: quality gate was not evaluated; do not adopt from token reduction alone.

## State and Evidence

| Field | Value |
|---|---|
| Baseline run | `baseline-20260824T075239Z` |
| Current run | `current-20260824T075339Z` |
| Baseline git SHA | `c474f93c43f27cbd96b54e9ae55fd4004270aad4` |
| Current git SHA | `c474f93c43f27cbd96b54e9ae55fd4004270aad4` |
| Baseline lock hash | `0e2dbb9bf6251f6d3c14bfd402bd0344ace58d856891ceb13907a78c4ce85e68` |
| Current lock hash | `0e2dbb9bf6251f6d3c14bfd402bd0344ace58d856891ceb13907a78c4ce85e68` |
| Video count | `5` |
| Eligible comparison | `True` |
| Quality gate recorded | `False` |

---

## Question

Does the candidate transcript preprocessing path reduce input cost or latency without violating quality gates?

## Method

- Baseline run: `baseline-20260824T075239Z`
- Current run: `current-20260824T075339Z`
- Eligible comparison: `True`

## Results

| Video | Baseline tokens | Current tokens | Token delta | Reduction | Latency delta | Status |
|---|---:|---:|---:|---:|---:|---|
| youtube_en_2h00m09s_for_benchmark | 25781 | 24633 | -1148 | 4.5% | 0.054s | success |
| youtube_en_2h49m45s_for_benchmark | 28401 | 28366 | -35 | 0.1% | 0.124s | success |
| youtube_en_39m00s_for_benchmark | 9378 | 9032 | -346 | 3.7% | 0.021s | success |
| youtube_en_4m35s_for_benchmark | 866 | 840 | -26 | 3.0% | 0.002s | success |
| youtube_en_55m48s_for_benchmark | 15362 | 15185 | -177 | 1.2% | 0.031s | success |

## Quality Gate

Quality was not evaluated. Do not claim adoption from token reduction alone.
