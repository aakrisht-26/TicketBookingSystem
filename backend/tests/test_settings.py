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
