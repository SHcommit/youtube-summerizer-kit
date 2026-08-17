"""Versioned task instructions used by the analysis pipeline."""

from importlib.resources import files

from chew.core.identity import fingerprint


def _prompt(name: str) -> str:
    return files("chew.templates").joinpath("prompts", name).read_text(encoding="utf-8").strip()


TOPIC_PROMPT = _prompt("topic.md")
CHAPTER_PROMPT = _prompt("chapter.md")
COMPOSE_PROMPT = _prompt("compose.md")
REPAIR_PROMPT = _prompt("repair.md")

PROMPT_FINGERPRINT = fingerprint(
    {
        "topic": TOPIC_PROMPT,
        "chapter": CHAPTER_PROMPT,
        "compose": COMPOSE_PROMPT,
        "repair": REPAIR_PROMPT,
        "version": 1,
    }
)
