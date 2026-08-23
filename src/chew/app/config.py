"""Markdown-based user configuration."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ConfigurationError(ValueError):
    """An actionable error in YTSUM.md or an output profile."""


class Settings(BaseModel):
    """Merged project and output-profile settings."""

    model_config = ConfigDict(extra="forbid")

    language: str = "ko"
    default_profile: str = "digest"
    depth: Literal["brief", "short", "quick", "concise", "detailed", "deep"] = "detailed"
    runtime: str = "frontier"
    task_runtimes: dict[str, str] = Field(default_factory=dict)
    local_accelerator: bool = False
    ollama_model: str | None = None
    whisper_fallback: bool = False
    max_input_tokens: int | None = Field(default=None, gt=0)
    reserved_output_tokens: int = Field(default=0, ge=0)
    output_verify: bool = True
    normalize_transcript: bool = False
    preprocess_transcript: bool = False
    storage_policy: Literal["compact", "private", "archive"] = "compact"
    instructions: str = ""


def discover_config(start: Path) -> Path | None:
    """Find the nearest CHEW.md or YTSUM.md from *start* upward."""

    current = start.resolve()
    if current.is_file():
        current = current.parent
    for directory in (current, *current.parents):
        for name in ("CHEW.md", "YTSUM.md"):
            candidate = directory / name
            if candidate.is_file():
                return candidate
    return None


def _parse_markdown(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text.strip()
    closing = text.find("\n---\n", 4)
    if closing == -1:
        raise ConfigurationError(f"Unclosed YAML front matter: {path}")
    try:
        raw_metadata = yaml.safe_load(text[4:closing]) or {}
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML front matter: {path}: {error}") from error
    if not isinstance(raw_metadata, dict):
        raise ConfigurationError(f"YAML front matter must be a mapping: {path}")
    return raw_metadata, text[closing + 5 :].strip()


def _template(name: str) -> Path:
    target = Path(str(files("chew.templates").joinpath(name)))
    if not target.exists() and name == "YTSUM.md":
        target = Path(str(files("chew.templates").joinpath("CHEW.md")))
    return target


def _merge(settings: Settings, path: Path) -> Settings:
    metadata, body = _parse_markdown(path)
    update = dict(metadata)
    prior = settings.instructions.strip()
    update["instructions"] = "\n\n".join(part for part in (prior, body) if part)
    return settings.model_copy(update=update)


def load_settings(start: Path, profile: str | None) -> Settings:
    """Load packaged defaults, project defaults, then a purpose profile."""

    template_file = "CHEW.md" if _template("CHEW.md").exists() else "YTSUM.md"
    settings = _merge(Settings(), _template(template_file))
    project_config = discover_config(start)
    if project_config is not None:
        settings = _merge(settings, project_config)

    selected_profile = profile
    if selected_profile is not None:
        project_profile = (
            project_config.parent / ".chew" / "profiles" / f"{selected_profile}.md"
            if project_config is not None
            else None
        )
        profile_path = (
            project_profile
            if project_profile is not None and project_profile.is_file()
            else _template(f"profiles/{selected_profile}.md")
        )
        settings = _merge(settings, profile_path)
    try:
        return Settings.model_validate(settings.model_dump())
    except ValidationError as error:
        raise ConfigurationError(f"Invalid configuration: {error}") from error
