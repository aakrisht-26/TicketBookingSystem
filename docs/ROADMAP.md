# Roadmap

Twenty-one steps. Read before starting any step. Steps 1 to 15 are the graded core and its hardening. Do not start frontend polish before they are done.

## Phase 0 - foundations

**Step 0. Repo, tooling and CI.**
Read `docs/STANDARDS.md` and `docs/COMPLIANCE.md` first. Layout, `pyproject.toml`, ruff and mypy config, pre-commit, `docker-compose.yml` with Postgres, GitHub Actions workflow, PR template, `docs/adr/0001-record-architecture-decisions.md`, `docs/backlog.md`, `docs/test-traceability.md` skeleton, `LICENSE`, `.env.example` skeleton, GitHub repo description and topics.
*Verify:* push a trivial PR, CI green, then a deliberate lint error turning it red. Show both runs.

**Step 1. App skeleton, database, first deploy.**
App factory, Pydantic Settings, structlog with correlation ID middleware, global exception handler, error registry, Alembic initialised, Neon pooled connection with `pool_pre_ping`, `GET /api/health` and `/api/health/ready`. Render service created, auto-deploy from `main`, migrations as pre-deploy command.
*Verify:* the **hosted** `/api/health/ready` returns ok. Force a local database outage, confirm 503 with correlation ID and no stack trace. Leave the deployed app idle ten minutes, hit it, confirm no stale-connection error.

**Step 2. Schema, migrations and the status view.**
Read `docs/DATA-MODEL.md`. Every table, every constraint, all four partial unique indexes, all FK indexes, the `show_seat_status` view.
*Verify:* `upgrade head`, `downgrade base`, `upgrade head` clean. `\d` output showing the partial indexes. Raw-SQL script proving each index rejects its duplicate. `SELECT status, count(*) FROM show_seat_status GROUP BY status` runs.

**Step 3. Auth, roles and rate limiting.**
Read `docs/STANDARDS.md` security section. Register (customer and organiser only), login, refresh rotation with family revocation, logout, `require_role`, rate limits, security headers. Seed admin.
*Verify:* pytest covering happy path, wrong password, expired access token, refresh rotation, **reuse of a rotated refresh token revoking the family**, **registration as admin rejected 422**, customer hitting an organiser route getting 403 not 500, rate limiter returning 429.

## Phase 1 - the graded core

**Step 4. Venues, categories and seats (admin).**
Venue with grid layout in one call, for example 10 rows by 12 with A to C Premium. Timezone required. Pagination. Organisers get read access to venues so they can attach shows.
*Verify:* create a 10x12 venue, `GET /api/venues/{id}` returns 120 seats with correct categories. Organiser can list venues, cannot create one.

**Step 5. Events and shows (organiser).**
Event CRUD with `kind` in movie or concert, show creation with date, time and per-category pricing, `show_seats` materialised in one transaction, public event list with filters on kind, date, venue and title search, plus pagination.
*Verify:* creating a show on the 120-seat venue inserts exactly 120 `show_seats` with prices resolved from `show_prices`. A rolled-back creation leaves zero orphans. Each filter asserted independently.

**Step 6. Seat map read and lazy expiry.**
Read `docs/DATA-MODEL.md` invariant 1. `GET /api/shows/{id}/seatmap` reading `show_seat_status`, public, one query, no N+1, no holder identity in the payload.
*Verify:* insert a hold via raw SQL with `expires_at = now() - interval '1 second'`, **scheduler not running**, call the endpoint, assert `available`. Assert query count for a 2000-seat show is constant and report p95 latency. Assert the response contains no user id for held seats.

**Step 7. Seat hold with concurrency protection.**
Read `docs/DATA-MODEL.md` invariant 2. `POST /api/shows/{id}/holds`. TTL from `hold_ttl_seconds`, default 600, env-overridable for tests.
*Verify:* the marquee test. 50 concurrent requests for one seat from 50 users: exactly one 201, forty-nine 409. Overlapping multi-seat requests: no partial double-allocation. Reverse-order multi-seat pair proving the `ORDER BY id` deadlock guard. Print actual counts.

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
Read `docs/DATA-MODEL.md` invariant 5. `POST /api/shows/{id}/waitlist` with quantity, sold-out check, position assignment, `DELETE` to leave, `GET` own position.
*Verify:* sell out a small show, three customers join, positions 1 to 3 asserted, duplicate join rejected 409, join on a non-sold-out category rejected, leaving does not corrupt remaining positions.

