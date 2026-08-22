"""Health endpoints.

Two endpoints, answering two different questions, because a platform needs to
tell them apart.

``GET /api/health`` is liveness: is this process running and able to serve
HTTP? It touches nothing else, so a slow dependency can never cause the
platform to restart a process that is working fine.

``GET /api/health/ready`` is readiness: can this process do useful work? That
means the database, so it queries it. A failure here should take the instance
out of rotation, not kill it.
"""

from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from app import __version__
from app.db import get_engine, ping
from app.errors import AppError, ErrorCode, ErrorResponse
from app.settings import Settings, get_settings

_logger = structlog.get_logger(__name__)

# Headroom for the query itself, on top of the driver's own connect timeout.
# The outer bound has to be strictly larger: if the two are equal it wins the
# race and replaces an error that names the failure with a bare TimeoutError
# that names nothing, leaving an operator with no diagnosis in the logs. It is
# a backstop for a connection that opens and then stops responding, not the
# primary mechanism.
_PROBE_MARGIN_SECONDS = 3

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Liveness result."""

    status: Literal["ok"] = Field(
        description="Always 'ok'. A process that can answer at all is live.",
    )
    version: str = Field(description="Version of the deployed backend.")

    model_config = {"json_schema_extra": {"example": {"status": "ok", "version": "0.1.0"}}}


class ReadinessResponse(BaseModel):
    """Readiness result. Only returned when every dependency answered."""

    status: Literal["ok"] = Field(description="Always 'ok'. A failure is a 503, not a body.")
    database: Literal["ok"] = Field(description="The database answered within the timeout.")
    version: str = Field(description="Version of the deployed backend.")

    model_config = {
        "json_schema_extra": {"example": {"status": "ok", "database": "ok", "version": "0.1.0"}}
    }


@router.get(
    "",
    summary="Liveness probe",
    description=(
        "Returns 200 whenever the process is running. Performs no I/O, so it "
        "reports the health of this process only and never that of its "
        "dependencies. Use /api/health/ready for dependency readiness."
    ),
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
)
async def health() -> HealthResponse:
    """Report that the process is alive."""
    return HealthResponse(status="ok", version=__version__)


@router.get(
    "/ready",
    summary="Readiness probe",
    description=(
        "Returns 200 when the database answered a trivial query within the "
        "configured timeout, and 503 with code DATABASE_UNAVAILABLE otherwise. "
        "The 503 body carries the correlation id and no detail about the "
        "failure, which is in the logs under that same id."
    ),
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "A dependency did not answer. The instance is not ready.",
        }
    },
)
async def ready(
    engine: Annotated[AsyncEngine, Depends(get_engine)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReadinessResponse:
    """Report that the process can reach everything it needs."""
    try:
        await ping(
            engine,
            timeout_seconds=settings.db_connect_timeout_seconds + _PROBE_MARGIN_SECONDS,
        )
    except (SQLAlchemyError, TimeoutError) as exc:
        # The exception type is logged and never returned. It names the driver,
        # and often the host, which is not something to hand to an unauthenticated
        # caller of a health endpoint.
        _logger.warning("health.database_unavailable", error_type=type(exc).__name__)
        raise AppError(ErrorCode.DATABASE_UNAVAILABLE) from exc

    return ReadinessResponse(status="ok", database="ok", version=__version__)
