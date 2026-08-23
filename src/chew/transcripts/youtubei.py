"""Structured transcript retrieval through YouTube's player bootstrap endpoint."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping
from contextvars import ContextVar
from typing import Any, cast
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from chew.domain import Provenance, SourceIdentity, Transcript, TranscriptSegment
from chew.transcripts.base import provider_failure_reason
from chew.transcripts.youtube_timedtext import _read_text

PageLoader = Callable[[str], str]
Post = Callable[[str, dict[str, str], bytes], str]


def _post_json(url: str, headers: dict[str, str], body: bytes) -> str:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=20) as response:
        return cast(bytes, response.read()).decode("utf-8")


def _balanced_json(source: str, start: int) -> Mapping[str, Any] | None:
    opening = source.find("{", start)
    if opening < 0:
        return None
    depth = 0
    quoted = False
    escaped = False
    for end in range(opening, len(source)):
        character = source[end]
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
            continue
        if character == '"':
            quoted = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                value = json.loads(source[opening : end + 1])
                return value if isinstance(value, Mapping) else None
    return None


def _bootstrap(page: str) -> tuple[str, Mapping[str, Any], str, Mapping[str, Any]] | None:
    config = _balanced_json(page, page.find("ytcfg.set({"))
    if config is None:
        return None
    api_key = config.get("INNERTUBE_API_KEY")
    context = config.get("INNERTUBE_CONTEXT")
    params_match = re.search(r'"getTranscriptEndpoint":\{"params":"([^"\\]+(?:\\.[^"\\]*)*)"', page)
    if not isinstance(api_key, str) or not isinstance(context, Mapping) or params_match is None:
        return None
    params = json.loads(f'"{params_match.group(1)}"')
    return api_key, context, params if isinstance(params, str) else "", config


def _player_details(page: str) -> tuple[str | None, int]:
    response = _balanced_json(page, page.find("ytInitialPlayerResponse"))
    details = response.get("videoDetails") if isinstance(response, Mapping) else None
    details = details if isinstance(details, Mapping) else {}
    title = details.get("title")
    seconds = details.get("lengthSeconds")
    try:
        duration_ms = round(float(seconds or 0) * 1_000)
    except (TypeError, ValueError):
        duration_ms = 0
    return str(title) if isinstance(title, str) else None, duration_ms


def _nested(value: object, *keys: str) -> object | None:
    current = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _segments(payload: object) -> tuple[TranscriptSegment, ...]:
    values = _nested(
        payload,
        "actions",
    )
    if not isinstance(values, list) or not values:
        return ()
    initial = _nested(
        values[0],
        "updateEngagementPanelAction",
        "content",
        "transcriptRenderer",
        "content",
        "transcriptSearchPanelRenderer",
        "body",
        "transcriptSegmentListRenderer",
        "initialSegments",
    )
    if not isinstance(initial, list):
        return ()
    results: list[TranscriptSegment] = []
    for value in initial:
        renderer = _nested(value, "transcriptSegmentRenderer")
        if not isinstance(renderer, Mapping):
            continue
        runs = _nested(renderer, "snippet", "runs")
        if not isinstance(runs, list):
            continue
        text = "".join(str(run.get("text") or "") for run in runs if isinstance(run, Mapping)).strip()
        try:
            start_ms = int(renderer.get("startMs") or 0)
            duration_ms = int(renderer.get("durationMs") or 0)
        except (TypeError, ValueError):
            continue
        if text and duration_ms > 0:
            results.append(TranscriptSegment(start_ms=start_ms, end_ms=start_ms + duration_ms, text=text))
    return tuple(results)


class YouTubeiTranscriptProvider:
    """Fetch transcript segments using bootstrap credentials from the public watch page."""

    name = "youtubei-transcript"

    def __init__(self, *, page_loader: PageLoader = _read_text, post: Post = _post_json) -> None:
        self.page_loader = page_loader
        self.post = post
        self._attempt_failure: ContextVar[tuple[str, ...]] = ContextVar(
            f"chew_youtubei_failure_{id(self)}", default=()
        )

    def attempt_reasons(self) -> tuple[str, ...]:
        return self._attempt_failure.get()

    async def fetch(self, source: SourceIdentity, language: str) -> Transcript | None:
        self._attempt_failure.set(())
        try:
            page = await asyncio.to_thread(self.page_loader, source.canonical_url)
            bootstrap = _bootstrap(page)
            if bootstrap is None:
                return None
            api_key, context, params, config = bootstrap
            client_value = context.get("client")
            client: Mapping[str, Any] = client_value if isinstance(client_value, Mapping) else {}
            request_context = dict(context)
            request_context["client"] = {**client, "originalUrl": source.canonical_url}
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://www.youtube.com",
                "Referer": source.canonical_url,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "X-Goog-AuthUser": "0",
                "X-Youtube-Bootstrap-Logged-In": "false",
            }
            client_name = config.get("INNERTUBE_CONTEXT_CLIENT_NAME", client.get("clientName"))
            client_version = config.get("INNERTUBE_CONTEXT_CLIENT_VERSION", client.get("clientVersion"))
            visitor_data = config.get("VISITOR_DATA", client.get("visitorData"))
            if isinstance(client_name, (str, int)):
                headers["X-Youtube-Client-Name"] = str(client_name)
            if isinstance(client_version, str):
                headers["X-Youtube-Client-Version"] = client_version
            if isinstance(visitor_data, str):
                headers["X-Goog-Visitor-Id"] = visitor_data
            if isinstance(config.get("XSRF_TOKEN"), str):
                headers["X-Youtube-Identity-Token"] = str(config["XSRF_TOKEN"])
            body = json.dumps({"context": request_context, "params": params}, separators=(",", ":")).encode("utf-8")
            response = await asyncio.to_thread(
                self.post,
                f"https://www.youtube.com/youtubei/v1/get_transcript?{urlencode({'key': api_key})}",
                headers,
                body,
            )
            segments = _segments(json.loads(response))
            if not segments:
                return None
            title, duration_ms = _player_details(page)
            return Transcript(
                source=source,
                language=language,
                duration_ms=max(duration_ms, segments[-1].end_ms),
                provenance=Provenance.TRANSCRIPT_API,
                segments=segments,
                title=title,
            )
        except Exception as error:  # Provider failures are recorded by the fallback chain.
            self._attempt_failure.set((provider_failure_reason(error),))
            return None
