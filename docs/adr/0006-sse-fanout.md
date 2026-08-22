# 6. Server-sent event fan-out is in-process

- Status: accepted
- Date: 2026-08-22

## Context

Step 8 introduces an in-process publisher with a typed `SeatStateChanged`
event. Step 10 adds `GET /api/shows/{id}/stream`, which subscribes to that
publisher and pushes seat state changes to a customer watching a seat map.
When someone takes a seat, everyone else looking at that show sees it grey out
within a second and without a refresh.

An in-process publisher reaches subscribers in the same process and nowhere
else. On a single instance that is complete. On two, it is not: a customer
whose stream is served by instance A never learns about a hold taken through
instance B. Their seat map stops updating.

The word that matters there is "silently". The connection stays open, the
heartbeat keeps arriving, the page looks live. The customer selects a seat that
was taken forty seconds ago and gets a 409 from a UI that told them it was
free. That is a worse experience than no live updates at all, because no live
updates at least sets the expectation that the page might be stale.

The current deployment is a single Render web service, so the constraint is not
violated today. It is one configuration change away from being violated, by
someone who has every reason to believe that adding an instance is a safe
operational act.

## Decision

Fan-out is in-process. The `SeatStateChanged` publisher from step 8 is the
only transport, and the SSE endpoint is one of its subscribers.

The constraint is stated plainly rather than left implicit. It appears in the
README's known limitations section and in the failure mode table in
`docs/DATA-MODEL.md`, which records that adding a second app instance would
miss cross-instance events. The Render service stays at one instance until the
migration below has landed.

The migration path is Postgres `LISTEN`/`NOTIFY`. The publisher issues a
`NOTIFY` on the same connection and inside the same transaction that writes the
seat change. Each instance holds one dedicated connection issuing `LISTEN` and
republishes what it receives onto its local in-process bus. Every subscriber,
including the SSE endpoint, is unchanged, because the bus interface introduced
at step 8 is the seam. The work is confined to the publisher and one listener
task.

`LISTEN`/`NOTIFY` is the chosen path specifically because it is transactional.
A `NOTIFY` fires on commit, so it is impossible to deliver an event for a
transaction that rolled back. Given that this system's whole subject is not
telling people a seat is available when it is not, that property is worth more
here than it would be in most systems.

## Alternatives considered

**Redis pub/sub.** Rejected. It introduces the infrastructure that
`0003-no-redis.md` declines, and it is fire-and-forget outside the database
transaction, so a rolled-back hold can still emit a "seat held" event to every
watching client. The seat map would then be wrong until something else
corrected it.

**Implementing `LISTEN`/`NOTIFY` now rather than later.** Rejected as
premature, though it is the accepted eventual answer. It costs a dedicated
long-lived connection per instance, reconnection and resubscription handling
when Neon drops that connection, and a payload size limit of 8000 bytes that in
practice forces a notify-then-fetch pattern rather than carrying the event
inline. That is real complexity, and today it buys nothing, because there is
one instance. The decision is to leave the seam in place and cross it when
there is a second instance to justify it.

**Sticky sessions pinning a show to an instance.** Rejected. It needs a router
that understands show ids rather than client ids, and it does not survive a
deploy: rebalancing moves shows between instances and drops streams mid-session.
It also fails outright when one show is popular enough to need more than one
instance, which is exactly the scenario that motivated scaling out.

**Polling instead of streaming.** Rejected. The brief asks for real-time status
and polling at an interval short enough to feel real-time costs more in total
requests than holding the streams open, while also being less responsive.

**Scaling vertically and never writing the constraint down.** Rejected. An
undocumented single-instance requirement is a trap laid for whoever next looks
at a slow response time and reaches for the instance count.

## Consequences

The honest downside is that scaling to a second instance breaks live updates,
and nothing in the test suite can catch it. Every test runs in one process, so
every test passes. This constraint is enforced by documentation and by
deployment configuration, not by code, which makes it the weakest guarantee in
the system. Naming it here, in the README and in the failure mode table is the
mitigation, and it is not a strong one.

A deploy terminates every open stream. Clients reconnect and resume using
`Last-Event-ID`, which step 10 implements and tests.

A restart loses any event that had not yet been delivered. This is acceptable,
and the reason is worth stating explicitly because it is what keeps the
weakness above from being a correctness problem: the SSE stream is a latency
optimisation over `show_seat_status`, never a source of truth. A client that
reconnects re-reads the seat map and converges. Nothing in this system is
correct only because an event arrived.

Fan-out cost is bounded by the number of streams one process holds, and step 10
asserts that an abruptly dropped client leaks neither a connection nor a task,
by counting both before and after. That is the failure mode an in-process
design actually has to worry about, as opposed to the distributed one it does
not have yet.
