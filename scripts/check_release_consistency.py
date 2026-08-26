from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

VERSION_HEADING_RE = re.compile(r"^## \[(?P<version>\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$", re.MULTILINE)
RELEASE_BRANCH_RE = re.compile(r"^(?:refs/heads/)?release/v(?P<version>\d+\.\d+\.\d+)$")
TAG_RE = re.compile(r"^(?:refs/tags/)?v(?P<version>\d+\.\d+\.\d+)$")
INIT_VERSION_RE = re.compile(r'^__version__\s*=\s*"(?P<version>\d+\.\d+\.\d+)"\s*$', re.MULTILINE)


def read_project_version(project_root: Path) -> str:
    pyproject_path = project_root / "pyproject.toml"
    with pyproject_path.open("rb") as file:
        pyproject = tomllib.load(file)
    version = pyproject.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise ValueError("pyproject.toml is missing [project].version")
    return version


def changelog_versions(project_root: Path) -> set[str]:
    changelog = (project_root / "CHANGELOG.md").read_text(encoding="utf-8")
    return {match.group("version") for match in VERSION_HEADING_RE.finditer(changelog)}


def read_init_version(project_root: Path) -> str | None:
    init_path = project_root / "src" / "chew" / "__init__.py"
    if not init_path.is_file():
        return None
    match = INIT_VERSION_RE.search(init_path.read_text(encoding="utf-8"))
    return match.group("version") if match else None


def _version_from_tag(tag: str) -> str | None:
    match = TAG_RE.match(tag)
    return match.group("version") if match else None


def _version_from_release_branch(branch: str) -> str | None:
    match = RELEASE_BRANCH_RE.match(branch)
    return match.group("version") if match else None


def check_release_consistency(project_root: Path, tag: str | None, branch: str | None) -> list[str]:
    version = read_project_version(project_root)
    versions = changelog_versions(project_root)
    errors: list[str] = []

    if tag:
        tag_version = _version_from_tag(tag)
        if tag_version is None:
            errors.append(f"release tag must match vX.Y.Z, got {tag}")
        elif tag_version != version:
            errors.append(f"tag {tag} does not match pyproject.toml version {version}")

    if branch:
        branch_version = _version_from_release_branch(branch)
        if branch_version is not None and branch_version != version:
            errors.append(f"release branch {branch} does not match pyproject.toml version {version}")

    if version not in versions:
        errors.append(f"CHANGELOG.md is missing heading for version {version}")

    init_version = read_init_version(project_root)
    if init_version is None:
        errors.append("src/chew/__init__.py is missing a __version__ = \"X.Y.Z\" line")
    elif init_version != version:
        errors.append(
            f"src/chew/__init__.py __version__ {init_version} does not match "
            f"pyproject.toml version {version}"
        )

    return errors


def _default_tag() -> str | None:
    ref = os.environ.get("GITHUB_REF", "")
    return ref if ref.startswith("refs/tags/") else None


def _default_branch() -> str | None:
    head_ref = os.environ.get("GITHUB_HEAD_REF", "")
    if head_ref:
        return head_ref
    ref = os.environ.get("GITHUB_REF", "")
    return ref if ref.startswith("refs/heads/") else None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate release version consistency.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--tag", default=_default_tag())
    parser.add_argument("--branch", default=_default_branch())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    errors = check_release_consistency(args.project_root, args.tag, args.branch)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("release version consistency check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
