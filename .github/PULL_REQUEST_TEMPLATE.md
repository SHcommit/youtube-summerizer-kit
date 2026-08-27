## Why
<!-- What problem does this solve? Link the issue: Closes #... -->

## What Changed
<!-- Short implementation summary. -->

## Architecture Impact
- [ ] No architecture boundary change
- [ ] Updates core/pipeline/app/harness/transcripts/interfaces boundaries
- [ ] ADR or `docs/agent-index.md` update included
- ADR / Decision: <!-- link docs/decisions/000X-....md, or "None" -->

## AI / Runtime Impact
- [ ] No prompt/schema/model/harness behavior change
- [ ] Prompt/schema/model/runtime behavior changed
- [ ] Evaluation or benchmark result linked below
- If a prompt bundle version changed (see `docs/decisions/0003-run-manifest-provenance.md`):
  - [ ] behavior-preserving (wording/format only)
  - [ ] behavior-changing (quality or output shape)
  - [ ] migration-required (existing Knowledge Packs need reprocessing)

## Verification
- [ ] `uv run --extra dev pytest`
- [ ] `uv run --extra dev ruff check .`
- [ ] `uv run --extra dev mypy src/chew`

## Benchmark
- [ ] Not required
- [ ] Required and linked:
<!-- reports/... -->

## Documentation
- [ ] `CHANGELOG.md` updated
- [ ] `README.md` updated
- [ ] `README.ko.md` updated
- [ ] `docs/agent-index.md` updated
- [ ] Not user-facing / not required

## Release Note
<!-- 1-3 lines suitable for GitHub Release. Write "None" if internal only. -->

## Breaking Change / Migration
<!-- None, or describe migration. -->
