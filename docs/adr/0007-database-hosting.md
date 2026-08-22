# 7. Neon over Render Postgres and Supabase

- Status: accepted
- Date: 2026-08-22

## Context

This project needs a hosted PostgreSQL database on a free tier, and it needs it
to still be there later. The submission is a repository link and a hosted URL
with no deadline attached, which means the interval between finishing and being
reviewed is unknown and possibly long, and during that interval nobody is
watching the infrastructure.

That reframes what "good enough for a free tier" means. Query performance is
not the binding constraint; a demo workload is small. The binding constraint is
survival. A reviewer opening the hosted URL after a quiet month must find a
working application, without anyone having intervened to keep it that way.

The requirements, in order of how much they matter here:

1. Survives extended inactivity with no manual step.
2. Does not expire, and is not deleted.
3. Real PostgreSQL. The guarantees in `docs/DATA-MODEL.md` are
   Postgres-specific: partial unique indexes, `SELECT ... FOR UPDATE`,
   `TIMESTAMPTZ` with `now()` evaluated server-side, and `LISTEN`/`NOTIFY` as
   the documented path in `0006-sse-fanout.md`.
4. A pooled connection endpoint, since a small web service opening connections
   per worker will otherwise exhaust a free tier's connection limit.

## Decision

Neon, using the pooled connection string, with `pool_pre_ping=True` and a
modest `pool_recycle` on the SQLAlchemy engine.

Neon scales a database to zero when idle and resumes it on the next connection,
in a couple of seconds, without expiring or requiring a restore. That maps onto
the reviewer's access pattern exactly: long idle, then one visit.

## Alternatives considered

**Render PostgreSQL, free tier.** Rejected, and it is the option this project
would otherwise have taken, since the application is already a Render web
service and colocating them is simpler. A free Render database expires 30 days
after creation and is then deleted. The failure is total, it is silent from the
outside, and it happens on a fixed schedule that has nothing to do with usage.
A reviewer arriving on day 31 finds a dead application and a repository whose
central claim cannot be checked. There is no recovery that does not involve
noticing in time.

**Supabase, free tier.** Rejected. A free project pauses after a week of
inactivity and needs a manual restore from the dashboard to come back. The
pattern that triggers it, a week of no traffic, is precisely the pattern this
project has between finishing and being reviewed, and the visit that would wake
it up is the one that finds it paused. It converts the reviewer's first
impression into a dependency on me happening to be watching.

**Self-hosted PostgreSQL on a small VPS.** Rejected. It costs money and it
makes me responsible for backups, patching, disk monitoring and uptime, none of
which this project is assessed on and all of which can fail while unattended.

**SQLite.** Rejected outright. Every hard guarantee here is Postgres-specific;
partial unique indexes and `FOR UPDATE` row locking are the mechanism, not an
implementation detail. `CLAUDE.md` forbids even testing against it, for the
good reason that a green test suite on SQLite would prove nothing about the
behaviour being claimed.

**Keeping Render PostgreSQL and recreating it every 30 days.** Rejected. It
substitutes a recurring manual step for an infrastructure choice, and the
consequence of forgetting once is total data loss on a schedule.

## Consequences

The first request after an idle period is slow. Neon resumes in about two
seconds, and Render's own free tier cold start is roughly a minute on top of
that. A reviewer who hits a blank page for a minute concludes the application
is broken, so the README says this in the first section, before the demo
credentials, and the demo GIF exists so that anyone unwilling to wait can still
see the system work.

Neon closes idle connections aggressively. Without `pool_pre_ping=True` the
application hands out a dead connection from the pool and the first request
after an idle period fails with a stale-connection error, which looks exactly
like a bug in the application. This is a real trap rather than a theoretical
one, which is why it is called out in `CLAUDE.md`, listed in the failure mode
table, and verified directly in step 1 by leaving the deployed application idle
for ten minutes and then hitting it.

Free tier storage is 0.5 GB. That is ample for the application and not ample
for the step 15 contention benchmark, which is why that step truncates its data
once the numbers have been recorded.

The stack now spans two providers. Two dashboards, two sets of credentials, and
a connection string that has to be configured into Render rather than wired up
automatically. That connection string is a secret: it lives in the Render
environment and in a local `.env`, and never in `alembic.ini`, which is
asserted by `test_no_connection_string_is_committed`.

Nothing in the codebase depends on Neon specifically, only on PostgreSQL 17,
which `docker-compose.yml` matches locally. If the free tier terms change, the
migration is a new connection string and a fresh `alembic upgrade head`.
