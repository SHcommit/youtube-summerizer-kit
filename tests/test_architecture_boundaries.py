from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_architecture.py"


def load_architecture_checker():
    spec = importlib.util.spec_from_file_location("check_architecture", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_module(root: Path, relative_path: str, source: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_architecture_checker_accepts_allowed_imports(tmp_path: Path) -> None:
    checker = load_architecture_checker()
    write_module(tmp_path, "src/chew/core/models.py", "from chew.core.identity import fingerprint\n")
    write_module(tmp_path, "src/chew/interfaces/presenters/command.py", "from chew.app.service import CommandResult\n")
    write_module(tmp_path, "src/chew/agents/policy/authorization.py", "from chew.agents.contracts import ToolGrant\n")

    errors = checker.check_architecture(tmp_path)

    assert errors == []


def test_architecture_checker_rejects_core_importing_pipeline(tmp_path: Path) -> None:
    checker = load_architecture_checker()
    write_module(tmp_path, "src/chew/core/models.py", "from chew.pipeline.engine import Engine\n")

    errors = checker.check_architecture(tmp_path)

    assert errors == ["src/chew/core/models.py imports forbidden module chew.pipeline.engine"]


def test_architecture_checker_rejects_interfaces_importing_adapters(tmp_path: Path) -> None:
    checker = load_architecture_checker()
    write_module(tmp_path, "src/chew/interfaces/http/routes.py", "from chew.storage.database import Database\n")

    errors = checker.check_architecture(tmp_path)

    assert errors == ["src/chew/interfaces/http/routes.py imports forbidden module chew.storage.database"]


def test_architecture_checker_rejects_agent_policy_importing_pipeline(tmp_path: Path) -> None:
    checker = load_architecture_checker()
    write_module(tmp_path, "src/chew/agents/policy/authorization.py", "import chew.pipeline.engine\n")

    errors = checker.check_architecture(tmp_path)

    assert errors == ["src/chew/agents/policy/authorization.py imports forbidden module chew.pipeline.engine"]
