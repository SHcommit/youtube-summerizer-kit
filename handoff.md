# Current Execution Index

> Read this first to answer "what should we do now?" Read the linked canonical document only
> when its acceptance criteria or product decision is needed.

## Branch and State

- Branch: `feature/benchmark-quality-readiness`
- Active roadmap: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)

## Next Priorities

1. Revisit the Frontier-call policy before implementation: default to one Frontier request whenever
   the selected model accepts the prepared transcript. Do not use video duration to automatically
   fan out 3--5 semantic calls; determine capability from the selected runtime/model's input budget.
   Any multi-call fallback requires an explicit, separately approved product policy.
2. Review the existing `benchmarks/reference-drafts/` queues and transcribe approved candidates into
   independently human-reviewed JSON references for the Korean fixtures, long-video preprocessing,
   and 4m35s short-video conditions. Run the remaining Frontier benchmarks only as the integrated
   pre-deployment gate.
3. Repair the short-video benchmark's evidence-reference comparability and make its prompt-policy
   comparison explicit before using it for a default-path decision.

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
- `79e5e8e` adds benchmark-reference validation. Full verification at that point was
  `291 passed, 2 skipped`; Ruff and mypy passed. Invalid references now fail before a live provider
  call; this does not replace the required human content review.
- `c474f93` adds AI-assisted, non-executable reference drafts. Focused benchmark tests passed
  (`39 passed`), as did Ruff and mypy. The source captions were retrieved anonymously with public
  yt-dlp; no browser credentials, local profile, or live Frontier benchmark were used.
- The latest five-English-video metrics-only run found `origin/develop` already up to date. Baseline
  `baseline-20260824T075239Z` and current
  `current-20260824T075339Z` used the same temporary five-video lock; all videos succeeded and
  current preprocessing reduced tokenizer input from 79,788 to 78,056 (2.2%) with 0.232 seconds of
  aggregate preprocessing latency. Quality was not evaluated, so the report status is `revise` and
  no default-adoption decision follows.
- `d695ee8` defines the presentation-only benchmark-label contract; `caff0ba` implements it. The
  renderer replaces internal keys in Markdown, HTML tables, Plotly axes, and fallback HTML
  with labels such as `English · 2h 00m`; the persisted keys remain unchanged. Full verification:
  `293 passed, 2 skipped`; Ruff and mypy passed. A regenerated five-video Plotly report is under
  `/tmp/chew-benchmark-five-labels.g8XKJ2/current/report.html`.
- User-approved short-video benchmark run `benchmark-results/run-7022e011212b/` compared the
  anonymously acquired 14m34s English transcript for `aBUniZHgCnE` across three Codex repeats per
  path. Single-pass median latency/usage was `16.952s`/`29,192`; hierarchical was
  `57.744s`/`348,963`. Both had zero evidence coverage, and the paths carry different prompt
  fingerprints, so this is not a default-path decision. Keep the reference-evidence/prompt-policy
  repair as the immediate prerequisite for rerunning it.
- The previous `single_frontier_v1` 15-minute design is not implementation-ready: duration alone
  is not a valid trigger for fan-out. Gemini long-context models can accept much longer prepared
  transcripts in one request, so the policy must become runtime/model input-budget aware first.
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
