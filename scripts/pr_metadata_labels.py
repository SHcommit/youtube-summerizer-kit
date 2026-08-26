from __future__ import annotations

import argparse
import re
import sys

TITLE_PREFIX_LABELS = {
    "feat": "kind:feature",
    "fix": "kind:bug",
    "docs": "kind:docs",
    "refactor": "kind:refactor",
    "bench": "knowledge:benchmark",
    "ci": "area:ci",
}
BRANCH_PREFIX_LABELS = {
    "feature": "kind:feature",
    "feat": "kind:feature",
    "fix": "kind:bug",
    "docs": "kind:docs",
    "refactor": "kind:refactor",
    "bench": "knowledge:benchmark",
    "ci": "area:ci",
    "spike": "kind:spike",
}
TITLE_PREFIX_RE = re.compile(r"^(?P<prefix>[a-z]+)(?:\([^)]+\))?:")


def _append_unique(labels: list[str], label: str) -> None:
    if label not in labels:
        labels.append(label)


def labels_for_pr(title: str, head_ref: str) -> list[str]:
    labels: list[str] = []

    title_match = TITLE_PREFIX_RE.match(title.strip().lower())
    if title_match:
        label = TITLE_PREFIX_LABELS.get(title_match.group("prefix"))
        if label:
            _append_unique(labels, label)

    if not any(label.startswith("kind:") for label in labels):
        branch_prefix = head_ref.split("/", 1)[0].lower()
        label = BRANCH_PREFIX_LABELS.get(branch_prefix)
        if label:
            _append_unique(labels, label)

    _append_unique(labels, "status:needs-triage")
    return labels


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print metadata labels for a pull request.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--head-ref", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    for label in labels_for_pr(title=args.title, head_ref=args.head_ref):
        print(label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
