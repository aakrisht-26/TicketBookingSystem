# 8. READ COMMITTED with explicit row locks, not SERIALIZABLE

- Status: accepted
- Date: 2026-08-22

## Context

Fifty customers click the same seat at the same moment. Exactly one of them
must get it. That sentence is the assignment, and everything else is
scaffolding around it.

Serialising those attempts is a database problem, not an application one. An
application-level check-then-insert loses the race by construction: between the
check and the insert, another transaction commits. So the question is not
whether the database serialises the attempts, but which mechanism it uses and
where in the code that mechanism is visible.

PostgreSQL's default isolation level is `READ COMMITTED`. The hold transaction
in `docs/DATA-MODEL.md` invariant 2 runs at that level and takes explicit row
locks:

```sql
BEGIN;
SELECT id FROM show_seats WHERE id = ANY(:seat_ids) ORDER BY id FOR UPDATE;
-- lazy expiry write, conflict check, then INSERT INTO seat_holds
COMMIT;
```

The alternative is `SERIALIZABLE`, where PostgreSQL detects the conflict itself
and aborts one of the transactions with a `serialization_failure` (SQLSTATE
40001) that the client is expected to retry.

Both are correct. This is genuinely a choice between two working designs, which
is why it needs a record rather than a comment.

## Decision

`READ COMMITTED` with explicit `SELECT ... FOR UPDATE`, ordered by `id`.

`ORDER BY id` is not stylistic. Two concurrent multi-seat requests with
overlapping seat sets, locking in opposite orders, deadlock. A consistent
ordering makes the second request block on the first rather than the two
killing each other.

Underneath the lock sit four partial unique indexes, listed in
`docs/DATA-MODEL.md` invariant 2:

```sql
CREATE UNIQUE INDEX ON seat_holds (active_key) WHERE active_key IS NOT NULL;
CREATE UNIQUE INDEX ON booking_seats (show_seat_id) WHERE active;
CREATE UNIQUE INDEX ON waitlist_offer_seats (show_seat_id) WHERE active;
CREATE UNIQUE INDEX ON waitlist_entries (show_id, category_id, user_id) WHERE status = 'waiting';
```

These are not decoration on top of the lock. They are the reason correctness
does not depend on every future code path remembering to take it. The lock
makes the common path fast and legible; the indexes make the guarantee hold
even when the application layer is wrong or bypassed entirely. Step 2 asserts
each of them rejects its own duplicate through raw SQL, with the application
out of the picture.

The reasoning behind choosing the lock over the retry is about where contention
lives. With an explicit `FOR UPDATE`, the point of serialisation is a line of
SQL in the hold transaction. A reader can see it, a reviewer can question it,
and a test can target it. With `SERIALIZABLE`, that point is inside the
database and the only trace in the application is a 40001 handler somewhere
generic, far from the code whose contention caused it. For a system whose
headline claim is a concurrency guarantee, having the guarantee be legible at
the place it is made is worth a great deal.

## Alternatives considered

**`SERIALIZABLE`.** Rejected, though it would also be correct. Every write path
touching seat state would need a retry wrapper, and every operation inside that
wrapper would need to be safe to run more than once. Under the sustained
contention that step 15 deliberately generates, the retry rate on a hot show
would make throughput a function of backoff tuning rather than of the database.
There is also a diagnostic cost: a serialisation failure caused by false
positives in predicate locking is indistinguishable, at the point it is caught,
from a genuine conflict over a seat.

**`READ COMMITTED` with no explicit lock, relying only on the partial unique
indexes.** Rejected. The outcome is correct, since the indexes reject the
duplicate, but the loser of the race learns about it through an integrity
error that has to be caught and translated back into a 409. Error handling
becomes exception-driven at the point of highest contention, and it is easy to
catch a unique violation from the wrong constraint and report the wrong thing.
The indexes are a safety net; making them the primary mechanism means
operating in the net.

**Advisory locks keyed on `show_seat_id`.** Rejected. They work, and they avoid
touching the row. But the lock is then attached to a number rather than to
data, nothing in the schema records that the convention exists, and a query
written later that does not know about it gets no protection and no error.

**Application-level check-then-insert.** Rejected. It is the bug the system
exists to prevent, and it is what a naive implementation does.

**A table-level lock on `show_seats`.** Rejected. It serialises the entire show
rather than the contended seat, so one popular row destroys throughput for
every other seat in the venue.

**`REPEATABLE READ`.** Rejected. For write conflicts it produces the same 40001
retry requirement as `SERIALIZABLE`, without `SERIALIZABLE`'s stronger
guarantee. It is the worst of both.

## Consequences

The loser of a contended hold blocks until the winner commits, rather than
failing immediately. Tail latency under contention is therefore bounded by how
long the winning transaction takes, which is why the hold transaction does no
network I/O, no email and no external calls between `BEGIN` and `COMMIT`. Step
15 reports the latency percentiles rather than asserting they are fine.

`ORDER BY id` is load-bearing and trivially easy to delete during a later
refactor, since the query returns the same rows without it and nothing fails
until two specific requests interleave. Step 7 includes a reverse-order
multi-seat pair specifically to catch its removal, and it exists for no other
reason.

Every future write path that touches seat state carries a standing obligation
to take the lock. That obligation is real and `SERIALIZABLE` would not have
imposed it. The partial unique indexes are the mitigation: forgetting the lock
degrades the error message, not the guarantee.

Deadlock remains possible if some later transaction locks these tables in a
different order from the hold path. The ordering convention is written down
here and in `docs/DATA-MODEL.md`, which is weaker than a mechanism, and is
worth remembering when adding a transaction that touches more than one of these
tables.

Long-running transactions holding row locks would stall unrelated requests on
the same seats. Nothing in this design prevents that, so hold transactions stay
short by convention, and `GET /api/admin/stats` exposes live hold counts so an
unusual number of them is visible rather than inferred.
