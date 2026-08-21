"""Log configuration.

The assertions here are about output an operator depends on: one line per
request, no duplicates, and JSON wherever something machine-readable will
consume it.
"""

import json
import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logging_config import configure_logging
from app.main import create_app
from app.settings import Environment
from tests.support import build_settings

_URL = "postgresql+psycopg://tbs:tbs@localhost:5432/tbs"


def test_uvicorn_loggers_are_rerouted_through_the_configured_handler() -> None:
    """Otherwise production interleaves JSON with unstructured framework lines."""
    configure_logging(json_logs=True, level="INFO")

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        assert logger.handlers == []
        assert logger.propagate is True


def test_uvicorn_access_log_is_silenced() -> None:
    """AccessLogMiddleware replaces it, and two access lines per request is worse
    than either one alone: an aggregator counts every request twice.
    """
    configure_logging(json_logs=True, level="INFO")

    access = logging.getLogger("uvicorn.access")
    assert access.handlers == []
    assert access.propagate is False


def test_exactly_one_access_line_per_request(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        client.get("/api/health")

    lines = [
        record
        for record in caplog.records
        if isinstance(record.msg, dict) and record.msg["event"] == "request.completed"
    ]
    assert len(lines) == 1


def test_reconfiguring_does_not_stack_handlers() -> None:
    """The factory runs once per test; handlers must not accumulate."""
    configure_logging(json_logs=True, level="INFO")
    before = len(logging.getLogger().handlers)

    configure_logging(json_logs=True, level="INFO")

    assert len(logging.getLogger().handlers) == before


def test_production_renders_json(capsys: pytest.CaptureFixture[str]) -> None:
    """A log aggregator cannot parse the console renderer's output."""
    settings = build_settings(environment=Environment.PRODUCTION, database_url=_URL)
    create_app(settings)

    logging.getLogger("app.test").info("probe", extra={"marker": "x"})

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured
    parsed = json.loads(captured[-1])
    assert parsed["event"] == "probe"
    assert parsed["level"] == "info"


def test_development_renders_for_humans(capsys: pytest.CaptureFixture[str]) -> None:
    settings = build_settings(environment=Environment.DEVELOPMENT, database_url=_URL)
    create_app(settings)

    logging.getLogger("app.test").info("probe")

    captured = capsys.readouterr().out.strip()
    assert "probe" in captured
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.splitlines()[-1])


def test_the_factory_configures_logging_from_settings(app: FastAPI) -> None:
    """Building an application is what installs the handler."""
    assert app.title == "Ticket Booking System"
    assert any(handler.get_name() == "tbs.console" for handler in logging.getLogger().handlers)
