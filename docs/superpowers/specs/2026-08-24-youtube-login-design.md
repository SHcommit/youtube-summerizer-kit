# YouTube Login Fallback Design

## Goal

Let a user explicitly connect their own logged-in browser session so `chew` can
retrieve YouTube captions when anonymous caption providers are rate-limited.

## Scope

Add a nested CLI workflow:

```text
chew auth youtube --from-browser chrome
chew auth youtube --clear
```

The authentication step is optional. Anonymous caption providers remain the
first choice. The CLI recommends the command only after a YouTube rate-limit or
access block; it does not make a Google account a first-run requirement.

## Data Flow

1. The user explicitly selects a supported local browser, initially `chrome`,
   `chromium`, or `firefox`.
2. `yt-dlp` reads that local browser's cookie store once using its documented
   browser-cookie support.
3. `chew` writes a private Netscape cookie file in its application-data
   directory, retaining only `youtube.com` and subdomain cookies.
4. Existing `YtDlpSubtitleProvider` receives that file path and uses it only
   for YouTube caption extraction.
5. `chew auth youtube --clear` securely removes the managed cookie file and
   marks YouTube authentication disconnected.

No provider sends cookies to a `chew` server. `chew` never scans browser
profiles without the explicit command, and it never stores source browser paths
in `CHEW.md`.

## Components

### `transcripts/youtube_auth.py`

Owns browser-cookie import, domain filtering, file mode restriction, status,
and deletion. It exposes a small service independent of Typer:

```python
class YouTubeAuthStore:
    def connect_from_browser(self, browser: str) -> Path: ...
    def cookie_file(self) -> Path | None: ...
    def clear(self) -> bool: ...
```

The implementation uses yt-dlp's cookie support rather than manually decoding
Chrome or Firefox storage. A temporary cookie export is created with restricted
permissions, parsed as Netscape cookies, filtered to domains equal to or ending
in `.youtube.com`, then deleted even on failure. The final file is mode `0600`.

### `app/bootstrap.py`

Resolves the managed cookie file first and the existing explicit
`youtube_cookie_file` setting second. This preserves the advanced manual option
and lets a project override the managed credential deliberately.

### `cli/main.py`

Adds `chew auth youtube`. It prints a concise account-risk warning before
connection, reports only a path-free success state, and never prints cookie
contents. The existing rate-limit error changes its recovery instruction to
`chew auth youtube --from-browser chrome`.

## Error Handling

- Unsupported browser: actionable supported-browser list; no files created.
- Browser access/decryption failure: explain that the browser must be locally
  accessible and the user can use the existing explicit `youtube_cookie_file`.
- No YouTube cookies after filtering: report that the user must sign in at
  `youtube.com`; do not create a credential file.
- Authentication does not guarantee access: a valid login can still face
  account, age, members-only, or YouTube anti-automation restrictions.
- `--clear` is idempotent and succeeds when no managed credential exists.

## Tests

- Auth store filters a mixed-domain cookie export to YouTube domains only.
- Auth store deletes temporary data and applies owner-only permissions.
- Missing YouTube cookies and unsupported browsers fail without a credential.
- Bootstrap selects managed credentials without changing the explicit
  `youtube_cookie_file` configuration contract.
- CLI connects, clears, and renders rate-limit recovery guidance without
  exposing secrets.

## Documentation

Update both READMEs, the transcript-acquisition wiki, `docs/agent-index.md`,
the packaged `CHEW.md` comments, and the Unreleased changelog. Documentation
must state that login is an optional recovery path, not a guarantee or a proxy
bypass.
