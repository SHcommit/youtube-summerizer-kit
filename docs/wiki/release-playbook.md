# Release Playbook

This playbook keeps package version, release branch, git tag, GitHub Release,
`CHANGELOG.md`, and release verification aligned.

## Release Flow

```text
develop -> release/vX.Y.Z -> master -> tag vX.Y.Z -> GitHub Release/PyPI
```

## Prepare the Release Branch

1. Create `release/vX.Y.Z` from `develop`.
2. Set `pyproject.toml` `[project].version` to `X.Y.Z`.
3. Move completed release notes from `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD`.
4. Update `reports/BENCHMARK.md` when the release includes benchmark-sensitive pipeline,
   harness, scheduler, segmentation, or runtime changes.
5. Run:

```bash
uv run python scripts/check_release_consistency.py --branch release/vX.Y.Z
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src/chew
```

## Release PR

Open the release PR from `release/vX.Y.Z` to `master`. The PR must explain:

- version being released;
- user-facing changes;
- migration or breaking changes;
- benchmark report path or why benchmark is not required;
- verification results.

## GitHub Release Notes

GitHub generated release notes use `.github/release.yml` to group merged PRs by
labels. Before tagging, keep the release PR labels accurate enough for the
generated sections:

- `impact:user-facing`, `kind:feature`, `kind:bug` for user-visible changes;
- `impact:architecture`, `area:harness`, `area:agents`, `knowledge:adr` for
  architecture and AI runtime changes;
- `impact:performance`, `area:benchmark`, `knowledge:benchmark` for performance
  evidence;
- `area:release`, `area:ci`, `dependencies`, `github_actions` for release and
  repository operations.

The generated PR list is not the whole release note. Add a short curated
summary to the GitHub Release body when the release includes migration,
benchmark, architecture, or operational decisions.

## Tag and Publish

After the release PR is merged to `master`, tag the exact merged commit:

```bash
uv run python scripts/check_release_consistency.py --tag vX.Y.Z
git tag vX.Y.Z
git push origin master --tags
```

The CD workflow verifies version consistency again before build, smoke test,
GitHub Release creation, and optional PyPI publishing.

## After Release

1. Confirm the GitHub Release exists and includes the built artifacts.
2. Confirm the package version matches `pyproject.toml`.
3. Merge or forward-port release metadata back to `develop` if needed.
4. Leave `## [Unreleased]` ready for the next development cycle.

## Repository Automation Notes

`Project Triage` can add new issues and pull requests to the user-level
`youtube-summarizer-kit Engineering` Project. GitHub's default repository token
may not have enough permission to write a user Project, so the workflow is
intentionally optional:

- create a repository secret named `PROJECTS_TOKEN` with permission to update
  the user Project to enable auto-add;
- leave the secret unset to keep Project triage manual without failing CI.
