"""Application configuration, read from the environment.

One source of truth. Nothing in the application reads ``os.environ`` directly,
so every knob this system has is visible in one class and documented in
``.env.example``.
"""

import re
from enum import StrEnum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Hosting providers hand out a plain `postgresql://` URL. SQLAlchemy would read
# that as psycopg2, which is not installed and is not the driver this project
# uses. The scheme is normalised rather than requiring the operator to edit a
# string their provider generated.
_DRIVERLESS_SCHEME = re.compile(r"^postgres(ql)?://")
ASYNC_DRIVER_SCHEME = "postgresql+psycopg://"


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
            "PostgreSQL connection URL, read by both the application engine and "
            "Alembic. Use the Neon pooled endpoint in production."
        ),
    )
    db_pool_size: int = Field(
        default=5,
        ge=1,
        description="Connections held open by this process.",
    )
    db_pool_recycle_seconds: int = Field(
        default=300,
        ge=1,
        description="Discard a pooled connection older than this.",
    )
    db_connect_timeout_seconds: int = Field(
        default=5,
        ge=1,
        description="Bound on how long a connection attempt or readiness probe may take.",
    )

    @field_validator("database_url")
    @classmethod
    def _use_the_async_driver(cls, value: str) -> str:
        """Normalise a provider-issued URL onto the driver this project uses.

        A URL that already names a driver is left alone, so an explicit choice
        is never silently overridden; an unsupported one fails loudly at engine
        creation rather than being rewritten into something that appears to
        work.
        """
        return _DRIVERLESS_SCHEME.sub(ASYNC_DRIVER_SCHEME, value, count=1)

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
