"""Correlation ID propagation."""

import asyncio
import logging
from typing import Any

import httpx2 as httpx
import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.request_context import REQUEST_ID_HEADER


def _events(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    """structlog puts the event dict on the record before formatting."""
    return [record.msg for record in caplog.records if isinstance(record.msg, dict)]


def test_generated_when_the_client_sends_none(client: TestClient) -> None:
    response = client.get("/api/health")

    request_id = response.headers[REQUEST_ID_HEADER]
    assert len(request_id) == 32
    assert request_id.isalnum()


def test_two_requests_get_different_ids(client: TestClient) -> None:
    first = client.get("/api/health").headers[REQUEST_ID_HEADER]
    second = client.get("/api/health").headers[REQUEST_ID_HEADER]

    assert first != second


def test_a_well_formed_client_id_is_honoured(client: TestClient) -> None:
    """A trace started upstream survives into this process."""
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "edge-proxy-abc123"})

    assert response.headers[REQUEST_ID_HEADER] == "edge-proxy-abc123"


@pytest.mark.parametrize(
    "hostile",
    [
        "short",
        "x" * 65,
        "has spaces",
        "<script>alert(1)</script>",
        "line\nbreak",
    ],
)
def test_a_malformed_client_id_is_replaced(client: TestClient, hostile: str) -> None:
    """The ID is echoed into responses and logs, so it is not taken on trust."""
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: hostile})

    assert response.headers[REQUEST_ID_HEADER] != hostile
    assert len(response.headers[REQUEST_ID_HEADER]) == 32


def test_every_log_line_for_a_request_carries_the_id(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """This is what makes the ID worth returning to a user."""
    with caplog.at_level(logging.INFO):
        client.get("/api/health", headers={REQUEST_ID_HEADER: "trace-000000001"})

    events = _events(caplog)
    assert events, "no structured log lines were emitted for the request"
    assert all(event["request_id"] == "trace-000000001" for event in events)


def test_the_access_log_reports_the_status_a_client_saw(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        client.get("/api/does-not-exist")

    completed = [event for event in _events(caplog) if event["event"] == "request.completed"]
    assert len(completed) == 1
    assert completed[0]["status_code"] == 404
    assert completed[0]["path"] == "/api/does-not-exist"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_concurrent_requests_never_share_a_correlation_id(
    app: FastAPI,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The reason the ID lives in a context variable and not in a global.

    Two requests are in flight in the same event loop at the same time, and
    each one logs on both sides of an await. A process-global, or any state
    keyed on anything coarser than the task, would attribute the second half of
    one request's logs to the other request. That is worse than having no
    correlation ID at all, because the logs would look correct.
    """
    logger = structlog.get_logger("test.slow")

    @app.get("/api/_slow")
    async def _slow() -> dict[str, str]:
        logger.info("slow.entered")
        await asyncio.sleep(0.05)
        logger.info("slow.resumed")
        return {"status": "ok"}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with caplog.at_level(logging.INFO):
            await asyncio.gather(
                client.get("/api/_slow", headers={REQUEST_ID_HEADER: "concurrent-aaaa"}),
                client.get("/api/_slow", headers={REQUEST_ID_HEADER: "concurrent-bbbb"}),
            )

    seen: dict[str, set[str]] = {}
    for event in _events(caplog):
        seen.setdefault(event["request_id"], set()).add(event["event"])

    assert seen == {
        "concurrent-aaaa": {"slow.entered", "slow.resumed", "request.completed"},
        "concurrent-bbbb": {"slow.entered", "slow.resumed", "request.completed"},
    }
