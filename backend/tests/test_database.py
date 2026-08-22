"""The engine, the readiness probe and the outage path.

Everything here that says "the database answered" talks to a real PostgreSQL,
because that is the only kind of evidence worth having.
"""

import logging
import time
from typing import cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

from app import __version__
from app.db import create_engine, ping
from app.errors import ERROR_REGISTRY, ErrorCode
from app.request_context import REQUEST_ID_HEADER
from app.settings import Settings
from tests.conftest import UNREACHABLE_DATABASE_URL
from tests.support import build_settings

_OUTAGE_BUDGET_SECONDS = 15.0


# --------------------------------------------------------------------------
# Engine configuration
# --------------------------------------------------------------------------


def test_pool_pre_ping_is_always_on(db_settings: Settings) -> None:
    """It is not a setting, and this fails if someone makes it one.

    Without it, the first request after Neon has closed an idle connection is
    served that dead connection and fails.
    """
    engine = create_engine(db_settings)

    assert engine.pool._pre_ping is True


def test_pool_settings_come_from_configuration(database_url: str) -> None:
    """A knob nothing reads is not a knob."""
    engine = create_engine(
        build_settings(database_url=database_url, db_pool_size=3, db_pool_recycle_seconds=77)
    )

    pool = cast("QueuePool", engine.pool)

    assert pool.size() == 3
    assert pool._recycle == 77


# --------------------------------------------------------------------------
# Readiness, against a real database
# --------------------------------------------------------------------------


def test_readiness_reports_the_database_is_ok(db_client: TestClient) -> None:
    response = db_client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "version": __version__}


def test_readiness_carries_a_correlation_id(db_client: TestClient) -> None:
    response = db_client.get("/api/health/ready")

    assert response.headers[REQUEST_ID_HEADER]


def test_liveness_does_not_need_the_database(unreachable_client: TestClient) -> None:
    """The whole reason the two probes are separate.

    The database is unreachable for this application, and liveness still
    answers 200, so the platform restarts nothing while a dependency is down.
    """
    response = unreachable_client.get("/api/health")

    assert response.status_code == 200


@pytest.mark.anyio
async def test_pool_pre_ping_recovers_a_dropped_connection(db_settings: Settings) -> None:
    """The deterministic form of "leave it idle and see what happens".

    Neon closes idle connections. Rather than wait for that, the pooled
    connection is closed underneath the pool at the driver level, which is what
    the client sees when the server drops it. The next checkout must succeed.
    """
    engine = create_engine(build_settings(database_url=db_settings.database_url, db_pool_size=1))
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            raw = await connection.get_raw_connection()
            driver_connection = raw.driver_connection
            assert driver_connection is not None

        await driver_connection.close()

        async with engine.connect() as connection:
            assert (await connection.execute(text("SELECT 1"))).scalar_one() == 1
    finally:
        await engine.dispose()


@pytest.mark.anyio
async def test_without_pre_ping_the_dropped_connection_fails(db_settings: Settings) -> None:
    """The other half of the test above.

    Without this, the previous test would pass just as well against an engine
    that never had `pool_pre_ping` at all, and would prove nothing.
    """
    engine = create_async_engine(db_settings.database_url, pool_pre_ping=False, pool_size=1)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            raw = await connection.get_raw_connection()
            driver_connection = raw.driver_connection
            assert driver_connection is not None

        await driver_connection.close()

        with pytest.raises(SQLAlchemyError):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


# --------------------------------------------------------------------------
# Forced outage
# --------------------------------------------------------------------------


def test_outage_returns_503_with_the_registered_code(unreachable_client: TestClient) -> None:
    response = unreachable_client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == ErrorCode.DATABASE_UNAVAILABLE


def test_outage_response_carries_a_correlation_id(unreachable_client: TestClient) -> None:
    """A user reporting an outage has something to quote."""
    response = unreachable_client.get("/api/health/ready")

    request_id = response.json()["error"]["request_id"]
    assert request_id
    assert request_id == response.headers[REQUEST_ID_HEADER]


def test_outage_response_leaks_nothing(unreachable_client: TestClient) -> None:
    """No stack trace, no driver name, no host, no credentials."""
    raw = unreachable_client.get("/api/health/ready").text

    for leak in (
        "Traceback",
        "psycopg",
        "sqlalchemy",
        "203.0.113.1",
        "leaked_user",
        "leaked_password",
        "leaked_db",
    ):
        assert leak not in raw, f"readiness 503 leaked {leak!r}"


def test_outage_message_is_the_registered_one(unreachable_client: TestClient) -> None:
    """The wording comes from the registry, never from the exception.

    Checking for known leak strings only catches the leaks anticipated. This
    catches any of them, because anything the driver produced would not be
    identical to the registered sentence.
    """
    body = unreachable_client.get("/api/health/ready").json()

    assert body["error"]["message"] == ERROR_REGISTRY[ErrorCode.DATABASE_UNAVAILABLE].message


def test_outage_logs_the_driver_diagnosis(
    unreachable_client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """What is withheld from the client has to reach the logs.

    The probe's outer timeout must not fire before the driver reports, or the
    only record of the failure is a bare TimeoutError naming nothing. That is
    exactly what happened when the two budgets were equal.
    """
    with caplog.at_level(logging.WARNING):
        unreachable_client.get("/api/health/ready")

    unavailable = [
        record.msg
        for record in caplog.records
        if isinstance(record.msg, dict) and record.msg["event"] == "health.database_unavailable"
    ]
    assert len(unavailable) == 1
    assert unavailable[0]["error_type"] != "TimeoutError"


def test_outage_body_has_only_the_envelope_fields(unreachable_client: TestClient) -> None:
    body = unreachable_client.get("/api/health/ready").json()

    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}


def test_outage_fails_fast(unreachable_client: TestClient) -> None:
    """A readiness probe that hangs tells the platform nothing.

    The budget is generous compared to the two-second connect timeout, because
    a loaded CI runner is slow, but it is far below the point where a platform
    health check would give up on its own.
    """
    started = time.monotonic()
    unreachable_client.get("/api/health/ready")
    elapsed = time.monotonic() - started

    assert elapsed < _OUTAGE_BUDGET_SECONDS, f"readiness took {elapsed:.1f}s"


@pytest.mark.anyio
async def test_ping_raises_rather_than_returning_a_status() -> None:
    """`ping` stays free of HTTP concerns; the endpoint does the translating."""
    engine = create_engine(
        build_settings(database_url=UNREACHABLE_DATABASE_URL, db_connect_timeout_seconds=2)
    )
    try:
        with pytest.raises((SQLAlchemyError, TimeoutError)):
            await ping(engine, timeout_seconds=2)
    finally:
        await engine.dispose()
