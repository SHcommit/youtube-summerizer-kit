#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _tool_error(tool: str, install_hint: str) -> str:
    return f"{tool} is required to render architecture assets. Install hint: {install_hint}"


def render_architecture_assets(root: Path) -> list[str]:
    root = root.resolve()
    architecture_root = root / "assets" / "architecture"
    rendered: list[str] = []
    errors: list[str] = []

    mermaid_sources = sorted(architecture_root.rglob("*.mmd")) if architecture_root.exists() else []
    d2_sources = sorted(architecture_root.rglob("*.d2")) if architecture_root.exists() else []

    if mermaid_sources and shutil.which("mmdc") is None:
        errors.append(_tool_error("mmdc", "npm install -g @mermaid-js/mermaid-cli"))
    if d2_sources and shutil.which("d2") is None:
        errors.append(_tool_error("d2", "https://d2lang.com/tour/install"))
    if errors:
        return errors

    for source_path in mermaid_sources:
        output_path = source_path.with_suffix(".png")
        subprocess.run(["mmdc", "-i", str(source_path), "-o", str(output_path), "-b", "transparent"], check=True)
        rendered.append(str(output_path.relative_to(root)))
    for source_path in d2_sources:
        output_path = source_path.with_suffix(".png")
        subprocess.run(["d2", str(source_path), str(output_path)], check=True)
        rendered.append(str(output_path.relative_to(root)))

    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="Render architecture .mmd/.d2 sources to PNG assets.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to render.")
    args = parser.parse_args()

    result = render_architecture_assets(args.root)
    if result and any(line.endswith("install") or "required to render" in line for line in result):
        for line in result:
            print(line, file=sys.stderr)
        return 1
    for line in result:
        print(f"rendered {line}")
    if not result:
        print("no architecture sources found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
