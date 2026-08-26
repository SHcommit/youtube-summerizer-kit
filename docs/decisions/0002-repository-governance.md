# Repository Governance Decision

## Question

How should this repository evolve from a code store into an Engineering OS without
adding process that is too heavy for the current project size?

## Context

The project is expanding across AI backend, multiple harnesses, CLI, future web
interfaces, RAG/research modules, agent contracts, release automation, and
documentation. The repository already contains strong internal knowledge
artifacts: `AGENTS.md`, `docs/agent-index.md`, `IMPROVEMENTS.md`,
`PRODUCT_ROADMAP.md`, `handoff.md`, architecture diagrams, wiki pages, and
benchmark reports.

The weak point is not the absence of documents. The weak point is traceability
between GitHub operating objects and those documents:

- Issue to PR to commit to release is not consistently connected.
- PR labels mostly cover dependency and documentation changes, not product
  areas such as pipeline, harnesses, transcripts, agents, benchmarks, or release.
- GitHub Projects exist but do not currently carry work items.
- Milestones are not used.
- Branch protection has been enabled by the maintainer for `master` and
  `develop`, but required checks and release-specific consistency gates still
  need to be connected.
- `CHANGELOG.md` is useful but currently carries too much responsibility. It
  should not be the only index for feature history, architecture decisions,
  benchmark evidence, and release notes.
- Stale naming such as `src/ytsum` can still appear in GitHub templates, while
  the active package is `src/chew`.
- Version state can drift. At the time of this decision, GitHub has a latest
  release/tag `v0.2.0`, while active development files can still show
  `pyproject.toml` version `0.1.2`.

## Decision

Keep `CHANGELOG.md`, but narrow its role. It remains the human-readable release
history for completed user-facing, operational, architecture, CLI, and
documentation changes. It is not the project board, ADR log, benchmark database,
incident log, or agent handoff.

Use the following source-of-truth split:

| Concern | Source of truth |
|---|---|
| Current execution state | `handoff.md` |
| Active unfinished work | `IMPROVEMENTS.md` |
| Deferred product opportunities | `PRODUCT_ROADMAP.md` |
| Architecture and operating decisions | `docs/decisions/` |
| Durable external-service and operational notes | `docs/wiki/` |
| Performance and benchmark evidence | `reports/` and `benchmarks/` |
| Agent/codebase navigation | `docs/agent-index.md` |
| Release history | `CHANGELOG.md` and GitHub Releases |
| Work tracking | GitHub Issues, labels, milestones, and one Project board |

Repository governance should be introduced in this order:

1. Make release version state consistent.
2. Add release consistency checks before any new tag can publish.
3. Remove stale names and obsolete verification commands.
4. Add a small but useful label taxonomy.
5. Upgrade PR and issue templates so traceability starts at intake.
6. Use one GitHub Project for current execution state.
7. Add conditional checks for architecture, benchmark, and AI runtime impact.

## Release Version Policy

The project uses release PRs rather than fully automatic semantic release for
now. The release path is:

```text
develop -> release/vX.Y.Z -> master -> tag vX.Y.Z -> GitHub Release/PyPI
```

The release PR must make these agree before the tag is created:

- `pyproject.toml` `[project].version`
- release branch name
- git tag
- GitHub Release
- `CHANGELOG.md` version heading
- benchmark or release-readiness report when required

The release consistency workflow should fail on mismatch. At minimum, it should
check:

- tag `vX.Y.Z` matches package version `X.Y.Z`;
- release branch `release/vX.Y.Z` matches package version `X.Y.Z`;
- `CHANGELOG.md` contains `## [X.Y.Z] - YYYY-MM-DD`;
- verification commands pass:
  - `uv run --extra dev pytest`
  - `uv run --extra dev ruff check .`
  - `uv run --extra dev mypy src/chew`
- package build and clean wheel smoke test pass.

## CHANGELOG Policy

`CHANGELOG.md` should answer: "What changed in a released or soon-to-be
released version that a user, maintainer, or operator should know?"

It should not contain every intermediate note from a long feature branch. Those
belong in PRs, ADRs, benchmark reports, or `handoff.md`.

GitHub generated release notes may list merged PRs and contributors. The
curated GitHub Release body should summarize the high-signal changes from
`CHANGELOG.md` and link to benchmark reports or migration notes when relevant.

## Label Policy

Use labels to reduce search cost and drive lightweight automation. Keep the
taxonomy small enough for a one-to-three-person project.

