"""Expiry frees a seat. A repeated confirm does not book it twice."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import seed_seat
from ticket_reservation.booking import HoldNotActive, SeatTaken, confirm_hold, hold_seat

START = datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc)


def test_repeat_confirm_does_not_book_twice(db):
    seat_id = seed_seat(db)
    hold_seat(
        db,
        seat_id=seat_id,
        buyer_key="alice",
        idempotency_key="alice-1",
        hold_for=timedelta(minutes=10),
        now=START,
    )
    first = confirm_hold(db, idempotency_key="alice-1", now=START)
    second = confirm_hold(db, idempotency_key="alice-1", now=START + timedelta(minutes=1))
    assert first.id == second.id
    assert second.status == "confirmed"

    count = db.execute(
        "SELECT count(*) AS n FROM holds WHERE status = 'confirmed'"
    ).fetchone()
    assert count["n"] == 1

    with pytest.raises(SeatTaken):
        hold_seat(
            db,
            seat_id=seat_id,
            buyer_key="bob",
            idempotency_key="bob-1",
            hold_for=timedelta(minutes=10),
            now=START + timedelta(minutes=1),
        )


def test_expired_hold_lets_the_next_buyer_through(db):
    seat_id = seed_seat(db)
    hold_seat(
        db,
        seat_id=seat_id,
        buyer_key="alice",
        idempotency_key="alice-1",
        hold_for=timedelta(minutes=2),
        now=START,
    )
    later = START + timedelta(minutes=2)
    nxt = hold_seat(
        db,
        seat_id=seat_id,
        buyer_key="bob",
        idempotency_key="bob-1",
        hold_for=timedelta(minutes=5),
        now=later,
    )
    assert nxt.buyer_key == "bob"
    assert nxt.status == "active"

    with pytest.raises(HoldNotActive) as caught:
        confirm_hold(db, idempotency_key="alice-1", now=later)
    assert caught.value.status == "expired"

    rows = db.execute(
        "SELECT buyer_key, status FROM holds ORDER BY id"
    ).fetchall()
    assert [(row["buyer_key"], row["status"]) for row in rows] == [
        ("alice", "expired"),
        ("bob", "active"),
    ]