**Step 12. Cancellation, offer creation, QR and email.**
Read `docs/DATA-MODEL.md` invariants 4 and 6. `POST /api/bookings/{id}/cancel` with the cutoff, freeing seats, then per category running the all-or-nothing allocation. Offer rows with hashed token, seat lock, queued email with time-limited link. **QR encodes the booking reference string itself.** The ticket email separately carries a verification link. Outbox worker with retry and backoff.
*Verify:* cancel one seat with a `quantity=2` entry at position 1 and `quantity=1` at position 2, assert the offer goes to **position 2** and position 1 keeps its place with a skip in `seat_events`. Cancel two seats and assert position 1 is served. Decode the QR PNG **programmatically** and assert it equals the booking reference exactly. Cancel after show start rejected. Force an SMTP failure, assert retry with backoff and that the booking is unaffected.

**Step 13. Offer claim and expiry cascade.**
`GET /api/offers/{token}`, `POST /api/offers/{token}/claim` with idempotency. Sweeper rolls expired offers onward per invariant 4.
*Verify:* `OFFER_TTL_SECONDS=5`, lapse three times, assert the offer walks 1 to 2 to 3 with correct timestamps and three outbox rows. Run where 2 claims in time: 3 never gets an offer. Claim one second after expiry rejected cleanly. Claim after the seat rolled onward rejected, seat still belongs to the new offeree.

**Step 14. Organiser reporting and admin stats.**
Booking summary and revenue **per event**, aggregated across that event's shows and broken down by category, gross and net of cancellations. `GET /api/admin/stats`.
*Verify:* revenue cross-checked against a direct SQL sum, both pasted in the PR. Cancelled bookings excluded from net, included in gross. An event with two shows sums correctly.

**Step 15. Contention benchmark.**
Script driving sustained concurrent load at hold and checkout on a fully seated show. Reports throughput, latency percentiles, conflict rate, and a final integrity assertion that seats sold equals seats booked with zero double-allocations. Truncate benchmark data afterwards, since Neon free storage is 0.5 GB.
*Verify:* run it, commit `docs/benchmark.md`, paste the summary into the README. Most persuasive artefact in the repo, because it proves the concurrency guarantee rather than claiming it.

## Phase 2 - frontend

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

## Phase 3 - ship

**Step 21. Seed, documentation, release.**
Seed script with a demo venue, several events across both kinds, one deliberately sold out with a populated waitlist, demo credentials for all three roles. README per the spec below. ADR index. Design write-up, 800 words maximum, **four sections matching the brief's four required topics**: seat hold and TTL mechanism, concurrency prevention, waitlist auto-assignment flow, time-limited offer handling. Tag `v1.0.0` and attach the source archive to a GitHub Release.
*Verify:* the final gate below, every line.

---

## README specification

The README is what gets this shortlisted. A reviewer gives it ten minutes. Order it for that reviewer, not for completeness.

1. One-line description, CI badge, hosted URL, note that a free tier cold start takes about a minute
2. **Demo GIF**, thirty to sixty seconds: seat selection, a live update in a second browser, the QR email. A reviewer who will not wait out a cold start will still watch this.
3. Demo credentials for all three roles
4. **All six evaluation criteria as headings**, each with three or four sentences and links to the code and the test that proves it. E5 (QR and email) and E6 (API design, code structure, documentation) get real sections, not a footnote.
5. Concurrency test output, pasted, so the reviewer does not have to run it
6. Benchmark summary from step 15
7. Requirement compliance matrix from `docs/COMPLIANCE.md`
8. Architecture diagram and the failure mode table from `docs/DATA-MODEL.md`
9. Setup guide, `.env.example`, API docs link, ERD
10. Seat hold and waitlist logic in prose
11. Known limitations: SSE single-instance, payment out of scope, seed script as the disaster recovery story
12. ADR index

---

## Final gate

Do not declare the project complete until all of these are true:

- [ ] `docs/COMPLIANCE.md` matrix fully ticked, every row
- [ ] All six evaluation criteria have their own README section
- [ ] Hosted URL live, full flow completed against production, real QR email received
- [ ] Design write-up under 800 words with the brief's four sections
- [ ] `docs/test-traceability.md` complete
- [ ] Demo GIF, demo credentials, benchmark table, concurrency output all in the README
- [ ] `v1.0.0` tagged with the source archive attached to the Release
- [ ] Clean clone plus README instructions reaches a running app with no undocumented step
