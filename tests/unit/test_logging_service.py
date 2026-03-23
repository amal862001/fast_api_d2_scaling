"""
Unit tests for services/logging_service.py

Covers:
  - configure_logging sets up JSONRenderer processor
  - get_logger returns a usable structlog logger
  - add_request_context injects request_id into every log entry
  - logger.info does not raise
"""
import pytest
import structlog
from services.logging_service import configure_logging, get_logger, add_request_context
from middleware.request_id import request_id_ctx


# ── configure_logging ─────────────────────────────────────────

def test_configure_logging_sets_json_renderer():
    """After configure_logging the processor chain must include JSONRenderer.
    Without it logs are plain text, not machine-parseable JSON."""
    configure_logging()
    config          = structlog.get_config()
    processor_names = [type(p).__name__ for p in config["processors"]]
    assert "JSONRenderer" in processor_names


def test_configure_logging_is_idempotent():
    """Calling configure_logging twice must not raise or break anything."""
    configure_logging()
    configure_logging()
    logger = get_logger("idempotent_test")
    assert logger is not None


# ── get_logger ────────────────────────────────────────────────

def test_get_logger_returns_logger():
    """get_logger must return a non-None structlog logger instance."""
    configure_logging()
    assert get_logger("test") is not None


def test_get_logger_different_names_return_loggers():
    """Named loggers for different modules must all be valid."""
    configure_logging()
    for name in ("main", "auth", "complaints", "worker"):
        assert get_logger(name) is not None


def test_logger_info_does_not_raise():
    """logger.info must never raise — a broken logger silences all observability."""
    configure_logging()
    logger = get_logger("test")
    try:
        logger.info("test_event", key="value", count=42)
    except Exception:
        pytest.fail("logger.info raised an exception")


def test_logger_accepts_arbitrary_kwargs():
    """Structured log entries with any extra kwargs must not raise."""
    configure_logging()
    logger = get_logger("test")
    try:
        logger.info("event", user_id=1, agency="NYPD", endpoint="/complaints")
    except Exception:
        pytest.fail("logger.info raised with kwargs")


# ── add_request_context ───────────────────────────────────────

def test_add_request_context_injects_request_id():
    """Processor must inject the current request_id into every log entry."""
    request_id_ctx.set("test-uuid-1234")
    event_dict = {"event": "test_log"}
    result     = add_request_context(None, None, event_dict)
    assert result["request_id"] == "test-uuid-1234"


def test_add_request_context_empty_when_no_request():
    """When no request is active the field must be an empty string, not missing."""
    request_id_ctx.set("")
    event_dict = {"event": "startup"}
    result     = add_request_context(None, None, event_dict)
    assert "request_id" in result
    assert result["request_id"] == ""


def test_add_request_context_updates_with_new_id():
    """Each new request sets a new ID — the processor must reflect the latest value."""
    request_id_ctx.set("first-id")
    r1 = add_request_context(None, None, {"event": "e1"})

    request_id_ctx.set("second-id")
    r2 = add_request_context(None, None, {"event": "e2"})

    assert r1["request_id"] == "first-id"
    assert r2["request_id"] == "second-id"


def test_add_request_context_preserves_existing_fields():
    """The processor must not drop any existing fields from the event dict."""
    request_id_ctx.set("some-id")
    event_dict = {"event": "my_event", "user_id": 42, "agency": "NYPD"}
    result     = add_request_context(None, None, event_dict)
    assert result["event"]   == "my_event"
    assert result["user_id"] == 42
    assert result["agency"]  == "NYPD"
