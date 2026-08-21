"""Application configuration, read from the environment.

One source of truth. Nothing in the application reads ``os.environ`` directly,
so every knob this system has is visible in one class and documented in
``.env.example``.
"""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment. Drives log rendering and error verbosity."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Configuration for one process.

    Every field here is read by live code. A variable that nothing consumes yet
    is not added until the step that consumes it, so this class never grows a
    setting that quietly does nothing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Deployment environment.",
    )
    log_level: str = Field(
        default="INFO",
        description="Root log level, a standard library level name.",
    )
    database_url: str = Field(
        description=(
            "PostgreSQL connection URL. Consumed by Alembic. The application "
            "engine that also reads it is created in the remainder of step 1."
        ),
    )

    @property
    def log_json(self) -> bool:
        """Render logs as JSON off the development console only.

        Production log aggregation needs JSON; a human reading a local console
        does not, and colourised key-value output is far easier to scan.
        """
        return self.environment is not Environment.DEVELOPMENT

    @property
    def debug(self) -> bool:
        """Whether this process is running outside production."""
        return self.environment is not Environment.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, read from the environment once.

    Cached because reading and validating the environment on every request is
    waste. Tests call ``get_settings.cache_clear()`` to pick up a changed
    environment.
    """
    return Settings()  # type: ignore[call-arg]  # pydantic-settings fills from env
