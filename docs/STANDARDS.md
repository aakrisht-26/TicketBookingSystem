# Engineering standards

Read before step 0, and whenever adding auth, an endpoint, or frontend work. Collectively these are how evaluation criterion E6 (API design, code structure, documentation) is won. E6 is the criterion lost by accident.

## Continuous integration

GitHub Actions on every push and PR: lint, format check, mypy strict, tsc strict, backend tests against a real Postgres service container, `alembic upgrade head` then `downgrade base` then `upgrade head`, frontend build, Playwright e2e with `axe`. Badge in the README. Red build blocks merge.

## Continuous deployment

`main` auto-deploys to Render. Migrations run as a **pre-deploy command, not on application boot**, so two booting instances cannot race a migration.

## Type safety end to end

`mypy --strict` on backend, TypeScript `strict` on frontend, and the frontend API client is **generated from the backend OpenAPI schema**, so a backend contract change breaks the frontend build instead of production. Small detail, disproportionate signal.

## Structured logging

`structlog`, JSON in production. Correlation ID from `X-Request-ID` or generated, present in every log line for that request and in every error response body. Seat state transitions logged at INFO with show id, seat id, actor and reason. Never log tokens, passwords or full JWTs.

## Errors

Single registry in `app/errors.py`. Shape `{"error": {"code": "SEAT_UNAVAILABLE", "message": "...", "request_id": "..."}}`. Codes stable and machine-readable, frontend switches on `code` and never on `message`. No stack trace reaches a client. Global handler catches everything unhandled and returns `INTERNAL_ERROR`.

## Security

- Argon2id password hashing.
- Short-lived access JWT plus rotating refresh token stored hashed and revocable. Refresh token in an httpOnly, Secure, SameSite=Lax cookie. Access tokens never in `localStorage`.
- Refresh token reuse detection: presenting an already-rotated token revokes the whole family.
- **Registration accepts `customer` and `organiser` only.** Admin is seeded, never self-registerable. A request attempting to register as admin returns 422. Needs an explicit test, because it is the kind of privilege escalation a reviewer will actually try.
- Rate limiting on login, register, hold creation and offer claim. In-process token bucket keyed on IP plus user. No Redis.
- CORS locked to the known origin, never `*`.
- All input validated by Pydantic. No string interpolation into SQL.
- Secrets only from env. A committed secret is a step failure.
- Security headers middleware: HSTS, X-Content-Type-Options, Referrer-Policy, restrictive CSP.
- Booking references are Crockford base32, 8 characters, from a CSPRNG. **Never sequential**, since a sequential reference leaks total booking volume to any ticket holder.
- Offer tokens and refresh tokens stored hashed, never plaintext.
- **The seat map never leaks holder identity.** Other customers see a seat as unavailable, not who holds it.

## Idempotency

`POST /api/bookings` and `POST /api/offers/{token}/claim` accept an `Idempotency-Key` header. Key, user, endpoint and a hash of the request body are stored with the response. Same key and same body replays the stored response. Same key with a **different** body returns `IDEMPOTENCY_KEY_REUSED` with 422. Double-clicking checkout must not produce two bookings.

## Accessibility

The seat map is the hard case and most implementations fail it. Keyboard navigable grid with arrow keys, `role="grid"` with proper row and cell semantics, state conveyed by text and pattern rather than colour alone, visible focus rings, live region announcing selection and hold countdown, WCAG AA contrast, `prefers-reduced-motion` respected. `axe` runs in Playwright and fails CI on violations.

## Frontend quality

TanStack Query for all server state. Every view has explicit loading, empty and error states. Route-level error boundary. Responsive to 360px. Optimistic seat selection rolling back cleanly on a 409.

## Observability

`GET /api/health` liveness, `GET /api/health/ready` checking the database. Admin-only `GET /api/admin/stats` exposing live hold count, expired-but-unswept count, waitlist depth per show, outbox backlog, last sweeper run. Graceful shutdown so in-flight transactions finish.

## Repo hygiene

Pre-commit hooks running ruff and mypy. PR template. `docs/adr/` numbered decision records. `docs/backlog.md`. `CONTRIBUTING.md`. `LICENSE`. GitHub repo description and topics set, since that is the first thing a reviewer sees.

## Infrastructure decisions, deliberately

**Docker Compose is for local Postgres only.** It does not extend to production topology.

**No Redis, no Celery, no message broker.** Seat state lives in Postgres. A copy in Redis creates a divergence failure mode where the cache says free and the database says sold, which is exactly the bug this system exists to prevent. Row-level locking in Postgres is the correct serialisation point, and one transaction gives atomicity across hold, booking and waitlist writes that a two-store design cannot. `docs/adr/0003-no-redis.md`.

**SSE fan-out is in-process, and that is a documented constraint.** Correct on one instance, would break on two. Migration path is Postgres `LISTEN`/`NOTIFY`, needing no new infrastructure. `docs/adr/0006-sse-fanout.md` and the README limitations section.

**Neon over Render Postgres and Supabase.** Render free Postgres expires 30 days after creation and is then deleted, which would kill the submission mid-process. Supabase free pauses after a week of inactivity and needs a manual restore. Neon scales to zero but auto-resumes on connection in under two seconds and never expires. `docs/adr/0007-database-hosting.md`.

## Email adapter

`EmailSender` with `send(to, subject, html, attachments)`:

- `ConsoleEmailSender` - stdout, writes the QR PNG to `./tmp/emails/`. Default in dev and tests.
- `SmtpEmailSender` - generic SMTP, env-configured.
- Selected by `EMAIL_BACKEND`.

Do not hardcode a provider. Verify the chosen provider's current free tier at step 12 rather than trusting anything here, since free tiers change. Hard requirement: must send to arbitrary recipients, not only a pre-verified owner address, otherwise the demo can only email Aakrisht.

Delivery goes through the outbox table with retry and exponential backoff, never a direct call inside the request. A booking must not fail because SMTP was briefly unreachable.
