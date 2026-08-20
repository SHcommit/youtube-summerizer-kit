# Local LLM Runtime Decision

## Question

Must `chew` use a local Open LLM, and must that runtime be Ollama?

## Current Decision

No. Local LLM support is optional. The product must work with a user-selected
BYOK runtime without installing a local model.

Ollama is the current local-runtime candidate because it provides model
download, lifecycle management, and a stable localhost API. It is not part of
the core domain or the only possible local runtime.

## User Choices

At first-time configuration, the user may choose one of the following:

1. Use a configured BYOK runtime only. No local model download occurs.
2. Install a small local Open LLM, such as Qwen3 4B, for local execution.
3. Install a larger local Open LLM, such as Qwen3 8B, when local quality needs
   justify the additional disk and memory use.
4. Defer the choice and change it later.

The CLI must show approximate download size and require explicit confirmation
before invoking a model download. It must not install Ollama or download a
model silently.

## Why Use Ollama When Local Execution Is Selected

- It keeps the application focused on transcript analysis rather than model
  file formats, GPU settings, model serving, and inference lifecycle.
- Its CLI can manage model download and status, while the application can call
  the localhost API through the existing harness adapter.
- It keeps a future local-runtime change behind the Harness adapter boundary.

## Why Not Require It

- Local models consume disk, memory, and startup time.
- Frontier BYOK models may provide better structured-output quality for some
  users.
- Bundling our own inference engine would substantially expand the product
  scope; choosing not to use Ollama does not justify building that engine now.

## Adoption Gate

Do not make local execution the default based on assumptions. Compare the
locked 39-minute and 55-minute fixtures in `IMPROVEMENTS.md` and publish the
measured token usage, latency, repair rate, evidence quality, and memory use.
Only then decide whether a local model should be recommended for a workflow.
