from __future__ import annotations

import json

from chew.core.models import GenerationRequest
from chew.core.prompts import GKT_PROMPT_BUNDLE_ID, GKT_PROMPT_FINGERPRINT, HARNESS_JSON_INSTRUCTION
from chew.harness.builtin import request_prompt


def test_gkt_prompt_bundle_id_is_a_readable_logical_id() -> None:
    assert GKT_PROMPT_BUNDLE_ID == "knowledge-extract/v1"


def test_gkt_prompt_fingerprint_is_stable_and_tracks_the_instruction() -> None:
    from chew.core.identity import fingerprint

    assert fingerprint(
        {"bundle": GKT_PROMPT_BUNDLE_ID, "instruction": HARNESS_JSON_INSTRUCTION}
    ) == GKT_PROMPT_FINGERPRINT


def test_request_prompt_embeds_the_same_harness_instruction_used_by_the_fingerprint() -> None:
    request = GenerationRequest(
        request_id="req-1",
        task="knowledge_extract",
        input={"key": "value"},
        output_schema={"type": "object"},
        trace_id="trace-1",
    )

    payload = json.loads(request_prompt(request))

    assert payload["instruction"] == HARNESS_JSON_INSTRUCTION
