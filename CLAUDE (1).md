# CLAUDE.md - Ticket Booking System

Instruction file for Claude Code. Read this fully before every step.

---

## 1. Working protocol

Non-negotiable. It overrides any instinct to be efficient.

1. **One step at a time.** Execute exactly one numbered step, then stop and report. Do not begin the next step, do not "also fix" something you noticed, do not scaffold ahead. Real defects found outside the current step go into `docs/backlog.md`.
2. **Branch per step.** `git checkout -b step-NN-short-name` off `main`. Never commit to `main` directly.
3. **Verification is mandatory.** Every step lists a verification command. Run it, paste the real output in your report. A step is never complete on the basis of "the code looks correct".
4. **Commit per step**, Conventional Commits form, for example `feat(holds): add seat hold endpoint with row-level locking`. Open a PR against `main` and leave it unmerged. Aakrisht merges.
5. **Report format:**
   - Files touched
   - Verification command plus actual output
   - Decisions made alone, and why
   - Anything that surprised you
   - What the next step will do
6. **No silent degradation.** If a signal exists but nothing consumes it, that is a bug. Add a field, a status, an error code or an event, and something must read it and a test must assert on it. This has been the single most common failure mode across previous projects. Check for it deliberately at the end of every step.
7. **Never mark a step done with a skipped or xfail test.** If a test cannot pass, stop and report why.
8. **`main` is always deployable.** From step 1 onward there is a live hosted URL. It is never broken at the end of a merged PR.

### Definition of Done, applies to every step

- [ ] `ruff check` and `ruff format --check` clean
- [ ] `mypy --strict` clean on backend, `tsc --noEmit` clean on frontend
- [ ] New code has tests, and those tests would fail if the feature were removed
- [ ] CI green on the PR
- [ ] No `TODO`, no commented-out code, no debug prints, no unused imports
- [ ] Any new error condition has a registered code in `app/errors.py`
- [ ] Any new env var is in `.env.example` with a comment
- [ ] Any non-obvious decision is written into `docs/adr/` as a short ADR
- [ ] Any new invariant is added to the traceability table in section 9
- [ ] Any brief requirement newly satisfied is ticked in the compliance matrix in section 2

---

## 2. Requirement compliance matrix

Every line of the assignment brief, mapped. Tick as steps land. **Nothing ships until this table is complete.** This table also goes in the README, because it lets a reviewer confirm coverage without hunting.

### Scope of work

| # | Brief requirement | Step | Proof |
|---|---|---|---|
| S1 | Admin creates and manages venues with seat layout and seat categories | 4 | `test_venues.py` |
| S2 | Organiser can register, log in | 3 | `test_auth.py::test_organiser_self_registration` |
| S3 | Organiser creates movie or event listings with venue, date, time, per-category pricing | 5 | `test_shows.py` |
| S4 | Customer can register, log in | 3 | `test_auth.py` |
| S5 | Customer can browse and filter events | 5, 16 | `test_events.py::test_filters` |
| S6 | Visual seat map with real-time status (available / held / booked) | 6, 10, 17 | `test_seatmap.py`, e2e |
| S7 | Seat hold with configurable TTL, default 600s | 7 | `test_holds.py::test_ttl_configurable` |
| S8 | Held seats shown unavailable to other customers | 6 | `test_seatmap.py::test_held_seat_unavailable_to_others` |
| S9 | Abandoned checkout auto-releases held seats | 8 | `test_holds.py::test_expiry_releases_seat` |
| S10 | Seat map updates in real time on release | 8, 10 | `test_sse.py::test_release_event_delivered` |
| S11 | Two customers cannot hold the same seat simultaneously | 7 | `test_concurrency.py` |
| S12 | Two customers cannot book the same seat simultaneously | 9 | `test_concurrency.py::test_concurrent_checkout_one_booking` |
| S13 | Booking sends email with QR code ticket | 12 | `test_email.py`, `test_qr.py` |
| S14 | QR encodes booking reference | 12 | `test_qr.py::test_qr_decodes_to_reference` |
| S15 | Waitlist join per seat category when sold out | 11 | `test_waitlist.py` |
| S16 | Cancellation offers seat to next customer on waitlist | 12 | `test_waitlist.py::test_cancel_creates_offer` |
| S17 | Offeree receives email with time-limited link | 12 | `test_email.py::test_offer_email_contains_link` |
| S18 | Unclaimed offer rolls to next in line | 13 | `test_waitlist.py::test_offer_cascade` |
| S19 | Customer can view booking history | 19 | e2e |
| S20 | Customer can cancel a booking | 12, 19 | `test_bookings.py::test_cancel` |
| S21 | Organiser can view booking summary and revenue per event | 14 | `test_reporting.py` |

