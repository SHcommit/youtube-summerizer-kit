from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_docs_sync.py"


def load_docs_sync_checker():
    spec = importlib.util.spec_from_file_location("check_docs_sync", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_file(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_docs_sync_accepts_current_repository() -> None:
    checker = load_docs_sync_checker()

    errors = checker.check_docs_sync(REPO_ROOT)

    assert errors == []


def test_docs_sync_reports_missing_readme_architecture_asset(tmp_path: Path) -> None:
    checker = load_docs_sync_checker()
    write_file(tmp_path, "README.md", "![Flow](assets/architecture/en/missing.png)\n")
    write_file(tmp_path, "README.ko.md", "![흐름](assets/architecture/ko/user-flow.png)\n")
    write_file(tmp_path, "assets/architecture/ko/user-flow.png", "png")
    write_file(tmp_path, "docs/agent-index.md", "| English | Korean | What it does |\n")
    write_file(tmp_path, "src/chew/cli/main.py", "")

    errors = checker.check_docs_sync(tmp_path)

    assert errors == ["README.md references missing architecture asset: assets/architecture/en/missing.png"]


def test_docs_sync_reports_missing_rendered_architecture_png(tmp_path: Path) -> None:
    checker = load_docs_sync_checker()
    write_file(tmp_path, "README.md", "")
    write_file(tmp_path, "README.ko.md", "")
    write_file(tmp_path, "assets/architecture/en/user-flow.mmd", "graph TD\n")
    write_file(tmp_path, "docs/agent-index.md", "| English | Korean | What it does |\n")
    write_file(tmp_path, "src/chew/cli/main.py", "")

    errors = checker.check_docs_sync(tmp_path)

    assert errors == ["assets/architecture/en/user-flow.mmd has no rendered PNG: assets/architecture/en/user-flow.png"]


def test_docs_sync_reports_visible_cli_command_missing_from_agent_index(tmp_path: Path) -> None:
    checker = load_docs_sync_checker()
    write_file(tmp_path, "README.md", "")
    write_file(tmp_path, "README.ko.md", "")
    write_file(
        tmp_path,
        "docs/agent-index.md",
        "| English | Korean | What it does |\n|---|---|---|\n| `summarize` | `요약` | Digest |\n",
    )
    write_file(
        tmp_path,
        "src/chew/cli/main.py",
        'app.command("summarize", help="Create a digest.")(summarize)\n'
        'app.command("요약", hidden=True)(summarize)\n'
        'app.command("doctor", help="Diagnose runtimes.")(doctor)\n',
    )

    errors = checker.check_docs_sync(tmp_path)

    assert errors == ["docs/agent-index.md CLI command table is missing visible command: doctor"]
