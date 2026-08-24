# Transcript Acquisition Resilience Design

## Goal

Make transcript acquisition complete predictably: public YouTube providers have bounded
execution, failures are retained as structured diagnostics, and a user-supplied transcript
can always enter the existing Frontier-first pipeline without browser credentials.

## Scope

- Keep `TranscriptProvider.fetch(source, language)` as the provider port.
- Bound each remote provider attempt to 20 seconds and the complete remote acquisition to
  60 seconds. Preserve `rate_limited`, `access_denied`, `session_refresh_required`, timeout,
  and generic provider failures in `TranscriptAttempt`.
- Add a file-input adapter for VTT, SRT, and TXT. The input is immutable raw evidence; parsing
  records its format and derives timestamps for plain text when no timings are available.
- Add `chew summarize --transcript PATH --source-url URL` so a supplied source URL remains the
  source identity and output link. The source positional argument is not required when both
  options are supplied.
- Do not read or persist browser cookies, passwords, Keychain values, or proxy credentials.
- Run the five-minute fixture through URL acquisition after the deadline work. If public access
  is blocked, record the bounded diagnostic and exercise the same pipeline through VTT/SRT/TXT.

## Boundaries

`transcripts/service.py` owns provider sequencing, deadlines, retries, and diagnostic output.
`transcripts/user_input.py` owns deterministic VTT/SRT/TXT parsing and has no network imports.
The CLI only validates option combinations and creates an explicit file provider. The pipeline
continues to consume a normal `Transcript`, so synthesis, evidence validation, and artifacts do
not learn about YouTube failure details.

## Documentation and Operational Record

- `docs/wiki/transcript-acquisition.md` is the durable troubleshooting and decision record.
- `handoff.md` contains only the active blocker and most recent reproducible result.
- `CHANGELOG.md` records released user-visible behavior.
- `docs/agent-index.md` and `AGENTS.md` point agents to the index and module boundaries.

## Non-goals

- No proxy service, proxy rotation, or third-party transcript-site fallback.
- No browser-session or Keychain recovery path.
- No speech-to-text expansion beyond the existing explicit Whisper option.
- No changes to Frontier model choice or summary quality policy.

## Acceptance Criteria

1. A hung provider cannot exceed 20 seconds and a public provider chain cannot exceed 60 seconds.
2. `429`, `FAILED_PRECONDITION`, session-refresh, and timeout outcomes are observable without
   leaking credentials.
3. A VTT/SRT/TXT file and `--source-url` reach the existing `KnowledgePack` workflow with no
   browser credential access.
4. The five-minute fixture has a dated execution record stating either successful public capture
   or the structured bounded failure, followed by a file-input pipeline result.