### Technical expectations

| # | Brief requirement | Step | Note |
|---|---|---|---|
| T1 | Backend API, frontend, database | all | |
| T2 | Role-based auth: customer, organiser, admin | 3 | |
| T3 | Seat map stored per show with per-seat status | 2, 6 | See section 6, invariant 1. Satisfied via `show_seats` plus the `show_seat_status` view |
| T4 | Rendered as visual grid on frontend | 17 | |
| T5 | Hold TTL enforced via scheduler or database-level expiry | 6, 8 | Database-level primary, sweeper secondary |
| T6 | Seat status updated on release | 8, 10 | |
| T7 | Concurrency protection, simultaneous attempts must not both succeed | 7, 9 | |
| T8 | Waitlist queue per seat category | 11 | |
| T9 | Auto-assignment and time-limited offer flow on cancellation | 12, 13 | |
| T10 | QR generation on booking | 12 | |
| T11 | Email delivery with QR, any free tier service | 12 | |

### Deliverables

| # | Brief requirement | Step |
|---|---|---|
| D1 | Complete source code | all |
| D2 | README with setup, `.env.example`, API docs, DB schema, hold and waitlist logic | 21 |
| D3 | Hosted application URL | 1, live from then on |
| D4 | System design write-up, 800 words max, four required topics | 21 |

Submission is **the GitHub repository link only**, per the instruction accompanying the brief. The brief's zip deliverable is satisfied by tagging `v1.0.0` and attaching the source archive to a GitHub Release, so the link covers it.

### Evaluation focus, all six

The brief lists **six** criteria, not four. All six get equal structural treatment in the README.

| # | Criterion | Where it is demonstrated |
|---|---|---|
| E1 | Seat hold TTL and auto-release mechanism | Steps 6, 7, 8 |
| E2 | Concurrency protection for simultaneous seat selection | Steps 7, 9, 15 |
| E3 | Waitlist auto-assignment and time-limited offer flow | Steps 11, 12, 13 |
| E4 | Seat map data model and real-time status updates | Steps 2, 6, 10 |
| E5 | QR code generation and email delivery | Step 12 |
| E6 | API design, code structure, and documentation | Sections 4 and 10, steps 0 and 21 |

E6 is not a formality. It is the criterion that the Definition of Done, the OpenAPI curation, the ADRs and the README specification all exist to satisfy. It is also the easiest to lose by accident.

### Explicitly out of scope

Payment processing. The brief describes checkout and pricing but never payment. Do not integrate a gateway. State this in one line in the README so its absence reads as a decision rather than an omission.

---

## 3. What is graded, what impresses, what backfires

The evaluator will not read every line. They will give this ten minutes: open the repo, read the top of the README, maybe watch a GIF, maybe click the hosted URL, skim two or three files, and then try to break the four mechanisms in E1 to E4.

So the work has to be good **and** visible in ninety seconds. Section 10 specifies the README with that in mind. It is the highest-leverage artefact in the repo, not an afterthought.

Two failure modes, in both directions:

- **Underbuilt:** works on the happy path, falls over the moment two tabs are open.
- **Overbuilt:** microservices, GraphQL, Kubernetes, a caching layer, an event bus, CQRS, five layers of abstraction over one CRUD call. This reads as inexperience, not seniority. A senior reviewer is impressed by a small system with hard guarantees and clear reasoning, never by a bigger diagram.

With no deadline the risk is not rushing, it is never shipping. Deploy at step 1 and keep it deployed.

---

## 4. Engineering standards

Cross-cutting. Set up in step 0 so every later step inherits them. Collectively these are how E6 is won.

**Continuous integration.** GitHub Actions on every push and PR: lint, format check, mypy strict, tsc strict, backend tests against a real Postgres service container, `alembic upgrade head` then `downgrade base` then `upgrade head`, frontend build, Playwright e2e with `axe`. Badge in the README. Red build blocks merge.

**Continuous deployment.** `main` auto-deploys to Render. Migrations run as a **pre-deploy command, not on application boot**, so two booting instances cannot race a migration.

**Type safety end to end.** `mypy --strict` on backend, TypeScript `strict` on frontend, and the frontend API client is **generated from the backend OpenAPI schema**, so a backend contract change breaks the frontend build instead of production.

**Structured logging.** `structlog`, JSON in production. Correlation ID from `X-Request-ID` or generated, present in every log line for that request and in every error response body. Seat state transitions logged at INFO with show id, seat id, actor and reason. Never log tokens, passwords or full JWTs.

