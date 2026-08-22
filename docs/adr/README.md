# Architecture decision records

Numbered, immutable, never renumbered. A reversed decision gets a new record
that supersedes the old one; the old record stays and is marked superseded.
Format and rationale: [ADR 0001](0001-record-architecture-decisions.md).

| # | Title | Status | Step |
|---|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted | 0 |
| [0002](0002-no-api-version-prefix.md) | No version prefix on the API path | accepted | 1 |
| [0003](0003-no-redis.md) | No Redis, no Celery, no message broker | accepted | 1 |
| [0004](0004-pure-asgi-middleware.md) | Middleware is written against raw ASGI | accepted | 1 |
| [0005](0005-derived-seat-status.md) | Seat status is derived, not stored | accepted | 1 |
| [0006](0006-sse-fanout.md) | Server-sent event fan-out is in-process | accepted | 1 |
| [0007](0007-database-hosting.md) | Neon over Render Postgres and Supabase | accepted | 1 |
| [0008](0008-read-committed-with-row-locks.md) | READ COMMITTED with explicit row locks, not SERIALIZABLE | accepted | 1 |
| [0009](0009-database-driver-and-pooling.md) | psycopg 3 as the only driver, with a small fixed pool | accepted | 1 |

Records 0003 and 0005 to 0008 were written before the code they govern. They
document decisions already taken in `CLAUDE.md`, `docs/STANDARDS.md` and
`docs/DATA-MODEL.md`, so that the reasoning exists at the point the
implementation starts rather than being reconstructed afterwards. The steps
that implement them are named in each record.
