# Requirement compliance matrix

Every line of the assignment brief, mapped. Tick as steps land. **Nothing ships until this table is complete.** It also goes in the README, so a reviewer can confirm coverage without hunting.

## Scope of work

| # | Brief requirement | Step | Proof | Done |
|---|---|---|---|---|
| S1 | Admin creates and manages venues with seat layout and seat categories | 4 | `test_venues.py` | [ ] |
| S2 | Organiser can register, log in | 3 | `test_auth.py::test_organiser_self_registration` | [ ] |
| S3 | Organiser creates movie or event listings with venue, date, time, per-category pricing | 5 | `test_shows.py` | [ ] |
| S4 | Customer can register, log in | 3 | `test_auth.py` | [ ] |
| S5 | Customer can browse and filter events | 5, 16 | `test_events.py::test_filters` | [ ] |
| S6 | Visual seat map with real-time status (available / held / booked) | 6, 10, 17 | `test_seatmap.py`, e2e | [ ] |
| S7 | Seat hold with configurable TTL, default 600s | 7 | `test_holds.py::test_ttl_configurable` | [ ] |
| S8 | Held seats shown unavailable to other customers | 6 | `test_seatmap.py::test_held_seat_unavailable_to_others` | [ ] |
| S9 | Abandoned checkout auto-releases held seats | 8 | `test_holds.py::test_expiry_releases_seat` | [ ] |
| S10 | Seat map updates in real time on release | 8, 10 | `test_sse.py::test_release_event_delivered` | [ ] |
| S11 | Two customers cannot hold the same seat simultaneously | 7 | `test_concurrency.py` | [ ] |
| S12 | Two customers cannot book the same seat simultaneously | 9 | `test_concurrency.py::test_concurrent_checkout_one_booking` | [ ] |
| S13 | Booking sends email with QR code ticket | 12 | `test_email.py`, `test_qr.py` | [ ] |
| S14 | QR encodes booking reference | 12 | `test_qr.py::test_qr_decodes_to_reference` | [ ] |
| S15 | Waitlist join per seat category when sold out | 11 | `test_waitlist.py` | [ ] |
| S16 | Cancellation offers seat to next customer on waitlist | 12 | `test_waitlist.py::test_cancel_creates_offer` | [ ] |
| S17 | Offeree receives email with time-limited link | 12 | `test_email.py::test_offer_email_contains_link` | [ ] |
| S18 | Unclaimed offer rolls to next in line | 13 | `test_waitlist.py::test_offer_cascade` | [ ] |
| S19 | Customer can view booking history | 19 | e2e | [ ] |
| S20 | Customer can cancel a booking | 12, 19 | `test_bookings.py::test_cancel` | [ ] |
| S21 | Organiser can view booking summary and revenue per event | 14 | `test_reporting.py` | [ ] |

## Technical expectations

| # | Brief requirement | Step | Note | Done |
|---|---|---|---|---|
| T1 | Backend API, frontend, database | all | | [ ] |
| T2 | Role-based auth: customer, organiser, admin | 3 | | [ ] |
| T3 | Seat map stored per show with per-seat status | 2, 6 | `show_seats` plus the `show_seat_status` view. See `docs/DATA-MODEL.md` invariant 1 | [ ] |
| T4 | Rendered as visual grid on frontend | 17 | | [ ] |
| T5 | Hold TTL enforced via scheduler or database-level expiry | 6, 8 | Database-level primary, sweeper secondary | [ ] |
| T6 | Seat status updated on release | 8, 10 | | [ ] |
| T7 | Concurrency protection, simultaneous attempts must not both succeed | 7, 9 | | [ ] |
| T8 | Waitlist queue per seat category | 11 | | [ ] |
| T9 | Auto-assignment and time-limited offer flow on cancellation | 12, 13 | | [ ] |
| T10 | QR generation on booking | 12 | | [ ] |
| T11 | Email delivery with QR, any free tier service | 12 | | [ ] |

## Deliverables

| # | Brief requirement | Step | Done |
|---|---|---|---|
| D1 | Complete source code | all | [ ] |
| D2 | README with setup, `.env.example`, API docs, DB schema, hold and waitlist logic | 21 | [ ] |
| D3 | Hosted application URL | 1, live from then on | [ ] |
| D4 | System design write-up, 800 words max, four required topics | 21 | [ ] |

Submission is **the GitHub repository link only**, per the instruction accompanying the brief. The brief's zip deliverable is satisfied by tagging `v1.0.0` and attaching the source archive to a GitHub Release, so the repo link covers it.

## Evaluation focus, all six

The brief lists **six** criteria, not four. All six get equal structural treatment in the README.

| # | Criterion | Where demonstrated |
|---|---|---|
| E1 | Seat hold TTL and auto-release mechanism | Steps 6, 7, 8 |
| E2 | Concurrency protection for simultaneous seat selection | Steps 7, 9, 15 |
| E3 | Waitlist auto-assignment and time-limited offer flow | Steps 11, 12, 13 |
| E4 | Seat map data model and real-time status updates | Steps 2, 6, 10 |
| E5 | QR code generation and email delivery | Step 12 |
| E6 | API design, code structure, and documentation | `docs/STANDARDS.md`, steps 0 and 21 |

E6 is not a formality. It is the criterion the Definition of Done, the OpenAPI curation, the ADRs and the README specification all exist to satisfy. It is also the easiest to lose by accident.

## Explicitly out of scope

Payment processing. The brief describes checkout and pricing but never payment. Do not integrate a gateway. State this in one line in the README so its absence reads as a decision rather than an omission.
