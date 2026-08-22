"""Shared fixtures.

Settings are constructed explicitly rather than read from the environment, so a
developer's local ``.env`` can never change what a test asserts. The one
exception is the database URL, which has to be real: `CLAUDE.md` forbids
testing against SQLite, so tests that touch a database talk to PostgreSQL.
"""

import asyncio
import os
import sys
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Environment, Settings
from tests.support import build_settings

# psycopg's async mode cannot run on the ProactorEventLoop that Windows selects
# by default. Production and CI are Linux and unaffected; this keeps the suite
# runnable on a Windows development machine without putting platform branching
# into the application.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Syntactically valid and deliberately never connected to. Tests that assert on
# routing, errors, logging or the OpenAPI schema need settings, not a database,
# and pointing them at a real one would make them slow and flaky for no gain.
UNCONNECTED_DATABASE_URL = "postgresql+psycopg://tbs:tbs@localhost:5432/tbs_unused"

# TEST-NET-3 (RFC 5737), reserved for documentation and guaranteed not to route.
# Used to force the outage path deterministically rather than by unplugging
# something.
# The credentials are distinctive so a test can assert they never appear in a
# response body.
UNREACHABLE_DATABASE_URL = (
    "postgresql+psycopg://leaked_user:leaked_password@203.0.113.1:5432/leaked_db"
)


@pytest.fixture
def anyio_backend() -> str:
    """Async tests run on asyncio. There is no trio in this project."""
    return "asyncio"


@pytest.fixture
def settings() -> Settings:
    """Configuration for a test process, with no reachable database."""
    return build_settings(
        environment=Environment.TEST,
        log_level="DEBUG",
        database_url=UNCONNECTED_DATABASE_URL,
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    """A freshly built application."""
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A client that returns the 500 envelope instead of re-raising."""
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def database_url() -> str:
    """The PostgreSQL a database test should run against.

    Deliberately fails rather than skipping. `CLAUDE.md` forbids marking a step
    done with a skipped test, and a database suite that quietly skips itself
    when nothing is configured is the same defect wearing a green tick.
    """
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL or DATABASE_URL must point at a PostgreSQL "
            "instance. See CONTRIBUTING.md; these tests never run against SQLite "
            "and never silently skip."
        )
    return url


@pytest.fixture
def db_settings(database_url: str) -> Settings:
    """Configuration pointed at a real database."""
    return build_settings(
        environment=Environment.TEST,
        log_level="DEBUG",
        database_url=database_url,
    )


@pytest.fixture
def db_client(db_settings: Settings) -> Iterator[TestClient]:
    """A client whose application can reach a real database."""
    with TestClient(create_app(db_settings), raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def unreachable_client() -> Iterator[TestClient]:
    """A client whose application points at a database that cannot answer."""
    outage = build_settings(
        environment=Environment.TEST,
        log_level="DEBUG",
        database_url=UNREACHABLE_DATABASE_URL,
        db_connect_timeout_seconds=2,
    )
    with TestClient(create_app(outage), raise_server_exceptions=False) as test_client:
        yield test_client