**Errors.** Single registry in `app/errors.py`. Shape `{"error": {"code": "SEAT_UNAVAILABLE", "message": "...", "request_id": "..."}}`. Codes stable and machine-readable, frontend switches on `code` and never on `message`. No stack trace reaches a client. Global handler catches everything unhandled and returns `INTERNAL_ERROR`.

**Security.**
- Argon2id password hashing.
- Short-lived access JWT plus rotating refresh token stored hashed and revocable. Refresh token in an httpOnly, Secure, SameSite=Lax cookie. Access tokens never in `localStorage`.
- Refresh token reuse detection: presenting an already-rotated token revokes the whole family.
- **Registration accepts `customer` and `organiser` only.** Admin is seeded, never self-registerable. A request attempting to register as admin returns 422. This needs an explicit test, because it is the kind of privilege escalation a reviewer will actually try.
- Rate limiting on login, register, hold creation and offer claim. In-process token bucket keyed on IP plus user. No Redis.
- CORS locked to the known origin, never `*`.
- All input validated by Pydantic. No string interpolation into SQL.
- Secrets only from env. A committed secret is a step failure.
- Security headers middleware: HSTS, X-Content-Type-Options, Referrer-Policy, restrictive CSP.
- Booking references are Crockford base32, 8 characters, from a CSPRNG. **Never sequential**, since a sequential reference leaks total booking volume to any ticket holder.
- Offer tokens and refresh tokens stored hashed, never plaintext.
- **The seat map never leaks holder identity.** Other customers see a seat as unavailable, not who holds it.

**Idempotency.** `POST /api/bookings` and `POST /api/offers/{token}/claim` accept an `Idempotency-Key` header. Key, user, endpoint and a hash of the request body are stored with the response. Same key and same body replays the stored response. Same key with a **different** body returns `IDEMPOTENCY_KEY_REUSED` with 422. Double-clicking checkout must not produce two bookings.

**Accessibility.** The seat map is the hard case and most implementations fail it. Keyboard navigable grid with arrow keys, `role="grid"` with proper row and cell semantics, state conveyed by text and pattern rather than colour alone, visible focus rings, live region announcing selection and hold countdown, WCAG AA contrast, `prefers-reduced-motion` respected. `axe` runs in Playwright and fails CI on violations.

**Frontend quality.** TanStack Query for all server state. Every view has explicit loading, empty and error states. Route-level error boundary. Responsive to 360px. Optimistic seat selection rolling back cleanly on a 409.

**Observability.** `GET /api/health` liveness, `GET /api/health/ready` checking the database. Admin-only `GET /api/admin/stats` exposing live hold count, expired-but-unswept count, waitlist depth per show, outbox backlog, last sweeper run. Graceful shutdown so in-flight transactions finish.

**Repo hygiene.** Pre-commit hooks running ruff and mypy. PR template. `docs/adr/` numbered decision records. `docs/backlog.md`. `CONTRIBUTING.md`. `LICENSE`. GitHub repo description and topics set, since that is the first thing a reviewer sees.

---

## 5. Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | FastAPI, SQLAlchemy 2.x, Alembic | Python 3.11 |
| DB | PostgreSQL, Neon in prod | `docker compose up` for local |
| Frontend | React, Vite, TypeScript strict | Tailwind, no component library |
| Server state | TanStack Query | |
| Real-time | Server-Sent Events | one stream per show |
| Auth | JWT access plus revocable refresh | customer, organiser, admin |
| QR | `qrcode[pil]` | |
| Email | adapter interface, see below | swappable provider |
| Backend tests | pytest, httpx, real Postgres | never SQLite |
| E2E | Playwright plus `axe` | |
| Lint and types | ruff, mypy strict, tsc strict | |
| CI/CD | GitHub Actions, Render auto-deploy | |
| Deploy | single Render web service | FastAPI serves the built Vite bundle |

### Neon specifics, which will bite otherwise

Use the **pooled** connection string. Neon closes idle connections aggressively, so SQLAlchemy needs `pool_pre_ping=True` and a modest `pool_recycle`. Without this the app throws stale-connection errors after quiet periods, which on a free tier is most of the time. Verify by leaving the app idle ten minutes then hitting it.

### On infrastructure, deliberately

**Docker Compose is for local Postgres only.** It does not extend to production topology.

