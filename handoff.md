# Current Execution Index

> Read this first to answer "what should we do now?" Read the linked canonical document only
> when its acceptance criteria or product decision is needed.

## Branch and State

- Branch: `feat/improvements-next-step`
- Active roadmap: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)

## Next Priorities

1. Prepare independently human-reviewed quality references for the Korean fixtures, long-video
   preprocessing, and 4m35s short-video conditions. Reference structure is now preflight-validated;
   run the Frontier benchmarks only as the integrated pre-deployment gate.

## Active Constraints

- `benchmarks/videos.lock.json` contains the Korean lecture fixture
  `youtube_ko_45m46s_for_benchmark`, Korean conversational fixture
  `youtube_ko_38m48s_for_benchmark`, plus English fixtures: `youtube_en_4m35s_for_benchmark`,
  `youtube_en_39m00s_for_benchmark`, `youtube_en_55m48s_for_benchmark`,
  `youtube_en_2h00m09s_for_benchmark`, and `youtube_en_2h49m45s_for_benchmark`. A locked fixture
  is a reproducibility target for maintainer benchmarks, not a user-input restriction. Its matching
  quality reference must be independently human-reviewed; the project ships no reusable
  live-reference answer.
- Each lock entry has a required caption `language`; both preprocessing measurement paths request
  that entry-specific language. The Korean lecture has publicly available automatic `ko` captions,
  but this does not establish an availability guarantee.
- `ExecutionPlan` records normal-runtime retry (2 attempts) and 429 policy (3 attempts, 60-second
  budget, 5-second full-jitter cap). The scheduler resets that in-memory 429 budget for an explicit
  `chew resume`. Generation subprocess timeout remains the separate `GenerationRequest` default.
- Do not run or interpret end-to-end Frontier benchmarks during incremental implementation. They are
  reserved for the final pre-deployment gate after functionality, policy boundaries, and loop
  termination work are complete.

## Current Decision

- Frontier remains the final reasoning and summary runtime.
- Ollama does not perform summary or judgment work. Reconsider it only for a specifically defined,
  low-risk helper task with measured benefit.
- Visible-panel browser capture and OCR are not product work: URL-based public transcript
  acquisition is the default path, and VTT/SRT/TXT remains the only explicit recovery input.
- Telemetry is injected by `ApplicationContainer` and uses `ContextVar`-isolated run collectors;
  a scoped DI library remains deferred in `PRODUCT_ROADMAP.md`.
- Knowledge Graph, Notion, RSS, MCP, REST API, and automation are deferred.

## Verification and Working Tree

- `0baee5d` contains the credential-boundary, transcript pipeline, bounded-runtime-policy,
  telemetry, P0 benchmark-snapshot, and migration work. Full verification at that point was
  `282 passed, 2 skipped`; Ruff and mypy passed. `e4d11c6` removes localized Korean segmentation
  depth aliases; its focused tests, Ruff, and mypy passed.
- `3bac530` adds the Korean lecture catalog and per-video caption-language handling. Full
  verification is current: `287 passed, 2 skipped`; Ruff and mypy passed. The metadata and
  caption-track check used anonymous public yt-dlp only; no live Frontier benchmark was run.
- `06d1654` adds the Korean conversational fixture. The same anonymous public metadata and
  caption-track check confirmed `ko`/`ko-orig`; no live Frontier benchmark was run.
- Reviewed benchmark-reference validation is pending commit. Full verification is current:
  `291 passed, 2 skipped`; Ruff and mypy passed. Invalid references now fail before a live provider
  call; this does not replace the required human content review.
- A result-path audit found no hard-coded summary, claim, or evidence content under `src/chew`.
  Static result strings are only renderer structure and state/provenance labels; every semantic
  result value comes from a Knowledge Pack and validated transcript evidence.
- The five-minute URL path completed under run `d2e4a1f7-9ab7-442a-9084-9a6129f7021d`; its
  `auto_subtitle` raw artifact, Knowledge Pack, Digest, and cached Blog reassembly are recorded
  in [`docs/wiki/transcript-acquisition.md`](docs/wiki/transcript-acquisition.md). The output
  schema fix has focused tests and a live reassembly result. Latest full verification: `279
  passed, 2 skipped`; Ruff and mypy passed.
- P0 transcript acquisition is complete. Short-video benchmark preparation resolves one public raw
  transcript snapshot before any Frontier condition runs and reuses it for all conditions and
  repeats; failure therefore creates no live condition or report. This was verified with focused
  tests only, not a live benchmark.
- Bounded 429 retry implementation has focused scheduler/policy coverage; full verification is the
  immediate next action before the next live Frontier validation. The required scheduler benchmark
  completed in `2m34.57s` (320,600 input / 9,647 output), above the recorded `1m50s` baseline;
  no 429 was reported and the separate dashboard process had no in-memory spans. This result is
  non-decisive and must not be repeated or interpreted until the final pre-deployment benchmark.
- Frontier validation is complete: the recorded five-minute Codex run rejected 1 of 11 proposed
  evidence candidates (10 valid), and a separate controlled Codex run with one injected topic
  failure produced `partial` status and the expected `01:00-02:00` missing range while actual
  Codex chapter and compose jobs completed. Details are in
  [`docs/wiki/transcript-acquisition.md`](docs/wiki/transcript-acquisition.md).
- Acquisition evidence and root-cause history are in
  [`docs/wiki/transcript-acquisition.md`](docs/wiki/transcript-acquisition.md).
- Untracked benchmark-report directories exist under
  `reports/performance-comparisons/transcript-preprocessing/`; inspect before staging and do not
  include them accidentally.
