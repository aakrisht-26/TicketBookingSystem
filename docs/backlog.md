# Backlog

Real defects and deferred work found while executing a step but outside that
step's scope. The working protocol in `CLAUDE.md` forbids fixing them in place;
they land here and are picked up by the step that owns them.

Not a wishlist. An entry needs a concrete reason it matters and a step that
will close it.

| # | Found in | Item | Owning step | Status |
|---|---|---|---|---|
| B1 | 0 | `docker compose up` is unverified on the development machine: Docker is not installed there, so `docker-compose.yml` is written against the documented Postgres 17 image but has never been started. Local backend tests therefore have no database to run against yet. Must be started for real, and its connection string proven, before any test claims to run against Postgres. | 1 | open |
| B2 | 0 | CI has no Postgres service container. Deliberate: at step 0 no code touches a database, and a service container nothing connects to is an unread signal. The workflow gains the service in the step that adds the first database-backed test, and that test is what proves the container works. | 1 | open |
| B4 | 1 | Step 1 is incomplete and its branch is not merged. Blocked on credentials: the Neon connection string and the Render account. Render's start command must be `uvicorn --factory app.main:create_app`: `app/main.py` exposes the factory and no module-level `app` object, so the conventional `uvicorn app.main:app` fails at boot. Outstanding are the SQLAlchemy engine with `pool_pre_ping` and `pool_recycle`, `GET /api/health/ready`, the Render service with migrations as a pre-deploy command, and the three deployment checks in the roadmap's step 1 verification (hosted readiness, forced database outage returning 503, ten-minute idle with no stale connection). | 1 | open |
| B3 | 0 | CI does not yet run `tsc --noEmit`, the frontend build, Playwright or `axe`, because there is no frontend. `docs/STANDARDS.md` requires all four. Each is added by the step that creates the thing it checks, never earlier. | 16, 20 | open |
