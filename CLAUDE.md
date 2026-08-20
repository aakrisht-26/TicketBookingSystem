# CLAUDE.md - Ticket Booking System

Root instruction file. Loaded every session and re-read after compaction. Kept short deliberately so the rules below stay reliable.

## Document index

Read the linked file **at the point indicated**, not all at once.

| File | Read when |
|---|---|
| `docs/ROADMAP.md` | Before starting any step. Contains all 21 steps, the README spec, and the final gate. |
| `docs/DATA-MODEL.md` | Before steps 2, 6, 7, 8, 9, 11, 12, 13. Contains the schema, the eight invariants, and the failure mode table. |
| `docs/STANDARDS.md` | Before step 0, and whenever adding auth, an endpoint, or frontend work. |
| `docs/COMPLIANCE.md` | At step 0 to understand scope, after each step to tick rows, at step 21 to verify. |

## Working protocol

Non-negotiable. Overrides any instinct to be efficient.

1. **One step at a time.** Execute exactly one numbered step, then stop and report. Do not begin the next step, do not "also fix" something you noticed, do not scaffold ahead. Real defects found outside the current step go into `docs/backlog.md`.
2. **Branch per step.** `git checkout -b step-NN-short-name` off `main`. Never commit to `main` directly.
3. **Verification is mandatory.** Every step lists a verification command. Run it, paste the real output in your report. A step is never complete on the basis of "the code looks correct".
4. **Commit per step**, Conventional Commits form. Open a PR against `main` and leave it unmerged. Aakrisht merges.
5. **Report format:** files touched; verification command plus actual output; decisions made alone and why; anything that surprised you; what the next step will do.
6. **No silent degradation.** If a signal exists but nothing consumes it, that is a bug. Add a field, a status, an error code or an event, and something must read it and a test must assert on it. This has been the single most common failure mode across previous projects. Check for it deliberately at the end of every step.
7. **Never mark a step done with a skipped or xfail test.** If a test cannot pass, stop and report why.
8. **`main` is always deployable.** From step 1 onward there is a live hosted URL, never broken at the end of a merged PR.

## Definition of Done

Applies to every step without exception.

- [ ] `ruff check` and `ruff format --check` clean
- [ ] `mypy --strict` clean on backend, `tsc --noEmit` clean on frontend
- [ ] New code has tests, and those tests would fail if the feature were removed
- [ ] CI green on the PR
- [ ] No `TODO`, no commented-out code, no debug prints, no unused imports
- [ ] Any new error condition has a registered code in `app/errors.py`
- [ ] Any new env var is in `.env.example` with a comment
- [ ] Any non-obvious decision written into `docs/adr/` as a short ADR
- [ ] Any new invariant added to `docs/test-traceability.md`
- [ ] Any brief requirement newly satisfied ticked in `docs/COMPLIANCE.md`

## Stack

FastAPI, SQLAlchemy 2.x, Alembic, Python 3.11. PostgreSQL on Neon in production, `docker compose` locally. React, Vite, TypeScript strict, Tailwind, TanStack Query. SSE for real-time. JWT access plus revocable refresh. pytest and httpx against real Postgres. Playwright plus `axe` for e2e. ruff, mypy strict, tsc strict. GitHub Actions. Single Render web service serving the built Vite bundle.

**Neon:** use the pooled connection string with `pool_pre_ping=True` and a modest `pool_recycle`. Neon closes idle connections aggressively and the app will throw stale-connection errors without this.

**Never test against SQLite.** The guarantees here are Postgres-specific.

**No Redis, no Celery, no message broker.** Considered, not a shortcut. See `docs/STANDARDS.md`.

## What backfires

Microservices, GraphQL, Kubernetes, a caching layer, an event bus, CQRS, five layers of abstraction over one CRUD call. This reads as inexperience, not seniority. A senior reviewer is impressed by a small system with hard guarantees and clear reasoning, never by a bigger diagram.

There is no deadline, so the risk is not rushing, it is never shipping. Deploy at step 1 and keep it deployed.

## Conventions

- Env-driven config: `HOLD_TTL_SECONDS` default 600, `OFFER_TTL_SECONDS`, `JWT_SECRET`, `DATABASE_URL`, `EMAIL_BACKEND`, SMTP settings, `FRONTEND_BASE_URL`, `RATE_LIMIT_*`.
- API prefix `/api`. No `/v1` unless justified, and ADR the decision rather than adding it reflexively.
- Money in integer cents. No float near a price.
- All timestamps `TIMESTAMPTZ`, UTC, `now()` evaluated in Postgres and never in Python.
- Backend tests in `backend/tests/`, concurrency tests in `backend/tests/test_concurrency.py` so a reviewer finds them in thirty seconds.
- OpenAPI curated deliberately: tags, summaries, response models, documented error responses, realistic examples. This is a graded criterion, not decoration.
- Prose in the README, ADRs and write-up uses plain hyphens, not em dashes.
