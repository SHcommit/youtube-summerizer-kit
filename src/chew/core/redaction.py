"""Small, deterministic redaction helpers for persisted operational metadata."""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|authorization|password|secret|token)", re.IGNORECASE)
REDACTED = "[REDACTED]"


def redact_sensitive(value: Any, *, key: str | None = None) -> Any:
    """Redact values under sensitive keys while preserving safe operational metadata."""

    if key is not None and _SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(child_key): redact_sensitive(child, key=str(child_key)) for child_key, child in value.items()}
    if isinstance(value, list):
        return [redact_sensitive(child) for child in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(child) for child in value)
    return value
