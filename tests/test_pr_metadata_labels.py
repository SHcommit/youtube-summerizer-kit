from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "pr_metadata_labels.py"


def load_labeler():
    spec = importlib.util.spec_from_file_location("pr_metadata_labels", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_metadata_labels_use_pr_title_prefix_first() -> None:
    labeler = load_labeler()

    labels = labeler.labels_for_pr(title="fix: repair transcript timeout", head_ref="feature/123-timeout")

    assert labels == ["kind:bug", "status:needs-triage"]


def test_metadata_labels_fall_back_to_branch_prefix() -> None:
    labeler = load_labeler()

    labels = labeler.labels_for_pr(title="Repair transcript timeout", head_ref="fix/123-timeout")

    assert labels == ["kind:bug", "status:needs-triage"]


def test_metadata_labels_map_documentation_and_spike_work() -> None:
    labeler = load_labeler()

    assert labeler.labels_for_pr(title="docs: update release guide", head_ref="feature/123-docs") == [
        "kind:docs",
        "status:needs-triage",
    ]
    assert labeler.labels_for_pr(title="Research release tooling", head_ref="spike/release-tooling") == [
        "kind:spike",
        "status:needs-triage",
    ]


def test_metadata_labels_do_not_guess_unknown_kind() -> None:
    labeler = load_labeler()

    labels = labeler.labels_for_pr(title="update wording", head_ref="topic/wording")

    assert labels == ["status:needs-triage"]