Recommended labels:

- `kind:feature`, `kind:bug`, `kind:refactor`, `kind:docs`, `kind:spike`
- `area:core`, `area:pipeline`, `area:storage`, `area:harness`, `area:transcripts`,
  `area:cli`, `area:agents`, `area:web`, `area:benchmark`, `area:docs`, `area:ci`,
  `area:release`
- `priority:P0`, `priority:P1`, `priority:P2`, `priority:P3`
- `status:needs-triage`, `status:ready`, `status:blocked`,
  `status:needs-benchmark`
- `impact:user-facing`, `impact:architecture`, `impact:performance`,
  `impact:security`, `impact:breaking`
- `knowledge:adr`, `knowledge:benchmark`

File-based `area:*` labels should be automatic. Priority and final impact
should remain human-reviewed until the project has a larger contributor base.

## Branch Policy

Topic branches should encode intent and connect to GitHub automation:

```text
feature/<issue-number>-<topic>
fix/<issue-number>-<topic>
docs/<issue-number>-<topic>
refactor/<issue-number>-<topic>
bench/<issue-number>-<topic>
ci/<issue-number>-<topic>
spike/<topic>
release/vX.Y.Z
```

`master` is production release history. `develop` is integration. Topic branches
target `develop`; release branches target `master`.

## PR Policy

Pull requests should carry the context that future maintainers need:

- Why the change exists.
- What changed.
- Linked issue.
- Architecture impact.
- AI/runtime/prompt/model impact.
- Verification results.
- Benchmark requirement or explicit reason not required.
- Documentation updates.
- Release note.
- Breaking change or migration note.

Automatable checks should stay narrow:

- PR title prefix.
- Required verification workflows.
- Stale path checks such as `src/ytsum`.
- Changelog/docs required checks when high-impact files change.
- Release version consistency checks on release branches and tags.

## Issue and Project Policy

Use YAML Issue Forms for:

- bug
- feature
- spike
- architecture decision
- performance
- documentation

Use one Project board first. Recommended columns:

```text
Inbox -> Ready -> Doing -> Review -> Benchmark -> Release -> Done
```

Avoid multiple boards until there are enough contributors to justify ownership
views.

## AI Project Policy

AI-specific changes need traceability because regressions can appear as quality,
latency, cost, grounding, or provider-compatibility issues.

Track these dimensions in PRs and labels:

- prompt/schema changes;
- model or runtime selection changes;
- harness behavior changes;
- benchmark fixture changes;
- latency or retry policy changes;
- evidence grounding and citation behavior;
- provider cost or token-shape changes.

Do not run live provider benchmarks on every PR. Require benchmark discussion
only for `area:pipeline`, `area:harness`, `area:benchmark`, or
`impact:performance` changes.

## Tooling Decision

Do not adopt Release Please, semantic-release, or a large release platform yet.
They can be valuable once release mistakes repeat or multiple maintainers are
cutting releases. Today, the better ROI is:

- explicit release PRs;
- version consistency checks;
- better PR and issue templates;
- labels;
- one Project board;
- architecture and benchmark checks.

This keeps automation close to current failure modes instead of copying larger
projects prematurely.

## Scaling Assessment

| Team size | Fit | Required governance |
|---|---|---|
| 1 person | Current structure is workable but manual sync is fragile. | Version checks, labels, PR template. |
| 3 people | Missing labels, ownership, and Project state become costly. | CODEOWNERS, issue forms, required checks. |
| 10 people | Manual release discipline becomes a bottleneck. | Milestones, release manager role, release PR automation. |
| 30 people | Local conventions are not enough. | Team CODEOWNERS, stronger branch rules, ADR discipline. |
| 100 people | Repository-level practice must become org-level governance. | Org rulesets, platform ownership, dedicated release engineering. |

## Consequences

Positive:

- The repository can preserve history, decisions, release state, and benchmark
  evidence without turning `CHANGELOG.md` into a catch-all document.
- Future agents and contributors can find the right artifact quickly.
- Release failures caused by version mismatch become machine-detectable.
- Automation remains proportional to current project size.

Tradeoffs:

- Some release work remains manual by design.
- Maintainers must keep labels and issue forms useful rather than decorative.
- A release consistency workflow must be maintained as the package metadata
  evolves.

## Immediate Work Queue

The executable queue for this decision lives in `IMPROVEMENTS.md` under the
repository governance P0/P1/P2 sections. Do not duplicate that checklist here.
