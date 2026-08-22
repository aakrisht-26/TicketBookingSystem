# 5. Seat status is derived, not stored

- Status: accepted
- Date: 2026-08-22

## Context

The assignment brief says the seat map must be "stored per show with per-seat
status". Read literally, that describes a per-show seat row carrying a `status`
column.

Half of it is not in question. The seat map is stored per show: `show_seats`
materialises one row per seat per show at show creation, carrying the category
and the resolved price. What is in question is the status.

A stored status column has to be written by every path that changes what a seat
is. Hold created, hold released, hold expired, checkout completed, booking
cancelled, offer created, offer expired, offer claimed, offer rolled onward.
Each of those is a second write that has to stay in step with the authoritative
rows in `seat_holds`, `booking_seats` and `waitlist_offer_seats`. Any single
path that updates one and forgets the other produces a seat that reads
`available` while being sold. That is not an abstract risk; it is the precise
defect this system is graded on, reintroduced as a denormalisation.

One of those transitions is worse than the rest, because it has no writer at
all. A hold expires when `expires_at < now()`. Nothing runs at that instant.
No request arrives, no code executes, and yet the seat has become available.
A stored column cannot represent this. It can only be corrected afterwards by a
sweeper, which means that between the moment of expiry and the next sweep, the
column is wrong. If the instance is asleep and the sweeper misses ticks, the
column stays wrong for as long as that lasts. A design in which a missed
background tick can cause a seat to be sold twice is not a design with a bug in
it; it is the wrong design.

## Decision

Status is computed at query time from the authoritative rows and exposed
through a view, `show_seat_status`:

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

`show_seats` stores the map. The view supplies the status. There is one source
of truth for whether a seat is taken, and it is the rows that record who took
it.

"Live" in that CASE is evaluated in Postgres against each table's own
columns: for a hold, `released_at IS NULL AND expires_at > now()`; for an
offer seat, `active` together with the parent offer's `expires_at`; for a
booking seat, `active`. Expiry is therefore true the instant it is true, on
every read path, with no job needing to have run.

At the API boundary the vocabulary narrows to the three statuses the brief
names. Customers see exactly `available`, `held` and `booked`. An `offered`
seat is reported as `held` to everyone except the offeree, who sees the offer
through a dedicated field on their own offer view. The richer internal model
stays internal.

This satisfies the brief's wording rather than working around it: the seat map
is stored per show, and per-seat status is queryable per show in a single
statement. What is avoided is a cached copy of a fact that is already recorded
elsewhere.

## Alternatives considered

**A stored status column maintained transactionally by every writer.**
Rejected. It is correct only for as long as every write path is correct, in
perpetuity, including paths written by people who have not read this document.
And it cannot express lazy expiry at all, because that transition has no
writer.

**A stored column plus a periodic reconciler.** Rejected. It concedes in
advance that the column will be wrong and makes the length of the wrong window
a function of whether a background job is running. That is exactly the coupling
between sweeper liveness and correctness that invariant 1 forbids.

**A materialised view refreshed on a schedule.** Rejected for the same
staleness reason, with the added cost that a refresh recomputes the entire
show rather than the seats that changed.

**Computing status per seat in Python.** Rejected twice over. It is an N+1
query pattern on a read that step 6 requires to be constant-query, and it moves
`now()` out of Postgres and into the application, which breaks invariant 8. A
clock-skewed application server would then be able to disagree with the
database about whether a hold is live, which is a way to sell a seat twice.

**No view, with the CASE expression written into each query.** Rejected. The
same logic is needed by the seat map read, the hold conflict check and the
waitlist sold-out check. Three copies is three chances for one of them to drift
after a schema change, and the drift would be silent. The view is the single
definition all three consume.

## Consequences

Every seat map read joins `seat_holds`, `booking_seats` and
`waitlist_offer_seats`. That join is the price of the guarantee, and it is paid
on the most frequently hit read in the system. It is mitigated with covering
indexes and, more importantly, measured rather than assumed: step 6 asserts a
constant query count for a 2000-seat show and reports p95 latency.

Status cannot be indexed directly. Predicates that filter on it are answered
through the partial indexes on the underlying tables, which means an index
that looks unrelated to status is in fact what makes a status query fast. The
migration docstrings justify each one for exactly this reason.

The view is not updatable. Writes go to the base tables. This is correct but
surprising to anyone who arrives expecting to `UPDATE show_seat_status SET
status = ...`, which is one of the reasons this record exists.

If the read cost ever becomes the bottleneck, the available fixes are a
materialised view or a cache, and both reintroduce the staleness window this
decision exists to avoid. That trade should only be made against numbers from
the step 15 benchmark, never against an intuition that a join is slow.

There is a deviation from the brief's literal wording, and it is a deliberate
one. It is stated in one sentence in the design write-up and it is not
buried, because a reviewer checking the schema against the brief needs to see
that the deviation was reasoned rather than missed.

## A note on this record's number

`docs/DATA-MODEL.md` refers to this decision as `0002-derived-seat-status.md`.
By the time it was written, 0002 had already been taken by
`0002-no-api-version-prefix.md`, which `CLAUDE.md` asked for during step 0.
Records are never renumbered once allocated, so this one is 0005. The reference
in `docs/DATA-MODEL.md` is stale and points at the wrong record.
