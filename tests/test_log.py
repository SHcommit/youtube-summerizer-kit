from __future__ import annotations

import json
import logging

from chew.log import JsonFormatter, configure_logging, get_logger, job_id_var, run_id_var


def test_json_formatter_emits_valid_json() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="chew.test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["event"] == "hello"
    assert "timestamp" in parsed
    assert parsed["logger"] == "chew.test"


def test_json_formatter_includes_context_vars() -> None:
    formatter = JsonFormatter()
    token_r = run_id_var.set("run-abc")
    token_j = job_id_var.set("job-xyz")
    try:
        record = logging.LogRecord(
            name="chew.scheduler", level=logging.INFO, pathname="", lineno=0,
            msg="job done", args=(), exc_info=None,
        )
        parsed = json.loads(formatter.format(record))
        assert parsed["run_id"] == "run-abc"
        assert parsed["job_id"] == "job-xyz"
    finally:
        run_id_var.reset(token_r)
        job_id_var.reset(token_j)


def test_json_formatter_includes_extra_fields() -> None:
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="chew.harness", level=logging.INFO, pathname="", lineno=0,
        msg="generate complete", args=(), exc_info=None,
    )
    record.__dict__["latency_ms"] = 420
    record.__dict__["model"] = "qwen3:8b"
    parsed = json.loads(formatter.format(record))
    assert parsed["latency_ms"] == 420
    assert parsed["model"] == "qwen3:8b"


def test_configure_logging_is_idempotent() -> None:
    configure_logging(level="WARNING")
    configure_logging(level="WARNING")
    root = logging.getLogger()
    json_handlers = [h for h in root.handlers if isinstance(h.formatter, JsonFormatter)]
    assert len(json_handlers) <= 1


def test_get_logger_returns_standard_logger() -> None:
    logger = get_logger("chew.test.module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "chew.test.module"
