# CI Failure Analysis — Missing Server Dependencies

**Date:** 2026-08-21

**Affected workflow:** `CI & AI Harness Monitor`
**Failed run:** `32390082581` on `develop` (2026-08-20 16:06 UTC)

## Executive summary

Every push to `develop` triggered a CI failure email because the type-checking
job ran `mypy src/chew` without installing the optional dependencies used by
modules inside that source tree. The application code was not failing at
runtime; the CI environment was incomplete for the scope it was asked to
check.

## What failed

The Python 3.13 CI job failed during `mypy src/chew` with six errors:

| Module | Missing dependency | Result |
| --- | --- | --- |
| `chew.server` | `fastapi`, `fastapi.responses` | imports could not be resolved; route decorators became untyped |
| `chew.cli.main` | `uvicorn` | import could not be resolved; an existing type-ignore then became unused |

The workflow installed `.[youtube,dev,telemetry]`, while `fastapi` and
`uvicorn` are declared in the project's existing `server` optional-dependency
group. Because mypy checks all of `src/chew`, it must be given the dependencies
for every checked module.

## Root cause

The checked source scope and installed dependency scope diverged:

```text
mypy target:       src/chew  (includes server.py and CLI server command)
CI dependencies:   youtube + dev + telemetry
required addition: server (fastapi + uvicorn)
```

The release workflow used the same incomplete installation command, so a future
tagged release could have failed in the same way.

## Improvement

Both CI and release verification now install:

```bash
pip install build '.[youtube,dev,telemetry,server]'
```

This keeps the environment aligned with the static-analysis scope. No runtime
dependency was added for regular users: `server` remains an optional package
extra and is installed only inside the validation workflows.

## Verification

The corrected dependency set was used to run the project's full local
verification suite:

| Check | Result |
| --- | --- |
| `mypy src/chew` | 57 source files, no issues |
| `ruff check .` | passed |
| `pytest -q` | 193 passed, 2 intentionally skipped |
| `python -m build` | source distribution and wheel built |

The GitHub Actions run triggered after merge is the final external confirmation
for the Python 3.12 and 3.13 matrix. Once that run is green, future pushes no
longer create this particular failure email.

## Prevention

- Treat the CI install command as the dependency contract for `mypy src/chew`.
- Whenever a new optional module is included under the mypy target, add its
  extra to CI and CD—or narrow the mypy target deliberately.
- Keep CI and CD installation commands identical when they run the same
  verification suite.
