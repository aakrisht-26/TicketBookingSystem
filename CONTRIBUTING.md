# Contributing

## Local setup

Requires Python 3.11, Node 22 and Docker.

```bash
cp .env.example .env
docker compose up -d postgres

cd backend
python3.11 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cd ..
pre-commit install
```

## Running the backend

```bash
cd backend
uvicorn --factory app.main:create_app --reload
```

`--factory` is not optional. `app/main.py` exposes `create_app` and no
module-level application instance, so importing the module reads no
environment and configures no logging. Every process builds its own
application from the factory, which is also how the tests get an instance that
cannot be contaminated by another test's configuration.

Interactive API documentation is at `http://localhost:8000/api/docs`, and the
schema the frontend client is generated from is at
`http://localhost:8000/api/openapi.json`.

## Database migrations

```bash
cd backend
alembic upgrade head          # apply everything outstanding
alembic downgrade base        # unwind to an empty database
alembic upgrade head --sql    # print the SQL without connecting
```

Migrations run as a deploy-time command, never on application boot, so two
booting instances cannot race each other. The connection URL comes from
`app/settings.py` rather than from `alembic.ini`, so no connection string is
ever committed.

Every revision needs a downgrade that works. CI runs upgrade, downgrade and
upgrade again on each pull request against a throwaway PostgreSQL, so a one-way
migration is caught there rather than the first time production needs
reverting.

## Checks

Run from `backend/`. CI runs exactly these, so a clean local run is a green
pull request.

```bash
ruff check .
ruff format --check .
mypy
pytest -q
```

The test suite needs a real PostgreSQL. It reads `TEST_DATABASE_URL`, falling
back to `DATABASE_URL`, and **fails rather than skipping** when neither is set.
That is deliberate: `CLAUDE.md` forbids marking a step done with a skipped
test, and a database suite that quietly skips itself is that failure wearing a
green tick. Set `TEST_DATABASE_URL` when you want tests kept away from the
database the application is using; the migration round trip in CI runs
`downgrade base`, which on a database with real schema drops all of it.

Never point tests at SQLite. The guarantees this system makes are
Postgres-specific and a green suite on SQLite would prove nothing.

### On Windows

psycopg's async mode cannot run on the `ProactorEventLoop` that Windows
selects by default, and raises an `InterfaceError` saying so. The test suite
sets the selector policy for itself, so `pytest` needs nothing.

Running the server does. Setting the event loop policy is **not** enough:
uvicorn builds its loop from a factory that returns `ProactorEventLoop` on
Windows directly, ignoring the policy. Start the server on an explicit loop
instead, from `backend/`:

```bash
python -c "import asyncio, uvicorn; s = uvicorn.Server(uvicorn.Config('app.main:create_app', factory=True, reload=True)); loop = asyncio.SelectorEventLoop(); asyncio.set_event_loop(loop); loop.run_until_complete(s.serve())"
```

Linux and macOS need none of this, and neither do CI or production, which is
why no part of it lives in `backend/app/`. See
[`docs/adr/0009-database-driver-and-pooling.md`](docs/adr/0009-database-driver-and-pooling.md).

`pre-commit run --all-files` runs the same lint, format and type checks across
the repository, plus the file hygiene hooks.

## Working protocol

The protocol in `CLAUDE.md` governs. Three parts of it matter most:

**One step per branch, one step per pull request.** Branch off `main` as
`step-NN-short-name`. Never commit to `main`. Something worth fixing that is
outside the current step goes in `docs/backlog.md`, not into the diff.

**Verification is not optional.** Every step in `docs/ROADMAP.md` names a
verification command. Run it and paste the real output into the pull request.
A step is never complete because the code looks correct.

**No silent degradation.** If a change introduces a signal, something must read
it and a test must assert on it. A field nobody reads, a status nobody
branches on, an event nobody subscribes to and an error code nobody returns are
all bugs, not future-proofing.

The full Definition of Done is in `CLAUDE.md` and is reproduced as a checklist
in the pull request template.

## Commits

Conventional Commits: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`,
`ci:`. The scope is optional and is usually `backend`, `frontend` or `ci`.

## Prose

Plain hyphens, not em dashes, in the README, the ADRs and the write-up.
