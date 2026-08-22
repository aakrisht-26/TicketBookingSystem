# Ticket Booking System

[![CI](https://github.com/aakrisht-26/TicketBookingSystem/actions/workflows/ci.yml/badge.svg)](https://github.com/aakrisht-26/TicketBookingSystem/actions/workflows/ci.yml)

Seat booking for movies and concerts, built around the parts that are actually
hard: holding a seat for a bounded time, guaranteeing two customers can never
take the same one, and handing a cancelled seat down a waitlist through
time-limited offers.

**This README is a placeholder.** It is written in full at step 21, to the
specification in `docs/ROADMAP.md`: demo GIF, demo credentials, all six
evaluation criteria, pasted concurrency test output, benchmark results, the
compliance matrix and the architecture diagram. A hosted URL goes here from
step 1 onward.

## Status

Step 0 of 21 complete: repository layout, tooling, continuous integration.

Step 1 is in progress and **not complete**. Landed: the application factory,
settings, structured logging with correlation IDs, the error registry and its
handlers, `GET /api/health`, `GET /api/health/ready`, the SQLAlchemy engine
against Neon, and the baseline migration. What remains is the Render
deployment, so there is no hosted URL yet. `docs/backlog.md` B4 tracks it.

## Stack

FastAPI, SQLAlchemy 2.x, Alembic and Python 3.11 against PostgreSQL, hosted on
Neon. React, Vite, TypeScript and Tailwind on the front. Server-sent events for
live seat updates. Deployed as a single Render web service.

## Layout

```
backend/app/          FastAPI application: factory, settings, errors, middleware
backend/migrations/   Alembic environment and the baseline revision
backend/tests/        pytest suite
docs/                 Roadmap, data model, standards, compliance matrix, ADRs
.github/              CI workflow and pull request template
docker-compose.yml    Local Postgres, development only
```

## Documentation

| File | What it is |
|---|---|
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | The 21 steps, the README specification, the final gate |
| [`docs/DATA-MODEL.md`](docs/DATA-MODEL.md) | Schema, the eight invariants, the failure mode table |
| [`docs/STANDARDS.md`](docs/STANDARDS.md) | Engineering standards: security, errors, accessibility, infrastructure |
| [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) | Every line of the brief, mapped to the step and test that satisfies it |
| [`docs/test-traceability.md`](docs/test-traceability.md) | Each invariant and the test that proves it |
| [`docs/adr/`](docs/adr/) | Architecture decision records |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Local setup and the working protocol |

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT. See [`LICENSE`](LICENSE).
