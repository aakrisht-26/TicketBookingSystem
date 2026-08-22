# 9. psycopg 3 as the only driver, with a small fixed pool

- Status: accepted
- Date: 2026-08-22

## Context

The application is async throughout, so it needs an async PostgreSQL driver.
Alembic is not async, so it needs a synchronous one. Those can be the same
driver or two different ones, and the choice is not obvious.

The connection string is the deciding constraint. Neon issues it in one shape,
and the operator should be able to paste it unchanged:

```
postgresql://USER:PASSWORD@ep-....-pooler.REGION.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Two things about that string matter. It carries `sslmode` and
`channel_binding`, which are libpq parameters rather than SQLAlchemy ones. And
the host contains `-pooler`, meaning it is Neon's pooled endpoint, which is
PgBouncer in transaction mode rather than PostgreSQL itself.

The second point shapes the pool. Putting a large bursting connection pool in
front of PgBouncer means two pools stacked on each other, each sized without
knowledge of the other, against a free tier with a finite connection budget.

## Decision

**psycopg 3 for everything**, as `postgresql+psycopg://`. The same driver
serves `create_async_engine` in the application and the synchronous
`engine_from_config` in `migrations/env.py`, from one connection string.

The scheme is normalised in `Settings`: a URL arriving as `postgresql://` or
`postgres://` is rewritten to `postgresql+psycopg://`, because that is the
shape providers issue and SQLAlchemy would otherwise resolve it to psycopg2,
which is not installed. A URL that already names a driver is left alone, so an
explicit choice fails loudly rather than being silently rewritten.

**A small fixed pool.** `pool_size` from configuration, default 5, and
`max_overflow=0`. The pooled endpoint is already a pool; this process's job is
to hold a small stable set of connections rather than to burst into somebody
else's.

**`pool_pre_ping` is hard-coded on and is not configurable.** Neon closes idle
connections aggressively. Without pre-ping the first request after a quiet
period is handed a dead connection and fails with something that reads like an
application bug. There is no deployment where turning it off is correct, so it
is not offered as a knob.

**`pool_recycle` and `connect_timeout` are configurable**, defaulting to 300
and 5 seconds.

## Alternatives considered

**asyncpg for the application, psycopg for Alembic.** Rejected, and it is the
faster driver, so this is a real cost. asyncpg does not accept libpq parameters:
`sslmode` and `channel_binding` have to be stripped from the URL and translated
into an `ssl=` argument. That means code that rewrites a connection string, and
a rewrite that is wrong fails at deploy time against the real database rather
than locally against a permissive one. Running two drivers also means two sets
of connection semantics to keep in mind for one database. The performance
difference does not decide this system: the bottleneck at step 15 is row-lock
contention on a seat, not driver parsing.

**asyncpg for both, with a sync wrapper for Alembic.** Rejected. It adds
indirection to the one component that most needs to be boring, since it is what
runs against production as a pre-deploy command.

**psycopg2.** Rejected. Synchronous only, so the application would need
threads to avoid blocking the event loop, which is the wrong shape for an
application whose remaining steps are about concurrency and streaming.

**Requiring the operator to write `postgresql+psycopg://` in the environment.**
Rejected. It makes correct configuration depend on remembering an
implementation detail, and the failure is at boot on a platform where boot
failures are least convenient to debug. Normalising costs one validator and one
test.

**Leaving `max_overflow` at SQLAlchemy's default of 10.** Rejected for now.
Three times the configured pool size can open against a free tier without
anything having asked for it. Refusing overflow makes saturation show up as
waiting on a connection, which is measurable, rather than as connections
appearing somewhere nobody is looking.

**Disabling psycopg's prepared statements for PgBouncer.** Considered and found
unnecessary. Transaction pooling historically broke prepared statements, which
is why `prepare_threshold=None` is common advice. Tested against this Neon
endpoint with 100 short transactions over 5 pooled connections, well past
psycopg's threshold of 5, with no error. The default is kept because turning it
off costs performance for a problem this deployment does not have; the finding
is recorded here so a future failure is recognised rather than rediscovered.

## Consequences

psycopg 3's async mode cannot run on the ProactorEventLoop that Windows selects
by default, and raises an error saying so. Production and CI are Linux and are
unaffected. On Windows the selector policy has to be set before anything
connects. That is handled in `tests/conftest.py` and documented in
`CONTRIBUTING.md`, deliberately not in `backend/app/`, because an application
that mutates the global event loop policy on import is worse than a documented
development step.

`max_overflow=0` means a burst beyond `pool_size` waits for a connection rather
than opening one. Under sustained contention that turns into queueing latency,
which step 15 is there to measure. If it turns out to be the limit, that is a
number to change the setting on, not a reason to have guessed differently now.

Normalising the URL scheme means `Settings.database_url` is not always the
string the operator supplied. Anything comparing the two has to normalise
first, and the validator is the single place that transformation happens.

The binary wheel, `psycopg[binary]`, is pinned rather than the source
distribution, because neither the Render build image nor the CI runner is
guaranteed a libpq build toolchain. It is the packaging most likely to install
without incident, at the cost of a larger install.
