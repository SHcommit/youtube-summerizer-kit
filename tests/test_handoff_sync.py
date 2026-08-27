from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_handoff_sync.py"


def load_handoff_sync_checker():
    spec = importlib.util.spec_from_file_location("check_handoff_sync", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_unreleased_section_returns_text_between_headings() -> None:
    checker = load_handoff_sync_checker()
    changelog = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "### Added\n- new thing\n\n"
        "## [0.3.1] - 2026-08-27\n\n"
        "### Added\n- old thing\n"
    )

    section = checker.extract_unreleased_section(changelog)

    assert section == "### Added\n- new thing"


def test_extract_unreleased_section_returns_empty_string_when_heading_missing() -> None:
    checker = load_handoff_sync_checker()

    assert checker.extract_unreleased_section("# Changelog\n\n## [0.3.1] - 2026-08-27\n") == ""


def test_passes_when_unreleased_section_is_unchanged() -> None:
    checker = load_handoff_sync_checker()

    errors = checker.check_handoff_sync(
        base_unreleased="### Added\n- existing",
        head_unreleased="### Added\n- existing",
        changed_files={"src/chew/pipeline/engine.py"},
    )

    assert errors == []


def test_passes_when_unreleased_section_changed_and_handoff_was_touched() -> None:
    checker = load_handoff_sync_checker()

    errors = checker.check_handoff_sync(
        base_unreleased="### Added\n- old",
        head_unreleased="### Added\n- old\n- new",
        changed_files={"CHANGELOG.md", "handoff.md"},
    )

    assert errors == []


def test_fails_when_unreleased_section_changed_without_touching_handoff() -> None:
    checker = load_handoff_sync_checker()

    errors = checker.check_handoff_sync(
        base_unreleased="### Added\n- old",
        head_unreleased="### Added\n- old\n- new",
        changed_files={"CHANGELOG.md"},
    )

    assert len(errors) == 1
    assert "handoff.md" in errors[0]
