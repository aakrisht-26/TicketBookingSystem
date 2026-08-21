# 1. Record architecture decisions

- Status: accepted
- Date: 2026-08-21

## Context

This system is graded on API design, code structure and documentation as much
as on behaviour, and several of its decisions are load-bearing but invisible in
the diff: seat state living only in Postgres, in-process SSE fan-out, Neon over
the alternatives, no message broker. A reviewer reading the code six months
from now, or reading it cold as an assessor, sees the outcome of those choices
but not the reasoning, and without the reasoning a deliberate constraint is
indistinguishable from an oversight.

Reconstructing that reasoning from commit messages does not work. Commits
explain what changed, not what was rejected, and the rejected option is usually
the more interesting half.

## Decision

Architecture decisions are recorded as short markdown files in `docs/adr/`,
numbered sequentially and never renumbered, in the format introduced by Michael
Nygard. Each record carries a status, the context that forced the decision, the
decision itself, and its consequences including the ones that hurt.

A record is immutable once accepted. A decision that is later reversed gets a
new record superseding the old one, and the old one is marked superseded rather
than deleted, so the history of the reasoning survives.

`docs/adr/README.md` indexes the records.

## Consequences

Every non-obvious decision now costs a few paragraphs of writing, which is a
real tax on small changes and is the reason ADR practices lapse. The
Definition of Done in `CLAUDE.md` names the ADR explicitly so it is checked per
step rather than remembered.

In exchange, the constraints this system accepts on purpose read as decisions.
Three of them are already known and get their own records as they land:
`0003-no-redis.md`, `0006-sse-fanout.md` and `0007-database-hosting.md`. The
final write-up and the README limitations section draw on those records instead
of reasoning from scratch.
