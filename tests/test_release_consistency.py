from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_release_consistency.py"


def load_release_checker():
    spec = importlib.util.spec_from_file_location("check_release_consistency", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_release_fixture(root: Path, *, version: str = "0.2.0", changelog_version: str = "0.2.0") -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "youtube-summarizer-kit"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n## [{changelog_version}] - 2026-08-25\n",
        encoding="utf-8",
    )


def test_release_consistency_accepts_matching_tag_branch_and_changelog(tmp_path: Path) -> None:
    checker = load_release_checker()
    write_release_fixture(tmp_path)

    errors = checker.check_release_consistency(tmp_path, tag="v0.2.0", branch="release/v0.2.0")

    assert errors == []


def test_release_consistency_reports_tag_version_mismatch(tmp_path: Path) -> None:
    checker = load_release_checker()
    write_release_fixture(tmp_path, version="0.2.0")

    errors = checker.check_release_consistency(tmp_path, tag="v0.2.1", branch=None)

    assert errors == ["tag v0.2.1 does not match pyproject.toml version 0.2.0"]


def test_release_consistency_reports_release_branch_version_mismatch(tmp_path: Path) -> None:
    checker = load_release_checker()
    write_release_fixture(tmp_path, version="0.2.0")

    errors = checker.check_release_consistency(tmp_path, tag=None, branch="release/v0.3.0")

    assert errors == ["release branch release/v0.3.0 does not match pyproject.toml version 0.2.0"]


def test_release_consistency_reports_missing_changelog_heading(tmp_path: Path) -> None:
    checker = load_release_checker()
    write_release_fixture(tmp_path, version="0.2.0", changelog_version="0.1.2")

    errors = checker.check_release_consistency(tmp_path, tag="v0.2.0", branch=None)

    assert errors == ["CHANGELOG.md is missing heading for version 0.2.0"]