**No Redis, no Celery, no message broker.** Considered, not a shortcut. Seat state lives in Postgres. A copy in Redis creates a divergence failure mode where the cache says free and the database says sold, which is exactly the bug this system exists to prevent. Row-level locking in Postgres is the correct serialisation point, and one transaction gives atomicity across hold, booking and waitlist writes that a two-store design cannot. `docs/adr/0003-no-redis.md`.

**SSE fan-out is in-process, and that is a documented constraint.** Correct on one instance, would break on two. Migration path is Postgres `LISTEN`/`NOTIFY`, which needs no new infrastructure. State it in `docs/adr/0006-sse-fanout.md` and in the README limitations section.

**Never test against SQLite.** The guarantees here are Postgres-specific.

### Email adapter

`EmailSender` with `send(to, subject, html, attachments)`:

- `ConsoleEmailSender` - stdout, writes the QR PNG to `./tmp/emails/`. Default in dev and tests.
- `SmtpEmailSender` - generic SMTP, env-configured.
- Selected by `EMAIL_BACKEND`.

Do not hardcode a provider. Verify the chosen provider's current free tier at step 12 rather than trusting anything here. Hard requirement: must send to arbitrary recipients, not only a pre-verified owner address, otherwise the demo can only email Aakrisht.

Delivery goes through an outbox table with retry and exponential backoff, never a direct call inside the request. A booking must not fail because SMTP was briefly unreachable.

---

## 6. Data model and invariants

The assignment turns on this section.

### Core tables

```
users(id, email uniq, password_hash, full_name, role, created_at, updated_at)
refresh_tokens(id, user_id, token_hash uniq, family_id, expires_at,
               revoked_at, user_agent, created_at)
idempotency_keys(id, key, user_id, endpoint, request_hash,
                 response_status, response_body, created_at)   -- uniq(key, user_id, endpoint)

venues(id, name, address, timezone, created_by, created_at)
seat_categories(id, venue_id, name, display_order)             -- Premium, Standard
seats(id, venue_id, category_id, row_label, seat_number, x, y)

events(id, organiser_id, venue_id, title, kind, description, poster_url, created_at)
                                                               -- kind: 'movie' | 'concert'
shows(id, event_id, starts_at, hold_ttl_seconds, offer_ttl_seconds, status)
show_prices(id, show_id, category_id, price_cents)
show_seats(id, show_id, seat_id, category_id, price_cents)     -- materialised on show create

seat_holds(id, show_seat_id, user_id, created_at, expires_at,
           released_at, released_reason, booking_id, active_key)
bookings(id, show_id, user_id, reference uniq, status, total_cents,
         contact_email, created_at, cancelled_at, cancelled_by)
booking_seats(id, booking_id, show_seat_id, price_cents, active bool)

waitlist_entries(id, show_id, category_id, user_id, quantity,
                 status, position, created_at, fulfilled_at)
waitlist_offers(id, waitlist_entry_id, token_hash uniq, created_at,
                expires_at, claimed_at, expired_at, booking_id)
waitlist_offer_seats(id, waitlist_offer_id, show_seat_id, active bool)

email_outbox(id, to_addr, subject, body_html, attachment_path,
             status, attempts, next_attempt_at, last_error, created_at, sent_at)
seat_events(id, show_seat_id, from_status, to_status, actor_user_id,
            reason, created_at)                                -- append-only audit
```

Index every foreign key. Add covering indexes for the seat map read and the waitlist head query. Justify each index in the migration docstring.

### Invariant 1: per-seat status is computed, and exposed through a view

The brief says the seat map is *"stored per show with per-seat status"*. The seat map **is** stored per show, in `show_seats`. Status is not stored as a column, and this is deliberate: a denormalised status column is precisely what double-sells a seat when a sweeper misses a tick, because the column and the authoritative hold and booking rows can disagree.

To satisfy the wording literally and keep a single source of truth, create a database view:

```sql
CREATE VIEW show_seat_status AS
SELECT ss.id AS show_seat_id, ss.show_id, ss.seat_id, ss.category_id, ss.price_cents,
       CASE
         WHEN <active booking_seat exists>        THEN 'booked'
         WHEN <live hold exists>                  THEN 'held'
         WHEN <live offer seat exists>            THEN 'offered'
         ELSE 'available'
       END AS status
FROM show_seats ss;
```

Per-seat status is then queryable per show in one statement, with zero divergence risk because it is computed at query time rather than cached. `docs/adr/0002-derived-seat-status.md` explains the choice, and the design write-up says so in one sentence. Do not skip that sentence: a reviewer checking the brief against the schema needs to see that the deviation was reasoned, not missed.

