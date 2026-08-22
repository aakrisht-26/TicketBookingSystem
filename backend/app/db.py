"""Database engine and readiness probe.

One engine per process, created by the application factory's lifespan and
disposed on shutdown. Nothing here knows about HTTP: the readiness endpoint
translates a failure into the error envelope, so this module stays usable from
the sweeper and from scripts that have no request in flight.

Pooling is shaped for Neon. The connection string is the pooled endpoint, which
is itself PgBouncer, so this process keeps a small stable set of connections
rather than bursting. See ``docs/adr/0009-database-driver-and-pooling.md``.

There is no session factory yet. Step 2 adds one alongside the first models,
because a factory nothing opens a session with is a moving part that no test
can hold to account.
"""

import asyncio
from typing import cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlette.requests import Request

from app.settings import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    """Build the engine for this process.

    ``pool_pre_ping`` is not configurable and is deliberately hard-coded on.
    Neon closes idle connections aggressively, and without it the first request
    after a quiet period is served a dead connection from the pool and fails
    with an error that looks like an application bug. There is no environment
    in which turning it off is the right choice, so it is not a knob.
    """
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_size=settings.db_pool_size,
        # The pooled endpoint is already a connection pool. Bursting past
        # pool_size would push that work onto PgBouncer and consume a free
        # tier's connection budget, so overflow is refused rather than queued
        # somewhere invisible. If step 15 shows this is the bottleneck, that is
        # a measurement to change it on.
        max_overflow=0,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


async def ping(engine: AsyncEngine, *, timeout_seconds: int) -> None:
    """Confirm the database can answer, or raise.

    Bounded, because a readiness probe that hangs is no more useful than one
    that fails: the platform learns nothing until its own timeout fires. The
    connection attempt is bounded by ``connect_timeout`` and the whole probe by
    ``timeout_seconds``, so a connection that opens and then stops responding is
    covered as well as one that never opens.
    """
    async with asyncio.timeout(timeout_seconds), engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def get_engine(request: Request) -> AsyncEngine:
    """Return the engine the application factory's lifespan created."""
    return cast("AsyncEngine", request.app.state.engine)
