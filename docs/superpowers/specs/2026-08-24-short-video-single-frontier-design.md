# Short-Video Single-Frontier Design

## Goal

Use one Frontier generation call for videos of 15 minutes or less, while retaining the existing local transcript, evidence-validation, persistence, export, and resume boundaries.

## Decision

`SHORT_VIDEO_MAX_DURATION_MS = 900_000` is a product policy constant. Once the transcript is available, the analysis pipeline selects one of two immutable strategies:

- `single_frontier_v1` for duration less than or equal to 15 minutes.
- `hierarchical_v1` for longer media.

The strategy is included in the request/cache identity and run metadata. A previously cached hierarchical short-video pack cannot be reused for a single-Frontier request.

## Single-Frontier Flow

```text
public or user-provided transcript
-> local normalization / optional deterministic preprocessing / segmentation
-> one `short_video_summary` Frontier request over the prepared transcript
-> local candidate-evidence validation against immutable raw spans
-> local one-topic / one-chapter Knowledge Pack construction
-> existing output compiler and artifact persistence
```

The response schema contains overview, one topic summary, claim candidates, concepts, examples, and further-study items. The local pipeline derives the sole chapter and never makes `chapter_summary` or `compose` calls for this strategy.

## Boundaries

- Frontier remains the sole semantic reasoning runtime.
- Local code performs only deterministic preprocessing, validation, structural assembly, persistence, and export.
- `task_runtimes` cannot route `short_video_summary` to a local runtime because the existing Frontier-first execution plan rejects local summary routes.
- Long videos retain the existing topic -> chapter -> compose DAG.
- A failed single summary produces no Knowledge Pack and remains resumable through the existing scheduler state machine.

## Data and Observability

- Persist one durable job with kind `short_video` and task `short_video_summary`.
- Keep standard generation measurement and add the existing validator measurement when claims include evidence candidates.
- Record strategy and threshold in cache/run metadata and telemetry attributes.
- Construct a normal `KnowledgePack` with one `TopicSummary`, one locally derived `ChapterSummary`, validated evidence refs, model/runtime provenance, and further-study items.

## Verification

- A 15-minute transcript creates one Frontier request and no topic/chapter/compose calls.
- A transcript one millisecond above the threshold keeps the hierarchical calls.
- Invalid evidence candidates are excluded on the single path.
- Cache identities differ between the two strategies.
- Existing output compilation works from the single-path Knowledge Pack.
- Update README, Korean README, agent index, CHANGELOG, IMPROVEMENTS, and handoff.
