from __future__ import annotations

import json

import pytest

from chew.domain import Provenance
from chew.identity import normalize_youtube_url
from chew.transcripts.youtubei import YouTubeiTranscriptProvider

SOURCE = normalize_youtube_url("https://youtu.be/abcDEF_1234")
pytestmark = pytest.mark.asyncio


async def test_provider_requests_structured_transcript_endpoint() -> None:
    page = '''
    <script>ytcfg.set({"INNERTUBE_API_KEY":"test-key","INNERTUBE_CONTEXT":{"client":{"clientName":"WEB","clientVersion":"1.0","visitorData":"visitor"}}});</script>
    <script>var ytInitialPlayerResponse = {"videoDetails":{"title":"영상 제목","lengthSeconds":"10"}};</script>
    "getTranscriptEndpoint":{"params":"endpoint-params"}
    '''
    captured: dict[str, object] = {}
    response = {
        "actions": [
            {
                "updateEngagementPanelAction": {
                    "content": {
                        "transcriptRenderer": {
                            "content": {
                                "transcriptSearchPanelRenderer": {
                                    "body": {
                                        "transcriptSegmentListRenderer": {
                                            "initialSegments": [
                                                {
                                                    "transcriptSegmentRenderer": {
                                                        "startMs": "0",
                                                        "durationMs": "4000",
                                                        "snippet": {"runs": [{"text": "first"}]},
                                                    }
                                                },
                                                {
                                                    "transcriptSegmentRenderer": {
                                                        "startMs": "4000",
                                                        "durationMs": "6000",
                                                        "snippet": {"runs": [{"text": "second"}]},
                                                    }
                                                },
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ]
    }

    def post(url: str, headers: dict[str, str], body: bytes) -> str:
        captured.update(url=url, headers=headers, body=json.loads(body))
        return json.dumps(response)

    provider = YouTubeiTranscriptProvider(page_loader=lambda _: page, post=post)

    transcript = await provider.fetch(SOURCE, "en")

    assert transcript is not None
    assert transcript.provenance == Provenance.TRANSCRIPT_API
    assert transcript.title == "영상 제목"
    assert transcript.duration_ms == 10_000
    assert [segment.text for segment in transcript.segments] == ["first", "second"]
    assert captured["url"] == "https://www.youtube.com/youtubei/v1/get_transcript?key=test-key"
    assert captured["body"] == {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "1.0",
                "visitorData": "visitor",
                "originalUrl": SOURCE.canonical_url,
            }
        },
        "params": "endpoint-params",
    }
