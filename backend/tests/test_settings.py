"""Configuration."""

import pytest
from pydantic import ValidationError

from app.settings import Environment
from tests.support import build_settings

_URL = "postgresql+psycopg://tbs:tbs@localhost:5432/tbs"


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failing at startup beats failing on the first query in production."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        build_settings()


def test_defaults_are_development() -> None:
    settings = build_settings(database_url=_URL)

    assert settings.environment is Environment.DEVELOPMENT
    assert settings.log_level == "INFO"


@pytest.mark.parametrize(
    ("environment", "json_logs", "debug"),
    [
        (Environment.DEVELOPMENT, False, True),
        (Environment.TEST, True, True),
        (Environment.PRODUCTION, True, False),
    ],
)
def test_rendering_and_debug_follow_the_environment(
    environment: Environment,
    json_logs: bool,
    debug: bool,
) -> None:
    settings = build_settings(environment=environment, database_url=_URL)

    assert settings.log_json is json_logs
    assert settings.debug is debug


def test_an_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError, match="environment"):
        build_settings(environment="staging", database_url=_URL)


def test_settings_are_frozen() -> None:
    """Configuration changing under a running request would be untraceable."""
    settings = build_settings(database_url=_URL)

    with pytest.raises(ValidationError):
        settings.log_level = "DEBUG"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        (
            "postgresql://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
        (
            "postgres://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
        (
            "postgresql+psycopg://u:p@host/db",
            "postgresql+psycopg://u:p@host/db",
        ),
    ],
)
def test_a_provider_issued_url_is_normalised_onto_the_async_driver(
    given: str,
    expected: str,
) -> None:
    """Neon and Render hand out `postgresql://`, which SQLAlchemy reads as psycopg2.

    Rewriting it here means the operator pastes the string their provider gave
    them, rather than editing it correctly or discovering the mistake on deploy.
    """
    assert build_settings(database_url=given).database_url == expected


def test_an_explicit_driver_is_left_alone() -> None:
    """An unsupported driver should fail loudly, not be silently rewritten."""
    settings = build_settings(database_url="postgresql+asyncpg://u:p@host/db")

    assert settings.database_url == "postgresql+asyncpg://u:p@host/db"


def test_query_parameters_survive_normalisation() -> None:
    """Neon's URL carries sslmode and channel_binding, and both matter."""
    settings = build_settings(
        database_url="postgresql://u:p@host/db?sslmode=require&channel_binding=require"
    )

    assert settings.database_url.endswith("?sslmode=require&channel_binding=require")