**Status vocabulary at the API boundary.** The brief names three statuses. Return exactly `available`, `held`, `booked` to customers. An `offered` seat is reported as `held` to everyone except the offeree, who sees a dedicated field on their own offer view. The richer internal model stays internal.

**Expiry is lazy.** A hold expires the instant `expires_at < now()`, whether or not a background job has run. Every read path evaluates this in SQL, including the view. The sweeper only writes tombstones, publishes events and drives the waitlist cascade. If the Render instance sleeps and the sweeper misses ticks, correctness must not change, only notification latency. **Any design where a missed tick can double-sell a seat is wrong.** Test with the scheduler switched off.

### Invariant 2: concurrency is enforced by the database

Application-level check-then-insert loses the race. The hold transaction:

```sql
BEGIN;
SELECT id FROM show_seats WHERE id = ANY(:seat_ids) ORDER BY id FOR UPDATE;
-- lazy expiry write: NULL out active_key on holds for these seats
--   where expires_at < now() and released_at is null
-- conflict check against booking_seats.active, live seat_holds, live waitlist_offer_seats
INSERT INTO seat_holds (...);
COMMIT;
```

`ORDER BY id` is required, otherwise two requests with overlapping seat sets deadlock.

Belt and braces on top of the row lock:

- `CREATE UNIQUE INDEX ON seat_holds (active_key) WHERE active_key IS NOT NULL;`
- `CREATE UNIQUE INDEX ON booking_seats (show_seat_id) WHERE active;`
- `CREATE UNIQUE INDEX ON waitlist_offer_seats (show_seat_id) WHERE active;`
- `CREATE UNIQUE INDEX ON waitlist_entries (show_id, category_id, user_id) WHERE status = 'waiting';`

All four must exist and be provably load-bearing. Step 2 includes raw-SQL tests asserting each rejects its duplicate with the application layer bypassed.

`READ COMMITTED` with explicit row locks, not `SERIALIZABLE`. ADR the choice: `SERIALIZABLE` is also correct but pushes serialisation failures onto the client as retries, while explicit locking makes the contention point visible in the code.

### Invariant 3: an offered seat is not public

A cancelled seat offered to a waitlisted customer is locked to them for `offer_ttl_seconds`. Same lazy expiry rule as holds.

### Invariant 4: waitlist offers are all-or-nothing on quantity

An entry with `quantity = 2` is never offered a single seat. Nobody wants one of two tickets, and a partial offer strands a seat.

When a cancellation frees seats, process each affected category independently. Walk waiting entries in `position` order and offer to the **first entry whose `quantity` is less than or equal to the number of currently free seats in that category**. Entries too large are skipped, not removed, and keep their position for a future release. Record every skip in `seat_events` with a reason. One cancellation may generate several offers, one, or none, all in one transaction.

### Invariant 5: sold out is per category

A customer may join the waitlist for a category with zero `available` seats for that show. Held seats count as unavailable, and the check re-evaluates on every request. One active entry per user, show and category, enforced by the partial unique index above.

### Invariant 6: cancellation has a cutoff

A booking cannot be cancelled after its show has started. Return `SHOW_ALREADY_STARTED`. Without this rule a customer can cancel mid-performance and trigger a pointless waitlist offer for a seat nobody can use.

### Invariant 7: history is append-only

Do not delete holds, offers or waitlist entries. Set `released_at`, `expired_at`, `status`. Every transition also writes a `seat_events` row. When asked how you would debug a reported double-booking, the answer is one query against `seat_events`.

### Invariant 8: time comes from the database

All timestamps `TIMESTAMPTZ`, all UTC, `now()` evaluated in Postgres, never in Python. A clock-skewed app server must not be able to cause a double sell. `venues.timezone` is for display only.

---

## 7. Failure modes

Build to this table, then publish it in the README.

| Failure | Behaviour | Guarantee |
|---|---|---|
| Sweeper stops or instance sleeps | Expired holds still read available via lazy expiry | Correctness unaffected, notification delayed |
| Two users select the same seat at once | Row lock serialises, one 201 and one 409 | No double allocation |
| User double-clicks checkout | Idempotency key replays first response | Exactly one booking |
| SMTP provider down | Outbox retries with backoff, booking already committed | Booking never fails on email |
| Offer link opened after expiry | `OFFER_EXPIRED`, seat already rolled onward | No stale claim |
| Browser closed mid-checkout | Hold expires at TTL, seat auto-releases | No permanent seat leak |
| DB connection drops mid-transaction | Whole transaction rolls back | No orphan state |
| Neon idles the connection out | `pool_pre_ping` reconnects transparently | No user-visible error |
| Cancellation after show start | Rejected with `SHOW_ALREADY_STARTED` | No pointless offer |
| Second app instance added | SSE fan-out would miss cross-instance events | Known limitation, `LISTEN`/`NOTIFY` is the path |

