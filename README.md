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
