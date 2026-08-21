"""Liveness endpoint.

``GET /api/health`` answers one question: is this process running and able to
serve HTTP? It deliberately touches nothing else, so a platform health check
never fails because a dependency is slow.

Readiness, ``GET /api/health/ready``, checks the database and is added with the
database connection in the remainder of step 1.
"""

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app import __version__

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    """Liveness result."""

    status: Literal["ok"] = Field(
        description="Always 'ok'. A process that can answer at all is live.",
    )
    version: str = Field(description="Version of the deployed backend.")

    model_config = {"json_schema_extra": {"example": {"status": "ok", "version": "0.1.0"}}}


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