---

## 8. Roadmap

Twenty-one steps. Steps 1 to 15 are the graded core and its hardening.

### Phase 0 - foundations

**Step 0. Repo, tooling and CI.**
Layout, `pyproject.toml`, ruff and mypy config, pre-commit, `docker-compose.yml` with Postgres, GitHub Actions workflow, PR template, `docs/adr/0001-record-architecture-decisions.md`, `docs/backlog.md`, `LICENSE`, `.env.example` skeleton, GitHub repo description and topics.
*Verify:* push a trivial PR, CI green, then a deliberate lint error turning it red. Show both runs.

**Step 1. App skeleton, database, first deploy.**
App factory, Pydantic Settings, structlog with correlation ID middleware, global exception handler, error registry, Alembic initialised, Neon pooled connection with `pool_pre_ping`, `GET /api/health` and `/api/health/ready`. Render service created, auto-deploy from `main`, migrations as pre-deploy command.
*Verify:* the **hosted** `/api/health/ready` returns ok. Force a local database outage, confirm 503 with correlation ID and no stack trace. Leave the deployed app idle ten minutes, hit it, confirm no stale-connection error.

**Step 2. Schema, migrations and the status view.**
Every table in section 6, every constraint, all four partial unique indexes, all FK indexes, the `show_seat_status` view.
*Verify:* `upgrade head`, `downgrade base`, `upgrade head` clean. `\d` output showing the partial indexes. Raw-SQL script proving each index rejects its duplicate. `SELECT status, count(*) FROM show_seat_status GROUP BY status` runs.

**Step 3. Auth, roles and rate limiting.**
Register (customer and organiser only), login, refresh rotation with family revocation, logout, `require_role`, rate limits, security headers. Seed admin.
*Verify:* pytest covering happy path, wrong password, expired access token, refresh rotation, **reuse of a rotated refresh token revoking the family**, **registration as admin rejected 422**, customer hitting an organiser route getting 403 not 500, rate limiter returning 429.

### Phase 1 - the graded core

**Step 4. Venues, categories and seats (admin).**
Venue with grid layout in one call, for example 10 rows by 12 with A to C Premium. Timezone required. Pagination. Organisers get read access to venues so they can attach shows.
*Verify:* create a 10x12 venue, `GET /api/venues/{id}` returns 120 seats with correct categories. Organiser can list venues, cannot create one.

**Step 5. Events and shows (organiser).**
Event CRUD with `kind` in movie or concert, show creation with date, time and per-category pricing, `show_seats` materialised in one transaction, public event list with filters on kind, date, venue and title search, plus pagination.
*Verify:* creating a show on the 120-seat venue inserts exactly 120 `show_seats` with prices resolved from `show_prices`. A rolled-back creation leaves zero orphans. Each filter asserted independently.

**Step 6. Seat map read and lazy expiry.**
`GET /api/shows/{id}/seatmap` reading `show_seat_status`, public, one query, no N+1, no holder identity in the payload.
*Verify:* insert a hold via raw SQL with `expires_at = now() - interval '1 second'`, **scheduler not running**, call the endpoint, assert `available`. Assert query count for a 2000-seat show is constant and report p95 latency. Assert the response contains no user id for held seats.

**Step 7. Seat hold with concurrency protection.**
`POST /api/shows/{id}/holds`. TTL from `hold_ttl_seconds`, default 600, env-overridable for tests.
*Verify:* the marquee test. 50 concurrent requests for one seat from 50 users: exactly one 201, forty-nine 409. Overlapping multi-seat requests: no partial double-allocation. Reverse-order multi-seat pair proving the deadlock guard. Print actual counts.

**Step 8. Internal event bus and release paths.**
In-process publisher with a typed `SeatStateChanged` event. Explicit `DELETE /api/holds/{id}`, sweeper tombstoning expired holds, nulling `active_key`, writing `seat_events`, publishing to the bus. **The bus has a test subscriber asserting events are published**, so the signal is consumed from the moment it exists. SSE attaches in step 10.
*Verify:* `HOLD_TTL_SECONDS=3`, create a hold, poll, assert available to held to available with real timestamps. Assert the bus received matching events. Kill the sweeper mid-run and assert the seat map is still correct.

