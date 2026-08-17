from pathlib import Path

import pytest

from chew.config import ConfigurationError, discover_config, load_settings


def test_discover_config_walks_up_to_project_root(tmp_path: Path) -> None:
    nested = tmp_path / "notes" / "backend"
    nested.mkdir(parents=True)
    config = tmp_path / "CHEW.md"
    config.write_text("# 공통 설정\n", encoding="utf-8")

    assert discover_config(nested) == config


def test_profile_overrides_project_default(tmp_path: Path) -> None:
    (tmp_path / "CHEW.md").write_text(
        "---\nlanguage: ko\ndepth: detailed\n---\n공통 톤",
        encoding="utf-8",
    )
    profiles = tmp_path / ".chew" / "profiles"
    profiles.mkdir(parents=True)
    (profiles / "blog.md").write_text(
        "---\ndepth: concise\n---\n블로그 톤",
        encoding="utf-8",
    )

    settings = load_settings(tmp_path, "blog")

    assert settings.language == "ko"
    assert settings.depth == "concise"
    assert "공통 톤" in settings.instructions
    assert "블로그 톤" in settings.instructions


def test_missing_config_uses_packaged_defaults(tmp_path: Path) -> None:
    settings = load_settings(tmp_path, None)

    assert settings.language == "ko"
    assert settings.default_profile == "digest"
    assert settings.storage_policy == "compact"
    assert settings.whisper_fallback is False
    assert settings.instructions


def test_project_can_explicitly_enable_optional_whisper_fallback(tmp_path: Path) -> None:
    (tmp_path / "CHEW.md").write_text("---\nwhisper_fallback: true\n---\n", encoding="utf-8")

    assert load_settings(tmp_path, None).whisper_fallback is True


def test_invalid_markdown_configuration_has_an_actionable_error(tmp_path: Path) -> None:
    (tmp_path / "CHEW.md").write_text("---\nruntime: [\n---\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="Invalid YAML front matter"):
        load_settings(tmp_path, None)
