"""JSON structured logging for youtube-summarizer-kit.

Usage in any module:
    import logging
    from chew.log import run_id_var, job_id_var

    logger = logging.getLogger(__name__)

    token = run_id_var.set("run-123")
    try:
        logger.info("job_completed", extra={"latency_ms": 420})
    finally:
        run_id_var.reset(token)
"""

from __future__ import annotations

import contextvars
import json
import logging
import time

from chew.core.redaction import redact_sensitive

run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="")
job_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("job_id", default="")

_BUILTIN_ATTRS = frozenset(
    {
        "args", "created", "exc_info", "exc_text", "filename", "funcName",
        "levelname", "levelno", "lineno", "message", "module", "msecs",
        "msg", "name", "pathname", "process", "processName", "relativeCreated",
        "stack_info", "thread", "threadName", "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        payload: dict[str, object] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "event": record.message,
            "run_id": run_id_var.get(),
            "job_id": job_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _BUILTIN_ATTRS and not key.startswith("_"):
                payload[key] = redact_sensitive(value, key=key)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON output. Safe to call multiple times."""
    root = logging.getLogger()
    if any(isinstance(h.formatter, JsonFormatter) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    """Return a standard Logger. Call configure_logging() first."""
    return logging.getLogger(name)