**Step 9. Checkout to booking, with idempotency.**
`POST /api/bookings` converting live holds into a confirmed booking in one transaction: reference, `booking_seats` active, `seat_holds.booking_id`, null `active_key`, `seat_events`, outbox row, contact email captured.
*Verify:* happy path, expired hold 409, another user's hold 403, two concurrent checkouts on one hold producing exactly one booking, same key twice returning the identical response with one booking in the database, same key with a different body returning 422.

**Step 10. SSE transport.**
`GET /api/shows/{id}/stream` subscribing to the step 8 bus. Heartbeat, reconnection with `Last-Event-ID`, clean disconnect.
*Verify:* two clients subscribed, one takes a hold, the other receives within a second. An abruptly dropped client leaks no connection or task, asserted by a count before and after.

**Step 11. Waitlist join.**
`POST /api/shows/{id}/waitlist` with quantity, sold-out check per invariant 5, position assignment, `DELETE` to leave, `GET` own position.
*Verify:* sell out a small show, three customers join, positions 1 to 3 asserted, duplicate join rejected 409, join on a non-sold-out category rejected, leaving does not corrupt remaining positions.

**Step 12. Cancellation, offer creation, QR and email.**
`POST /api/bookings/{id}/cancel` with the invariant 6 cutoff, freeing seats, then per category running the invariant 4 allocation. Offer rows with hashed token, seat lock, queued email with time-limited link. **QR encodes the booking reference string itself**, per S14. The ticket email separately carries a verification link. Outbox worker with retry and backoff.
*Verify:* cancel one seat with a `quantity=2` entry at position 1 and `quantity=1` at position 2, assert the offer goes to **position 2** and position 1 keeps its place with a skip in `seat_events`. Cancel two seats and assert position 1 is served. Decode the QR PNG **programmatically** and assert it equals the booking reference exactly. Cancel after show start rejected. Force an SMTP failure, assert retry with backoff and that the booking is unaffected.

**Step 13. Offer claim and expiry cascade.**
`GET /api/offers/{token}`, `POST /api/offers/{token}/claim` with idempotency. Sweeper rolls expired offers onward per invariant 4.
*Verify:* `OFFER_TTL_SECONDS=5`, lapse three times, assert the offer walks 1 to 2 to 3 with correct timestamps and three outbox rows. Run where 2 claims in time: 3 never gets an offer. Claim one second after expiry rejected cleanly. Claim after the seat rolled onward rejected, seat still belongs to the new offeree.

**Step 14. Organiser reporting and admin stats.**
Booking summary and revenue **per event**, aggregated across that event's shows and broken down by category, gross and net of cancellations. `GET /api/admin/stats`.
*Verify:* revenue cross-checked against a direct SQL sum, both pasted in the PR. Cancelled bookings excluded from net, included in gross. An event with two shows sums correctly.

**Step 15. Contention benchmark.**
Script driving sustained concurrent load at hold and checkout on a fully seated show. Reports throughput, latency percentiles, conflict rate, and a final integrity assertion that seats sold equals seats booked with zero double-allocations.
*Verify:* run it, commit `docs/benchmark.md`, paste the summary into the README. Most persuasive artefact in the repo, because it proves E2 rather than claiming it.

### Phase 2 - frontend

**Step 16. Shell, auth and event browse.**
Routing, auth context, generated API client from OpenAPI, TanStack Query, error boundaries, login and register with role choice between customer and organiser, event list with filters, event detail.
*Verify:* `tsc --noEmit` clean, generated client in use, screenshots of loading, empty and error states for every view.

**Step 17. Seat map and checkout.**
Visual grid, colour plus pattern plus text, live SSE updates, selection, hold countdown, checkout, confirmation with QR.
*Verify:* two browsers side by side, one holds, the other greys out within a second without refresh. Countdown reaching zero releases the selection. Screen recording in the PR.

**Step 18. Accessibility pass.**
Keyboard grid navigation, ARIA grid semantics, live region for selection and countdown, focus management, contrast, reduced motion.
*Verify:* a full purchase completed **without touching the mouse**, recorded. `axe` clean, wired into CI.

**Step 19. Booking history, waitlist and dashboards.**
Booking history with cancel and QR re-display, waitlist join and queue position, offer claim page with its own countdown, organiser dashboard, admin venue management.
*Verify:* manual walkthrough plus screenshots. Queue position updates after someone ahead is served. Cancel disabled with an explanation once the show has started.

**Step 20. Playwright e2e.**
Register to browse to hold to book to QR. Sold out to waitlist to cancellation to offer link to claim. Hold expiry releasing a seat. Two-context concurrency on one seat.
*Verify:* green locally and in CI, run twice consecutively to prove it is not flaky.

