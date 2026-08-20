# Data model and invariants

Read before steps 2, 6, 7, 8, 9, 11, 12, 13. The assignment turns on this document.

## Core tables

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

## Invariant 1: per-seat status is computed, and exposed through a view

The brief says the seat map is *"stored per show with per-seat status"*. The seat map **is** stored per show, in `show_seats`. Status is not stored as a column, and this is deliberate: a denormalised status column is precisely what double-sells a seat when it drifts from the authoritative hold and booking rows.

To satisfy the wording literally and keep a single source of truth, create a view:

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

Per-seat status is then queryable per show in one statement with zero divergence risk, because it is computed at query time rather than cached. Write `docs/adr/0002-derived-seat-status.md`, and say so in one sentence in the design write-up. Do not skip that sentence: a reviewer checking the brief against the schema needs to see the deviation was reasoned, not missed.

**Status vocabulary at the API boundary.** The brief names three statuses. Return exactly `available`, `held`, `booked` to customers. An `offered` seat is reported as `held` to everyone except the offeree, who sees a dedicated field on their own offer view. The richer internal model stays internal.

**Expiry is lazy.** A hold expires the instant `expires_at < now()`, whether or not a background job has run. Every read path evaluates this in SQL, including the view. The sweeper only writes tombstones, publishes events and drives the waitlist cascade. If the Render instance sleeps and the sweeper misses ticks, correctness must not change, only notification latency. **Any design where a missed tick can double-sell a seat is wrong.** Test with the scheduler switched off.

## Invariant 2: concurrency is enforced by the database

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
  `active_key` is set to `show_seat_id` while live, `NULL` on release, expiry or conversion.
- `CREATE UNIQUE INDEX ON booking_seats (show_seat_id) WHERE active;`
- `CREATE UNIQUE INDEX ON waitlist_offer_seats (show_seat_id) WHERE active;`
- `CREATE UNIQUE INDEX ON waitlist_entries (show_id, category_id, user_id) WHERE status = 'waiting';`

All four must exist and be provably load-bearing. Step 2 includes raw-SQL tests asserting each rejects its duplicate with the application layer bypassed.

`READ COMMITTED` with explicit row locks, not `SERIALIZABLE`. ADR the choice: `SERIALIZABLE` is also correct but pushes serialisation failures onto the client as retries, while explicit locking makes the contention point visible in the code.

## Invariant 3: an offered seat is not public

A cancelled seat offered to a waitlisted customer is locked to them for `offer_ttl_seconds`. Same lazy expiry rule as holds.

## Invariant 4: waitlist offers are all-or-nothing on quantity

An entry with `quantity = 2` is never offered a single seat. Nobody wants one of two tickets, and a partial offer strands a seat.

When a cancellation frees seats, process each affected category independently. Walk waiting entries in `position` order and offer to the **first entry whose `quantity` is less than or equal to the number of currently free seats in that category**. Entries too large are skipped, not removed, and keep their position for a future release. Record every skip in `seat_events` with a reason. One cancellation may generate several offers, one, or none, all in one transaction.

## Invariant 5: sold out is per category

A customer may join the waitlist for a category with zero `available` seats for that show. Held seats count as unavailable, and the check re-evaluates on every request. One active entry per user, show and category, enforced by the partial unique index above.

## Invariant 6: cancellation has a cutoff

A booking cannot be cancelled after its show has started. Return `SHOW_ALREADY_STARTED`. Without this a customer can cancel mid-performance and trigger a pointless waitlist offer for a seat nobody can use.

## Invariant 7: history is append-only

Do not delete holds, offers or waitlist entries. Set `released_at`, `expired_at`, `status`. Every transition also writes a `seat_events` row. When asked how you would debug a reported double-booking, the answer is one query against `seat_events`.

## Invariant 8: time comes from the database

All timestamps `TIMESTAMPTZ`, all UTC, `now()` evaluated in Postgres, never in Python. A clock-skewed app server must not be able to cause a double sell. `venues.timezone` is for display only.

---

## Failure modes

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
| Database lost entirely | Migrations plus seed script rebuild it | Seed script is the disaster recovery story |
