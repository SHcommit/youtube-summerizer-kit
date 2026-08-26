from __future__ import annotations

import ast
import sys
from pathlib import Path

FORBIDDEN_IMPORTS_BY_PREFIX = {
    "src/chew/core": (
        "chew.agents",
        "chew.app",
        "chew.benchmark",
        "chew.cli",
        "chew.harness",
        "chew.interfaces",
        "chew.pipeline",
        "chew.retention",
        "chew.server",
        "chew.storage",
        "chew.transcripts",
    ),
    "src/chew/interfaces": (
        "chew.cli",
        "chew.harness",
        "chew.storage",
        "chew.transcripts",
    ),
    "src/chew/agents/contracts": (
        "chew.app",
        "chew.cli",
        "chew.harness",
        "chew.interfaces",
        "chew.pipeline",
        "chew.storage",
        "chew.transcripts",
    ),
    "src/chew/agents/policy": (
        "chew.app",
        "chew.cli",
        "chew.harness",
        "chew.interfaces",
        "chew.pipeline",
        "chew.storage",
        "chew.transcripts",
    ),
    "src/chew/agents/ports": (
        "chew.app",
        "chew.cli",
        "chew.harness",
        "chew.interfaces",
        "chew.pipeline",
        "chew.storage",
        "chew.transcripts",
    ),
}


def imported_modules(source: str) -> list[str]:
    tree = ast.parse(source)
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _rule_for(path: Path) -> tuple[str, ...]:
    normalized = path.as_posix()
    for prefix, forbidden in FORBIDDEN_IMPORTS_BY_PREFIX.items():
        if normalized.startswith(prefix):
            return forbidden
    return ()


def check_architecture(project_root: Path) -> list[str]:
    src_root = project_root / "src" / "chew"
    errors: list[str] = []
    for path in sorted(src_root.rglob("*.py")):
        relative_path = path.relative_to(project_root)
        forbidden = _rule_for(relative_path)
        if not forbidden:
            continue
        for module in imported_modules(path.read_text(encoding="utf-8")):
            if any(module == prefix or module.startswith(f"{prefix}.") for prefix in forbidden):
                errors.append(f"{relative_path.as_posix()} imports forbidden module {module}")
    return errors


def main() -> int:
    errors = check_architecture(Path.cwd())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("architecture boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