### Phase 3 - ship

**Step 21. Seed, documentation, release.**
Seed script with a demo venue, several events across both kinds, one deliberately sold out with a populated waitlist, demo credentials for all three roles. README per section 10. ADR index. Design write-up, 800 words maximum, **four sections matching the brief's four required topics**: seat hold and TTL mechanism, concurrency prevention, waitlist auto-assignment flow, time-limited offer handling. Tag `v1.0.0` and attach the source archive to a GitHub Release.
*Verify:* clean clone, follow the README verbatim, reach a running app. Full flow against production with a real QR email received. `wc -w` on the write-up under 800. Compliance matrix in section 2 fully ticked. Demo GIF present.

---

## 9. Test traceability

Maintain `docs/test-traceability.md` mapping every invariant in section 6, every row in section 7, and every requirement in section 2 to the named test that proves it. Coverage percentage is a weak metric and is not the target. This table is the target, and it is what to point an interviewer at.

| Invariant | Test |
|---|---|
| 1, lazy expiry without scheduler | `test_seatmap.py::test_expired_hold_reads_available_with_no_scheduler` |
| 1, three-status API vocabulary | `test_seatmap.py::test_offered_seat_reported_as_held_to_others` |
| 2, concurrent holds | `test_concurrency.py::test_fifty_concurrent_holds_one_winner` |
| 2, index is load-bearing | `test_concurrency.py::test_partial_unique_index_rejects_duplicate_raw_sql` |
| 2, deadlock guard | `test_concurrency.py::test_reverse_order_multiseat_no_deadlock` |
| 3, offered seat not public | `test_waitlist.py::test_offered_seat_unavailable_to_others` |
| 4, quantity all-or-nothing | `test_waitlist.py::test_single_seat_skips_quantity_two_entry` |
| 5, sold out per category | `test_waitlist.py::test_join_rejected_when_category_not_sold_out` |
| 6, cancellation cutoff | `test_bookings.py::test_cancel_rejected_after_show_start` |
| 7, audit completeness | `test_audit.py::test_every_transition_writes_seat_event` |
| 8, database time | `test_time.py::test_expiry_uses_db_now_not_python_now` |

A step that adds an invariant without adding a row here is incomplete.

---

## 10. README specification

The README is what gets this shortlisted. Order it for a reviewer with ten minutes, not for completeness.

1. One-line description, CI badge, hosted URL, note that a free tier cold start takes about a minute
2. **Demo GIF**, thirty to sixty seconds: seat selection, a live update in a second browser, the QR email. A reviewer who will not wait out a cold start will still watch this.
3. Demo credentials for all three roles
4. **All six evaluation criteria as headings**, each with three or four sentences and links to the code and the test that proves it. E5 and E6 get real sections, not a footnote.
5. Concurrency test output, pasted, so the reviewer does not have to run it
6. Benchmark summary from step 15
7. Requirement compliance matrix from section 2
8. Architecture diagram and the failure mode table from section 7
9. Setup guide, `.env.example`, API docs link, ERD
10. Seat hold and waitlist logic in prose
11. Known limitations, including SSE single-instance and payment being out of scope
12. ADR index

---

## 11. Conventions

- Env-driven config: `HOLD_TTL_SECONDS` default 600, `OFFER_TTL_SECONDS`, `JWT_SECRET`, `DATABASE_URL`, `EMAIL_BACKEND`, SMTP settings, `FRONTEND_BASE_URL`, `RATE_LIMIT_*`.
- API prefix `/api`. No `/v1` unless justified, and ADR the decision rather than adding it reflexively.
- Money in integer cents. No float near a price.
- Backend tests in `backend/tests/`, concurrency tests in `backend/tests/test_concurrency.py` so a reviewer finds them in thirty seconds.
- OpenAPI curated deliberately: tags, summaries, response models, documented error responses, realistic examples. This is a direct E6 input, not decoration.
- Prose in the README, ADRs and write-up uses plain hyphens, not em dashes.

---

## 12. Final gate

Do not declare the project complete until all of these are true:

- [ ] Section 2 compliance matrix fully ticked, every row
- [ ] All six evaluation criteria have their own README section
- [ ] Hosted URL live, full flow completed against production, real QR email received
- [ ] Design write-up under 800 words with the brief's four sections
- [ ] `docs/test-traceability.md` complete
- [ ] Demo GIF, demo credentials, benchmark table, concurrency output all in the README
- [ ] `v1.0.0` tagged with the source archive attached to the Release
- [ ] Clean clone plus README instructions reaches a running app with no undocumented step
