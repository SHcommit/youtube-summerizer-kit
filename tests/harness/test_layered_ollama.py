from __future__ import annotations

import pytest

from chew.domain import GenerationRequest
from chew.harness.layered_ollama import TASK_LAYERS, LayeredOllamaHarness


def _make_request(task: str) -> GenerationRequest:
    return GenerationRequest(
        request_id=f"req-{task}",
        task=task,
        input={"topic_id": "t1", "title": "Test"},
        output_schema={"type": "object"},
        trace_id="run-1",
    )


@pytest.mark.asyncio
async def test_layered_ollama_routes_topic_summary_to_layer1() -> None:
    """topic_summary task routes to the 1.5B layer1 model."""
    layer1_model = "qwen2.5:1.5b"
    layer2_model = "qwen2.5:7b"
    layer3_model = "qwen2.5:14b"
    selected_models: list[str] = []

    async def fake_transport(payload: dict) -> dict:
        selected_models.append(str(payload.get("model", "")))
        return {"response": '{"summary": "ok"}', "prompt_eval_count": 1, "eval_count": 1}

    harness = LayeredOllamaHarness(
        layer1_model=layer1_model,
        layer2_model=layer2_model,
        layer3_model=layer3_model,
        transport=fake_transport,
    )
    await harness.generate(_make_request("topic_summary"))
    assert selected_models == [layer1_model]


@pytest.mark.asyncio
async def test_layered_ollama_routes_chapter_summary_to_layer2() -> None:
    """chapter_summary task routes to the 7B layer2 model."""
    selected_models: list[str] = []

    async def fake_transport(payload: dict) -> dict:
        selected_models.append(str(payload.get("model", "")))
        return {"response": '{"summary": "ok"}', "prompt_eval_count": 1, "eval_count": 1}

    harness = LayeredOllamaHarness(
        layer1_model="qwen2.5:1.5b",
        layer2_model="qwen2.5:7b",
        layer3_model="qwen2.5:14b",
        transport=fake_transport,
    )
    await harness.generate(_make_request("chapter_summary"))
    assert selected_models == ["qwen2.5:7b"]


@pytest.mark.asyncio
async def test_layered_ollama_routes_compose_to_layer3() -> None:
    """compose task routes to the 14B layer3 model."""
    selected_models: list[str] = []

    async def fake_transport(payload: dict) -> dict:
        selected_models.append(str(payload.get("model", "")))
        return {"response": '{"result": "ok"}', "prompt_eval_count": 1, "eval_count": 1}

    harness = LayeredOllamaHarness(
        layer1_model="qwen2.5:1.5b",
        layer2_model="qwen2.5:7b",
        layer3_model="qwen2.5:14b",
        transport=fake_transport,
    )
    await harness.generate(_make_request("compose"))
    assert selected_models == ["qwen2.5:14b"]


@pytest.mark.asyncio
async def test_layered_ollama_routes_unknown_task_to_layer3() -> None:
    """Unknown task names default to layer3 (most capable)."""
    selected_models: list[str] = []

    async def fake_transport(payload: dict) -> dict:
        selected_models.append(str(payload.get("model", "")))
        return {"response": '{"result": "ok"}', "prompt_eval_count": 1, "eval_count": 1}

    harness = LayeredOllamaHarness(
        layer1_model="qwen2.5:1.5b",
        layer2_model="qwen2.5:7b",
        layer3_model="qwen2.5:14b",
        transport=fake_transport,
    )
    await harness.generate(_make_request("unknown_future_task"))
    assert selected_models == ["qwen2.5:14b"]


@pytest.mark.asyncio
async def test_layered_ollama_aclose_closes_all_layers() -> None:
    """aclose() closes all three layer clients without error."""
    harness = LayeredOllamaHarness()
    # Trigger client creation on all layers by calling _get_client
    harness._layers["layer1"]._get_client()
    harness._layers["layer2"]._get_client()
    harness._layers["layer3"]._get_client()
    await harness.aclose()
    assert harness._layers["layer1"]._client is None
    assert harness._layers["layer2"]._client is None
    assert harness._layers["layer3"]._client is None


def test_task_layers_routing_table_covers_all_engine_tasks() -> None:
    """TASK_LAYERS must cover all tasks emitted by the engine."""
    engine_tasks = {"topic_summary", "chapter_summary", "compose", "repair",
                    "output_outline", "output_compose", "output_verify"}
    assert engine_tasks.issubset(set(TASK_LAYERS.keys()))


def test_pinned_model_constants_use_quantized_tags() -> None:
    from chew.harness.layered_ollama import LAYER1_MODEL, LAYER2_MODEL, LAYER3_MODEL

    assert LAYER1_MODEL == "qwen2.5:1.5b-instruct-q4_K_M"
    assert LAYER2_MODEL == "qwen2.5:7b-instruct-q4_K_M"
    assert LAYER3_MODEL == "qwen2.5:14b-instruct-q4_K_M"


def test_layered_ollama_harness_defaults_to_pinned_tags() -> None:
    import inspect

    from chew.harness.layered_ollama import LAYER1_MODEL, LAYER2_MODEL, LAYER3_MODEL, LayeredOllamaHarness

    sig = inspect.signature(LayeredOllamaHarness.__init__)
    assert sig.parameters["layer1_model"].default == LAYER1_MODEL
    assert sig.parameters["layer2_model"].default == LAYER2_MODEL
    assert sig.parameters["layer3_model"].default == LAYER3_MODEL
