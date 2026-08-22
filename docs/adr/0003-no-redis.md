# 3. No Redis, no Celery, no message broker

- Status: accepted
- Date: 2026-08-22

## Context

This system exists to make one guarantee: a seat is never sold twice. Every
piece of state that bears on that guarantee lives in Postgres, in
`seat_holds`, `booking_seats` and `waitlist_offer_seats`, and is serialised by
row locks and partial unique indexes as described in `docs/DATA-MODEL.md`
invariant 2.

The conventional reach at this point is for Redis and a task queue. Redis key
expiry looks like a natural fit for hold TTLs, a cache in front of the seat map
looks like an obvious performance win, and Celery with a broker looks like the
right home for the sweeper and for outbound email. Three of the four are
reflexes rather than decisions, and the fourth is a decision with a specific
failure mode attached.

That failure mode is worth naming precisely, because it is not a general
objection to caching. Seat state in two stores means seat state has two
answers. Redis says a seat is free, Postgres says it is sold, and something
between them fell over at the wrong moment. A customer is shown an available
seat, takes it, and the write fails on a constraint they were never told about,
or worse, does not fail. That divergence is a strictly worse version of the bug
this entire system is built to prevent, introduced in the name of avoiding a
single indexed query.

The second problem is transactional. Postgres gives one transaction spanning
the hold row, the booking row, the waitlist entry, the `seat_events` audit row
and the outbox row. Either all of it happened or none of it did. Nothing in
Redis can join that transaction. A hold row written in Postgres and a TTL key
written in Redis are two writes with a window between them, and a crash in that
window leaves either a hold nothing will expire or an expiry for a hold that
does not exist.

## Decision

Seat state lives in Postgres and only in Postgres. No Redis, no Celery, no
message broker, no external cache.

Hold and offer expiry is lazy: a hold is expired the instant
`expires_at < now()`, evaluated in SQL on every read path, including the
`show_seat_status` view. No external clock and no background job is required
for a seat to become available again.

The sweeper is a periodic in-process task. Its job is to write tombstones,
publish events and drive the waitlist cascade, never to make expiry true.
Outbound email goes through the `email_outbox` table with retry and
exponential backoff. Step 8's event bus is an in-process typed publisher.

## Alternatives considered

**Redis key expiry as the hold TTL mechanism.** Rejected. It makes expiry
authoritative in a store that cannot participate in the Postgres transaction
that creates the hold, so the two can disagree after any crash. It also
requires the key to exist for expiry to work, which means a Redis restart
without persistence silently converts every live hold into a permanent one.
Lazy expiry in SQL needs no key, no clock and no process to be running.

**Redis as a seat map cache.** Rejected on the divergence argument above. The
performance case is also weaker than it looks: the seat map read is one
indexed query against a view, and step 6 asserts a constant query count for a
2000-seat show. Trading a bounded staleness window for one query is a bad deal
when the thing going stale is the exact fact the system guarantees.

**Redis pub/sub for SSE fan-out.** Rejected here and addressed properly in
`0006-sse-fanout.md`. In short, Postgres `LISTEN`/`NOTIFY` solves the same
problem, is transactional, and needs no new infrastructure.

**Celery with a broker for the sweeper and email.** Rejected. It adds a broker,
a worker process and a result backend in order to run two periodic jobs. The
outbox table already provides at-least-once delivery, retry, exponential
backoff, a `last_error` column and a backlog that `GET /api/admin/stats`
reports on. All of that is queryable with SQL when something goes wrong, which
a broker's internal state is not.

**A message broker or event bus between components.** Rejected. There is one
process. An in-process typed publisher gives the same decoupling at the seam
where it is wanted, with no delivery semantics, no ordering questions and no
second thing to deploy.

## Consequences

The sweeper's cadence is tied to the web process. If Render sleeps the
instance, ticks are missed. This is survivable only because expiry is lazy: a
missed tick delays the notification and the tombstone, never the correctness of
what the seat map reports. That is not a claim to be taken on trust, which is
why step 6 reads the seat map with the scheduler not running at all, and step 8
kills the sweeper mid-run and asserts the map is still correct.

Email delivery is at-least-once with a poll interval, so a queued message can
sit for up to one sweep before it is attempted. For a booking confirmation and
a waitlist offer link, that is acceptable. It would not be for something
time-critical, and if it ever became so, the outbox table is already a queue
and moving it behind a real one is a contained change.

Throughput is bounded by Postgres. Concurrent holds on the same seat serialise
on a row lock, and there is no layer above absorbing that contention. Step 15
measures the ceiling under sustained load rather than assuming it is high
enough.

Horizontal scaling is constrained, though for reasons documented separately in
`0006-sse-fanout.md`. A broker would have solved the cross-instance fan-out
problem as a side effect. That is a real thing given up, and it is given up
knowingly.

The system is smaller. One datastore, one process, one deployment, one place to
look when a seat is in the wrong state. For a system whose value is a hard
guarantee rather than throughput, that is the trade worth making.
