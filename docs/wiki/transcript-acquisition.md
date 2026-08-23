# Transcript Acquisition Reliability

`chew` treats transcript acquisition as a recoverable input stage before any Frontier synthesis.
No model request is made until one immutable raw transcript snapshot is available.

## Provider Order

1. YouTube player bootstrap `youtubei/v1/get_transcript` structured segments
2. Direct YouTube player `captionTracks` discovery, then signed timed-text VTT retrieval
3. `yt-dlp` manual captions
4. `yt-dlp` automatic captions
5. `youtube-transcript-api`
6. `pytubefix` captions
7. Optional local Whisper after audio acquisition, or local media supplied by the user

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

The direct provider makes the input boundary explicit: a public watch response can contain a
caption track while its `api/timedtext` VTT request returns `HTTP 429 Too Many Requests`.
The direct provider records that as `rate_limited` and does not invoke an LLM.

The `youtubei` provider uses the watch page's bootstrapped API key, client context, and transcript
endpoint params. It is an independent best-effort path, not an official public API. A `400
FAILED_PRECONDITION` is recorded as a provider failure and the chain continues to caption tracks.

`yt-dlp` enables Node.js and its official EJS challenge component when Node.js is already installed,
which is required for current YouTube JavaScript challenges. Cookies and proxies are never enabled automatically. A user may explicitly run
`chew auth youtube --from-browser chrome`; only then does `chew` read the selected local browser,
retain YouTube-domain cookies in its private local credential file, and pass that file to yt-dlp.
The credential can be removed with `chew auth youtube --clear`. No cookie is sent to a `chew`
server. This can expose the user's own account to YouTube enforcement and does not guarantee access.
Advanced users may instead set `youtube_cookie_file: ./youtube-cookies.txt` in `CHEW.md`; the
adapter reads that supplied file in place.

## Recovery Paths

1. Retry after the reported delay.
2. Optionally run `chew auth youtube --from-browser chrome` for the user's local login session.
3. Optionally set `youtube_cookie_file` for a user-supplied YouTube-only cookie file.
4. Enable `whisper_fallback: true` only after Whisper prerequisites are available.
5. Supply local MP3/MP4 media for local transcription.
6. Prefer a local MP3/MP4 input until dedicated VTT/SRT/TXT transcript-file input is implemented.

For a fair benchmark, resolve and cache one raw transcript before comparing one-pass and
hierarchical Frontier paths. A provider outage invalidates the benchmark instead of producing a
quality claim from mismatched inputs.
