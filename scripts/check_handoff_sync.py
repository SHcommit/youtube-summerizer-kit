#!/usr/bin/env python3
"""Check that a CHANGELOG.md [Unreleased] change is accompanied by a handoff.md update.

AGENTS.md's documentation lifecycle rule requires refreshing handoff.md's execution index (and
removing completed-history prose) whenever work is recorded in CHANGELOG.md. This is a mechanical
proxy for that rule: it cannot judge whether handoff.md was trimmed correctly, only that it was
touched in the same PR as an [Unreleased] change.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

UNRELEASED_HEADING = "## [Unreleased]"


def extract_unreleased_section(changelog_text: str) -> str:
    lines = changelog_text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.strip() == UNRELEASED_HEADING:
            start = index + 1
            break
    if start is None:
        return ""
    end = len(lines)
    for index in range(start, len(lines)):
        if lines[index].startswith("## ["):
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def check_handoff_sync(*, base_unreleased: str, head_unreleased: str, changed_files: set[str]) -> list[str]:
    if base_unreleased == head_unreleased:
        return []
    if "handoff.md" in changed_files:
        return []
    return [
        "CHANGELOG.md's [Unreleased] section changed but handoff.md was not updated in this PR. "
        "AGENTS.md's documentation lifecycle rule requires refreshing handoff.md's execution index "
        "(and trimming completed-history prose) whenever work is recorded in CHANGELOG.md."
    ]


def _run_git(args: list[str], *, root: Path) -> str:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return result.stdout


def _changed_files(root: Path, base: str, head: str) -> set[str]:
    output = _run_git(["diff", "--name-only", f"{base}...{head}"], root=root)
    return {line.strip() for line in output.splitlines() if line.strip()}


def _changelog_at(root: Path, ref: str) -> str:
    try:
        return _run_git(["show", f"{ref}:CHANGELOG.md"], root=root)
    except subprocess.CalledProcessError:
        return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that CHANGELOG.md [Unreleased] changes are accompanied by a handoff.md update."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="origin/develop")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    root = args.root.resolve()
    changed_files = _changed_files(root, args.base, args.head)
    base_unreleased = extract_unreleased_section(_changelog_at(root, args.base))
    head_unreleased = extract_unreleased_section(_changelog_at(root, args.head))

    errors = check_handoff_sync(
        base_unreleased=base_unreleased, head_unreleased=head_unreleased, changed_files=changed_files
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("handoff sync check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
