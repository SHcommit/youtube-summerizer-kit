# Transcript Acquisition Reliability

`chew` treats transcript acquisition as a recoverable input stage before any Frontier synthesis.
No model request is made until one immutable raw transcript snapshot is available.

## Provider Order

1. `yt-dlp` manual captions
2. `yt-dlp` automatic captions
3. `youtube-transcript-api`
4. `pytubefix` captions
5. Optional local Whisper after audio acquisition, or local media supplied by the user

The first accepted transcript is normalized, content-addressed, and reused for all analysis
and output generation. Providers record their provenance; transcript-derived artifacts never
replace the immutable raw snapshot.

## Failure Policy

- `rate_limited`: retry the same provider once with bounded exponential delay, then continue to
  independent providers.
- `access_denied`: continue to the next provider; do not treat it as absent captions.
- `not_available`: continue normally.
- all providers rate-limited: return a distinct error with a retry delay. Do not invoke an LLM or
  fabricate a report.

`yt-dlp` rate-limit mitigation uses request spacing. PO Token plugins, cookies, and proxies are
not enabled automatically. They are user-managed opt-ins because they can expose credentials,
increase account risk, or make results non-reproducible.

## Recovery Paths

1. Retry after the reported delay.
2. Enable `whisper_fallback: true` only after Whisper prerequisites are available.
3. Supply local MP3/MP4 media for local transcription.
4. Prefer a local MP3/MP4 input until dedicated VTT/SRT/TXT transcript-file input is implemented.

For a fair benchmark, resolve and cache one raw transcript before comparing one-pass and
hierarchical Frontier paths. A provider outage invalidates the benchmark instead of producing a
quality claim from mismatched inputs.
