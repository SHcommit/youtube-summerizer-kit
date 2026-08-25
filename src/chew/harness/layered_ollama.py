"""Layered Ollama harness: routes pipeline tasks to model-size tiers."""

from __future__ import annotations

from chew.domain import GenerationRequest, GenerationResult
from chew.harness.base import HarnessCapabilities, HarnessProbe
from chew.harness.ollama import OllamaHarness, Transport

# Maps GenerationRequest.task → layer key.
# Unknown tasks default to "layer3" (most capable / safest).
TASK_LAYERS: dict[str, str] = {
    "topic_summary": "layer1",   # Map: 1.5B lightweight
    "repair": "layer1",          # Repair is a cheap re-generation
    "chapter_summary": "layer2", # Combine: 7B mid-tier
    "output_outline": "layer3",  # Reduce/output: 14B capable
    "output_compose": "layer3",
    "output_verify": "layer3",
    "compose": "layer3",
}

# Pinned quantized model tags for reproducibility (§7-7).
# Override by passing model= explicitly or subclassing.
LAYER1_MODEL = "qwen2.5:1.5b-instruct-q4_K_M"
LAYER2_MODEL = "qwen2.5:7b-instruct-q4_K_M"
LAYER3_MODEL = "qwen2.5:14b-instruct-q4_K_M"


class LayeredOllamaHarness:
    """Routes each pipeline task to the appropriate Ollama model tier.

    Layer 1 (Map)     — topic_summary, repair    → lightweight 1.5B model
    Layer 2 (Combine) — chapter_summary           → mid-tier 7B model
    Layer 3 (Reduce)  — compose, output_*         → capable 14B+ model
    """

    runtime_id = "layered_ollama"

    def __init__(
        self,
        layer1_model: str = LAYER1_MODEL,
        layer2_model: str = LAYER2_MODEL,
        layer3_model: str = LAYER3_MODEL,
        *,
        endpoint: str = "http://127.0.0.1:11434",
        transport: Transport | None = None,
    ) -> None:
        self._layers: dict[str, OllamaHarness] = {
            "layer1": OllamaHarness(model=layer1_model, endpoint=endpoint, transport=transport),
            "layer2": OllamaHarness(model=layer2_model, endpoint=endpoint, transport=transport),
            "layer3": OllamaHarness(model=layer3_model, endpoint=endpoint, transport=transport),
        }

    def _select_layer(self, task: str) -> OllamaHarness:
        return self._layers[TASK_LAYERS.get(task, "layer3")]

    async def probe(self) -> HarnessProbe:
        """Probe via layer1 (lightest). Returns runtime_id='layered_ollama'."""
        inner = await self._layers["layer1"].probe()
        return HarnessProbe(
            runtime_id=self.runtime_id,
            available=inner.available,
            auth_ready=inner.auth_ready,
            version=inner.version,
            capabilities=HarnessCapabilities(structured_output=True, max_concurrency=1),
            detail=inner.detail,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        task = request.task
        if task == "repair":
            target_task = request.input.get("target_task")
            if isinstance(target_task, str):
                task = target_task
        return await self._select_layer(task).generate(request)

    async def aclose(self) -> None:
        """Close all layer HTTP clients."""
        for layer in self._layers.values():
            await layer.aclose()
