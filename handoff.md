# Current Execution Index

> Read this first to answer "what should we do now?" Read the linked canonical document only
> when its acceptance criteria or product decision is needed.

## Branch and State

- Branch: `feat/ollama-summary-efficiency`
- Active roadmap: [`IMPROVEMENTS.md`](IMPROVEMENTS.md)
- Completed history: [`CHANGELOG.md`](CHANGELOG.md)
- Deferred product work: [`PRODUCT_ROADMAP.md`](PRODUCT_ROADMAP.md)

## Next Priorities

1. Complete P0 transcript acquisition: remove browser credential/Keychain dependency from the
   default recovery path, add per-provider and global deadlines, then add VTT/SRT/TXT user
   transcript input. Verify a 5-minute fixture reaches Frontier and creates a Knowledge Pack.
2. Run reviewed Korean and long-video preprocessing benchmarks only after P0 can supply the same
   raw transcript snapshot to both paths. Keep preprocessing opt-in unless it achieves the 10%
   adoption gate without quality regression.
3. Run `chew benchmark run --short-video` for the 4m35s `5m_en` fixture after P0 transcript
   acquisition and a reviewed reference are available. Compare same-transcript, same-Frontier
   one-pass and hierarchical paths before changing the default analysis path.
4. Complete the remaining Policy/Sandbox work: decide on per-task timeout/retry policy in
   `ExecutionPlan` and validate evidence handling on a real Frontier run.

## Latest Transcript Acquisition Result

- Fixture: `https://www.youtube.com/watch?v=c4GaJKprGEs` (about five minutes).
- Tried public `youtubei`, direct `captionTracks` timed-text, yt-dlp manual/automatic captions,
  `youtube-transcript-api`, and `pytubefix`; local requests encountered `400 FAILED_PRECONDITION`,
  `HTTP 429`, or no usable caption result.
- Tried yt-dlp browser-session mode. Whole-Chrome auto-discovery exceeded one minute; selecting a
  single Chrome profile avoided that scan but YouTube returned `The page needs to be reloaded`.
  Browser-session mode can invoke macOS Keychain, so it is not an acceptable default recovery path.
- A full `chew summarize` run was stopped after about three and a half minutes in transcript
  acquisition. No raw snapshot, Frontier request, Knowledge Pack, or user output was produced.
- A third-party public transcript endpoint did return VTT for diagnosis, proving captions exist,
  but it is not a product fallback and must not be used to claim end-to-end success.

## Current Decision

- Frontier remains the final reasoning and summary runtime.
- Ollama does not perform summary or judgment work. Reconsider it only for a specifically defined,
  low-risk helper task with measured benefit.
- Knowledge Graph, Notion, RSS, MCP, REST API, and automation are deferred.

## Verification and Working Tree

- Last documentation check: `git diff --check` passed.
- Untracked benchmark-report directories exist under
  `reports/performance-comparisons/transcript-preprocessing/`; inspect before staging and do not
  include them accidentally.
