#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ARCHITECTURE_IMAGE_RE = re.compile(r"!\[[^\]]*]\((assets/architecture/[^)\s]+)\)")
VISIBLE_APP_COMMAND_RE = re.compile(r"""app\.command\(["']([^"']+)["'](?P<options>[^)]*)\)""")
VISIBLE_TYPER_RE = re.compile(r"""app\.add_typer\([^,\n]+,\s*name=["']([^"']+)["'](?P<options>[^)]*)\)""")
DYNAMIC_COMMAND_TUPLE_RE = re.compile(r"""\(["']([^"']+)["'],\s*["'][^"']+["'],\s*["'][^"']+["'],""")
BACKTICK_RE = re.compile(r"`([^`]+)`")


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _is_hidden_registration(options: str) -> bool:
    return "hidden=True" in options.replace(" ", "")


def _visible_cli_commands(cli_source: str) -> set[str]:
    commands: set[str] = set()
    for line in cli_source.splitlines():
        match = VISIBLE_APP_COMMAND_RE.search(line)
        if match is None:
            continue
        name = match.group(1)
        options = match.group("options")
        if not _is_hidden_registration(options):
            commands.add(name)
    for line in cli_source.splitlines():
        match = VISIBLE_TYPER_RE.search(line)
        if match is None:
            continue
        name = match.group(1)
        options = match.group("options")
        if not _is_hidden_registration(options):
            commands.add(name)
    in_dynamic_command_block = False
    for line in cli_source.splitlines():
        if line.startswith("for english, korean, help_text, command in ("):
            in_dynamic_command_block = True
            continue
        if in_dynamic_command_block and line.startswith("):"):
            in_dynamic_command_block = False
            continue
        if not in_dynamic_command_block:
            continue
        match = DYNAMIC_COMMAND_TUPLE_RE.search(line)
        if match is not None:
            commands.add(match.group(1))
    return commands


def _documented_cli_commands(agent_index: str) -> set[str]:
    in_cli_table = False
    commands: set[str] = set()
    for line in agent_index.splitlines():
        if line.startswith("## 6. "):
            break
        if line.startswith("| English | Korean | What it does |"):
            in_cli_table = True
            continue
        if not in_cli_table or not line.startswith("|"):
            continue
        for value in BACKTICK_RE.findall(line):
            commands.add(value)
    return commands


def _check_readme_architecture_links(root: Path) -> list[str]:
    errors: list[str] = []
    for readme_name in ("README.md", "README.ko.md"):
        readme_path = root / readme_name
        for relative_link in ARCHITECTURE_IMAGE_RE.findall(_read_text(readme_path)):
            if not (root / relative_link).is_file():
                errors.append(f"{readme_name} references missing architecture asset: {relative_link}")
    return errors


def _check_rendered_architecture_assets(root: Path) -> list[str]:
    errors: list[str] = []
    architecture_root = root / "assets" / "architecture"
    if not architecture_root.exists():
        return errors
    for source_path in sorted([*architecture_root.rglob("*.mmd"), *architecture_root.rglob("*.d2")]):
        png_path = source_path.with_suffix(".png")
        if not png_path.is_file():
            errors.append(
                f"{source_path.relative_to(root)} has no rendered PNG: {png_path.relative_to(root)}"
            )
    return errors


def _check_agent_index_cli_table(root: Path) -> list[str]:
    cli_source = _read_text(root / "src" / "chew" / "cli" / "main.py")
    agent_index = _read_text(root / "docs" / "agent-index.md")
    documented = _documented_cli_commands(agent_index)
    errors: list[str] = []
    for command in sorted(_visible_cli_commands(cli_source) - documented):
        errors.append(f"docs/agent-index.md CLI command table is missing visible command: {command}")
    return errors


def check_docs_sync(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    errors.extend(_check_readme_architecture_links(root))
    errors.extend(_check_rendered_architecture_assets(root))
    errors.extend(_check_agent_index_cli_table(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check README, architecture asset, and agent-index documentation sync."
    )
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to check.")
    args = parser.parse_args()

    errors = check_docs_sync(args.root)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("docs sync check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
