# Transcript Acquisition

## Purpose

This page is the durable operational record for caption acquisition. It records reproducible
provider behavior, bounded recovery decisions, and rejected approaches. Keep current-session
next actions in [`handoff.md`](../../handoff.md), not here.

## Product Boundary

- `chew` never uses a proxy service, proxy rotation, third-party transcript website, browser
  cookie store, password, or macOS Keychain for transcript recovery.
- Public YouTube caption providers are best-effort. A user-provided VTT, SRT, or TXT file is the
  supported recovery path and is marked `USER_PROVIDED` provenance.
- The final synthesis remains the user's configured Frontier runtime; acquisition does not make
  any LLM routing decision.

## Provider Order and Limits

1. `youtubei-transcript`
2. `youtube-timedtext`
3. `yt-dlp-manual`
4. `yt-dlp-automatic`
5. `youtube-transcript-api`
6. `pytubefix`

Each provider has a 20-second deadline. The public chain has a 60-second monotonic budget.
`rate_limited` retries once with bounded exponential delay only when the remaining global budget
permits it. Attempt reasons are retained in `TranscriptUnavailable` and never include credentials.

## Failure Meanings

| Reason | Meaning | Recovery |
|---|---|---|
| `rate_limited` | YouTube returned `429` or equivalent throttling text. | Retry later, or provide VTT/SRT/TXT. |
| `failed_precondition` | The unofficial `youtubei` operation rejected its prerequisites. | Continue to the next provider; do not treat it as a public API contract. |
| `session_refresh_required` | yt-dlp reported that a browser session needs reload. | Do not read a browser session; provide VTT/SRT/TXT. |
| `provider_timeout` | One adapter exceeded 20 seconds. | Continue to the next provider. |
| `acquisition_timeout` | The 60-second public budget expired. | Stop and offer VTT/SRT/TXT. |

## Root-Cause Analysis and Resolution

### What failed

The original failure was not one defect with one fix.

1. **External YouTube variability:** the same public caption sources returned `429`,
   `FAILED_PRECONDITION`, no usable track, or a browser-session refresh request on different
   attempts. These responses are controlled by YouTube and can vary by video, IP reputation,
   request timing, and caption type.
2. **Single-path operational weakness:** the earlier provider chain could wait for slow adapters
   without a service-owned acquisition budget, making a public failure appear to hang the CLI.
3. **Unsafe recovery proposal:** browser-profile extraction can request macOS Keychain access.
   Even if it recovers a particular video, it violates the product's local credential boundary.
4. **Measurement confusion:** one early full `chew summarize` retest used an existing SQLite raw
   transcript cache and then waited for Frontier synthesis. That wait was not caption acquisition;
   later measurements bypassed the cache and called `TranscriptService` directly.

### What changed

1. `TranscriptService` now owns a 20-second deadline per provider and a 60-second monotonic
   public-acquisition budget. It records `provider_timeout` or `acquisition_timeout` and proceeds
   to the next provider instead of waiting indefinitely.
2. Provider failures map to stable, non-secret reasons (`rate_limited`, `failed_precondition`,
   `access_denied`, `session_refresh_required`, or provider type). The CLI can give a recovery
   action without exposing transport or credential data.
3. The provider chain keeps independent public adapters and reaches `yt-dlp-automatic` after
   manual/public candidates fail. Both current fixtures succeeded at that fallback.
4. Application bootstrap no longer passes configured browser profile or cookie-file settings to
   default providers. There is no Keychain or browser-cookie recovery dependency in the normal
   product path.
5. `--transcript <VTT|SRT|TXT> --source-url <URL>` is the deterministic recovery path. It
   preserves original source identity and marks the raw evidence as `USER_PROVIDED`.

### Resolution Status

**Resolved:** provider hangs have bounded handling; browser credential recovery is removed from
the default pipeline; users have a credential-free transcript-input recovery path.

**Not solved and not claimed:** YouTube can still deny captions. Public extraction is best-effort,
not an entitlement. The remaining P0 validation is a full user-transcript-to-Frontier-to-
Knowledge-Pack run, recorded separately when the configured Frontier runtime is available.

## User Recovery

```bash
chew summarize --transcript ./captions.vtt \
  --source-url 'https://www.youtube.com/watch?v=VIDEO_ID'
```

`--source-url` preserves YouTube source identity and output links. VTT/SRT timing is retained.
TXT uses deterministic 30-second sequential ranges because it contains no native timing.

## Dated Execution Record

### 2026-08-24: Five-minute fixture

- Fixture: `https://www.youtube.com/watch?v=c4GaJKprGEs`.
- Earlier public attempts observed `HTTP 429`, `400 FAILED_PRECONDITION`, no usable caption
  track, and yt-dlp's `The page needs to be reloaded` browser-session error. A browser-profile
  path was rejected because it can trigger Keychain access.
- Cache-bypassed provider-chain run after deadline implementation completed in **23.1 seconds**.
  `youtubei-transcript` returned an HTTP error, `youtube-timedtext` and `yt-dlp-manual` had no
  usable result, and `yt-dlp-automatic` returned **75** caption segments.
- This proves public acquisition can work on the fixture but is not a reliability guarantee.
  The run deliberately stopped before Frontier synthesis; it is not a Knowledge Pack benchmark.

### 2026-08-24: Representative long-video fixture

- Fixture: `https://www.youtube.com/watch?v=ZIaOBAjvc38` (`39m_en`, 2,340 seconds in the
  locked fixture catalog; this is the current representative video near the requested 30-minute
  class).
- Cache-bypassed provider-chain run completed in **16.82 seconds**. `youtubei-transcript`
  returned an HTTP error, timed-text and manual captions had no usable result, and
  `yt-dlp-automatic` returned **836** segments with a 2,340,000 ms duration.
- This was transcript acquisition only. It did not invoke Frontier and must not be reported as a
  summary-quality or end-to-end benchmark.

## Rejected Approaches

- Browser cookie/profile extraction: may access OS credential storage and is not required for the
  supported product path.
- Central, residential, or rotating proxies: paid, operationally fragile, and do not resolve all
  `429`, session, or `FAILED_PRECONDITION` cases.
- Third-party transcript websites as a fallback: violates source/provenance and availability
  guarantees. They may be used only for maintainer diagnosis, never as product transport.
