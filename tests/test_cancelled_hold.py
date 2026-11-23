"""A cancelled hold must not stay a booking, and the seat must open up."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import seed_seat
from ticket_reservation.booking import HoldNotActive, cancel_hold, confirm_hold, hold_seat

START = datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc)


def test_cancelled_hold_frees_the_seat_and_cannot_be_confirmed(db):
    seat_id = seed_seat(db)
    first = hold_seat(
        db,
        seat_id=seat_id,
        buyer_key="alice",
        idempotency_key="alice-1",
        hold_for=timedelta(minutes=5),
        now=START,
    )
    cancelled = cancel_hold(db, idempotency_key="alice-1", now=START)
    repeated = cancel_hold(db, idempotency_key="alice-1", now=START)
    assert cancelled.id == first.id
    assert repeated.id == first.id
    assert repeated.status == "cancelled"

    with pytest.raises(HoldNotActive) as caught:
        confirm_hold(db, idempotency_key="alice-1", now=START)
    assert caught.value.status == "cancelled"

    second = hold_seat(
        db,
        seat_id=seat_id,
        buyer_key="bob",
        idempotency_key="bob-1",
        hold_for=timedelta(minutes=5),
        now=START,
    )
    booked = confirm_hold(db, idempotency_key="bob-1", now=START)
    assert second.status == "active"
    assert booked.status == "confirmed"

    rows = db.execute(
        """
        SELECT buyer_key, status
          FROM holds
         WHERE seat_id = %s
         ORDER BY id
        """,
        (seat_id,),
    ).fetchall()
    assert [(row["buyer_key"], row["status"]) for row in rows] == [
        ("alice", "cancelled"),
        ("bob", "confirmed"),
    ]
