-- Events on sale.
CREATE TABLE events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL,
    starts_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- One row per physical seat. The label is unique inside an event.
CREATE TABLE seats (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id bigint NOT NULL REFERENCES events (id),
    label text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (event_id, label)
);

-- A hold is one buyer's claim on one seat.
-- status is active, confirmed, cancelled, or expired.
-- idempotency_key is the caller's request id. A repeat of that id
-- must come back as this same row, not a second booking.
CREATE TABLE holds (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seat_id bigint NOT NULL REFERENCES seats (id),
    buyer_key text NOT NULL,
    idempotency_key text NOT NULL,
    status text NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'confirmed', 'cancelled', 'expired')),
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT holds_idempotency_key UNIQUE (idempotency_key)
);

-- A seat is taken while a hold is still active or a booking is confirmed.
-- Cancelled and expired rows stay in the table and do not block the seat.
-- The hold transaction marks a lapsed active row as expired before insert.
-- Postgres cannot put now() in an index predicate, so expiry is an update.
CREATE UNIQUE INDEX holds_one_taken_seat
    ON holds (seat_id)
    WHERE status IN ('active', 'confirmed');
