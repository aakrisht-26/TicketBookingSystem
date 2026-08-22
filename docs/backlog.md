# Backlog

Real defects and deferred work found while executing a step but outside that
step's scope. The working protocol in `CLAUDE.md` forbids fixing them in place;
they land here and are picked up by the step that owns them.

Not a wishlist. An entry needs a concrete reason it matters and a step that
will close it.

| # | Found in | Item | Owning step | Status |
|---|---|---|---|---|
| B1 | 0 | `docker compose up` is still unverified: Docker is not installed on the development machine. No longer blocking, because the database tests run against Neon locally and against the CI service container, both real PostgreSQL 18. The compose file remains untested and is only a convenience for a contributor who wants a local database. | any | open, downgraded |
| B2 | 0 | CI had no Postgres service container, deliberately, until something connected to it. | 1 | closed: the workflow now runs `postgres:18`, the migration round trip and the database tests against it. |
| B4 | 1 | Step 1 is incomplete and its branch is not merged. The database half is done: the engine, `GET /api/health/ready` and the baseline migration are in, verified against real Neon. What remains is the deploy, blocked on network access. Render's start command must be `uvicorn --factory app.main:create_app`: `app/main.py` exposes the factory and no module-level `app` object, so the conventional `uvicorn app.main:app` fails at boot. Migrations run as a pre-deploy command, `alembic upgrade head`, never on boot. Outstanding: the Render service itself, auto-deploy from `main`, and the two remaining roadmap checks that need a deployment (hosted `/api/health/ready` returning ok, and ten minutes idle followed by a request with no stale-connection error). The forced-outage check is done and did not need the deploy. | 1 | open |
| B3 | 0 | CI does not yet run `tsc --noEmit`, the frontend build, Playwright or `axe`, because there is no frontend. `docs/STANDARDS.md` requires all four. Each is added by the step that creates the thing it checks, never earlier. | 16, 20 | open |
