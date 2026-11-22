"""Two buyers try to hold the last seat at the same time."""

from __future__ import annotations

import threading
from datetime import timedelta

from tests.conftest import seed_seat
from ticket_reservation.booking import SeatTaken, hold_seat


def test_two_buyers_cannot_take_the_last_seat(db, open_db):
    seat_id = seed_seat(db)
    barrier = threading.Barrier(2)
    outcomes = []
    guard = threading.Lock()

    def attempt(buyer: str) -> None:
        with open_db() as conn:
            barrier.wait(timeout=5)
            try:
                hold = hold_seat(
                    conn,
                    seat_id=seat_id,
                    buyer_key=buyer,
                    idempotency_key=f"hold-{buyer}",
                    hold_for=timedelta(minutes=10),
                )
                outcome = ("held", buyer, hold.id)
            except SeatTaken:
                outcome = ("taken", buyer, None)
            except Exception as exc:  # keep the thread alive and fail the test below
                outcome = ("error", buyer, exc)
        with guard:
            outcomes.append(outcome)

    threads = [
        threading.Thread(target=attempt, args=("alice",)),
        threading.Thread(target=attempt, args=("bob",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
        assert not thread.is_alive()

    errors = [item for item in outcomes if item[0] == "error"]
    assert errors == []
    held = [item for item in outcomes if item[0] == "held"]
    taken = [item for item in outcomes if item[0] == "taken"]
    assert len(held) == 1
    assert len(taken) == 1

    rows = db.execute(
        """
        SELECT buyer_key
          FROM holds
         WHERE seat_id = %s
           AND status = 'active'
        """,
        (seat_id,),
    ).fetchall()
    assert [row["buyer_key"] for row in rows] == [held[0][1]]
