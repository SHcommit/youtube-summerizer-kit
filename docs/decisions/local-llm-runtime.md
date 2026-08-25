# Local LLM Runtime Decision

## Question

Must `chew` use a local Open LLM, and must that runtime be Ollama?

## Approved Target Decision

Local LLM support remains optional. The product works without a local model,
using deterministic transcript cleanup before a user-selected BYOK Frontier
runtime. When a configured single Ollama model is already available, it may
propose compact input-cleanup annotations. It never performs summary,
judgment, claim generation, evidence acceptance, or final-output composition.

This is the approved implementation target, not a description of the current
production path.

Ollama is the current local-runtime candidate because it provides model
download, lifecycle management, and a stable localhost API. It is not part of
the core domain or the only possible local runtime.

## Runtime Modes

The local cleanup policy has three modes, with `auto` as the default:

1. `auto`: use the configured single model only when the loopback Ollama service
   and model are already available; otherwise use deterministic cleanup.
2. `on`: require the configured model and report an explicit configuration
   error when it is unavailable.
3. `off`: always use deterministic cleanup.

No analysis mode installs Ollama or downloads a model. Any future setup command
must show approximate download size and require explicit confirmation.

## Input-Cleanup Boundary

The model returns a structured sidecar containing raw span identifiers,
boundary hints, filler or repetition candidates, low-confidence ranges,
confidence values, and short reason codes. It does not return a rewritten
transcript or replacement words. Raw text and timestamps remain immutable.
Local code validates the sidecar, may omit validated filler/repetition spans or
insert structural separators, and materializes one prepared transcript while
preserving raw spans for evidence validation.

If the assisted candidate is more than 5% larger in estimated tokens than the
deterministic baseline, changes protected content, fails schema validation, or
times out, the pipeline discards it and immediately uses the deterministic
baseline. It never sends both raw and prepared transcripts to Frontier.

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
Only then decide whether `auto` should remain the recommended mode. This does
not authorize local topic, chapter, compose, claim, or final-summary generation.
