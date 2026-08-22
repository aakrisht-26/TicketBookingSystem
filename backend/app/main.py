"""Application factory.

``create_app`` builds a fully wired application and is the only place the
middleware stack, the exception handlers and the routers are assembled.

There is deliberately no module-level ``app`` instance. Importing this module
therefore has no side effects: no environment is read and no logging is
configured until something asks for an application. The server is started with
``uvicorn --factory app.main:create_app``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app import __version__
from app.api import health
from app.db import create_engine
from app.errors import ErrorResponse, register_exception_handlers
from app.logging_config import configure_logging
from app.middleware import AccessLogMiddleware, CorrelationIdMiddleware
from app.settings import Settings, get_settings

_logger = structlog.get_logger(__name__)

API_PREFIX = "/api"

_DESCRIPTION = """
Seat booking for movies and concerts.

Errors share one envelope, `{"error": {"code", "message", "request_id"}}`.
Switch on `code`, which is stable, and never on `message`, which is not. The
`request_id` matches the `X-Request-ID` response header and the server logs for
that request.
""".strip()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application.

    Args:
        settings: Configuration to run with. Defaults to the process-wide
            settings read from the environment. Tests pass an explicit instance.

    Returns:
        A configured application, ready to serve.
    """
    resolved = settings or get_settings()
    configure_logging(json_logs=resolved.log_json, level=resolved.log_level)

    @asynccontextmanager
    async def lifespan(instance: FastAPI) -> AsyncIterator[None]:
        """Own the engine for the life of the process.

        The engine is created here rather than at import, so importing this
        module still has no side effects, and disposed on the way out so a
        reload or a shutdown does not leak connections against a free tier's
        budget.
        """
        instance.state.engine = create_engine(resolved)
        _logger.info("app.started", environment=resolved.environment.value)
        try:
            yield
        finally:
            await instance.state.engine.dispose()
            _logger.info("app.stopped")

    app = FastAPI(
        lifespan=lifespan,
        title="Ticket Booking System",
        version=__version__,
        description=_DESCRIPTION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
        responses={500: {"model": ErrorResponse, "description": "Unexpected server error."}},
    )

    # Order matters. Starlette applies these outermost first, so the
    # correlation ID is bound before the access log line is written and before
    # any handler runs.
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)

    # Endpoints depend on Settings rather than reading the cached
    # process-wide instance, so a test that builds an application with its own
    # configuration gets that configuration everywhere.
    app.dependency_overrides[get_settings] = lambda: resolved

    app.include_router(
        health.router,
        prefix=API_PREFIX,
        responses={404: {"model": ErrorResponse, "description": "No such route."}},
    )

    return app
