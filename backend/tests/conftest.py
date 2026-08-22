"""Shared fixtures.

Settings are constructed explicitly rather than read from the environment, so a
developer's local ``.env`` can never change what a test asserts.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Environment, Settings
from tests.support import build_settings

# Not a real database. Nothing in step 1 connects; Alembic is the only consumer
# and the migration tests assert on how the value is resolved, not on a server
# answering at the other end.
TEST_DATABASE_URL = "postgresql+psycopg://tbs:tbs@localhost:5432/tbs_test"


@pytest.fixture
def settings() -> Settings:
    """Configuration for a test process."""
    return build_settings(
        environment=Environment.TEST,
        log_level="DEBUG",
        database_url=TEST_DATABASE_URL,
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
