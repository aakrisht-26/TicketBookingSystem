# Architecture decision records

Numbered, immutable, never renumbered. A reversed decision gets a new record
that supersedes the old one; the old record stays and is marked superseded.
Format and rationale: [ADR 0001](0001-record-architecture-decisions.md).

| # | Title | Status | Step |
|---|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | accepted | 0 |
| [0002](0002-no-api-version-prefix.md) | No version prefix on the API path | accepted | 1 |
| [0004](0004-pure-asgi-middleware.md) | Middleware is written against raw ASGI | accepted | 1 |

Records known to be coming, named here so the numbering is not a surprise:
`0003-no-redis.md`, `0006-sse-fanout.md`, `0007-database-hosting.md`. Their
reasoning is summarised in `docs/STANDARDS.md` until each record lands with the
step that makes the decision real.
