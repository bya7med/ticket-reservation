# Ticket reservation

Python and PostgreSQL service for selling numbered seats.

If two buyers go for the last seat, only one hold is stored. The hold is written in a transaction and it expires. Sending the same request again does not book that seat a second time.

Short pull requests add the tables, the hold and confirm flow, and tests for a race and for a cancelled hold.

## Database

Postgres 16 or newer. Copy `.env.example` to `.env` and set `DATABASE_URL`.

```bash
psql "$DATABASE_URL" -f sql/001_events_seats_holds.sql
```

`events` is the show, `seats` is one label inside that show, and `holds` is a buyer's claim. A seat can have one active hold or one confirmed booking. A cancelled or expired hold leaves the seat free.

## Holding a seat

`hold_seat` runs in one transaction. It locks the seat, marks any lapsed hold on that seat as expired, and inserts a new active row only if the seat is free. The unique index on live holds is there in case a second insert still races through.

Pass `hold_for` as how long the hold stays valid. A later call with the same `idempotency_key` returns the hold that was already stored.

## Confirming a booking

`confirm_hold` locks the seat, then the hold. An active hold that has not expired becomes `confirmed`. Calling it again with the same idempotency key returns that booking. It does not write a second one. A cancelled or expired hold cannot be confirmed.

`cancel_hold` marks an active hold as cancelled. The seat can then be held by another buyer. A second cancel returns the same row. A confirmed booking is not cancelled by this call.
