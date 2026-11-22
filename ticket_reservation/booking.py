"""Seat holds.

Every change locks the seat row before it touches a hold. Confirm and
cancel use that same order, so the two paths cannot deadlock.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.errors import UniqueViolation

_HOLD_COLUMNS = "id, seat_id, buyer_key, idempotency_key, status, expires_at"


@dataclass(frozen=True)
class Hold:
    id: int
    seat_id: int
    buyer_key: str
    idempotency_key: str
    status: str
    expires_at: datetime


class SeatNotFound(LookupError):
    """No seat exists with this id."""


class SeatTaken(Exception):
    """Another live hold or a confirmed booking already has this seat."""


class HoldNotFound(LookupError):
    """No hold exists for this idempotency key."""


class HoldNotActive(Exception):
    """The hold is cancelled, expired, or already confirmed."""

    def __init__(self, status: str) -> None:
        super().__init__(status)
        self.status = status


class IdempotencyConflict(Exception):
    """This request id was already used for a different seat or buyer."""


def hold_seat(
    conn: psycopg.Connection,
    *,
    seat_id: int,
    buyer_key: str,
    idempotency_key: str,
    hold_for: timedelta,
    now: datetime | None = None,
) -> Hold:
    """Store one active hold, or return the hold this request already made.

    `now` defaults to the current UTC time. Tests pass a fixed clock so
    expiry does not depend on sleeping.
    """
    if hold_for.total_seconds() <= 0:
        raise ValueError("hold_for must be positive")
    _required(buyer_key, idempotency_key)
    current = _clock(now)

    with conn.transaction():
        _lock_seat(conn, seat_id)
        existing = _hold_by_key(conn, idempotency_key, lock=True)
        if existing is not None:
            if existing["seat_id"] != seat_id or existing["buyer_key"] != buyer_key:
                raise IdempotencyConflict(idempotency_key)
            return _to_hold(existing)

        _expire_elapsed(conn, seat_id, current)
        taken = conn.execute(
            """
            SELECT id
              FROM holds
             WHERE seat_id = %s
               AND status IN ('active', 'confirmed')
            """,
            (seat_id,),
        ).fetchone()
        if taken is not None:
            raise SeatTaken(seat_id)

        try:
            with conn.transaction():
                row = conn.execute(
                    f"""
                    INSERT INTO holds (
                        seat_id, buyer_key, idempotency_key, status, expires_at, updated_at
                    )
                    VALUES (%s, %s, %s, 'active', %s, %s)
                    RETURNING {_HOLD_COLUMNS}
                    """,
                    (seat_id, buyer_key, idempotency_key, current + hold_for, current),
                ).fetchone()
        except UniqueViolation as exc:
            if exc.diag.constraint_name == "holds_one_taken_seat":
                raise SeatTaken(seat_id) from None
            raise
        return _to_hold(row)


def _required(buyer_key: str, idempotency_key: str) -> None:
    if not buyer_key.strip() or not idempotency_key.strip():
        raise ValueError("buyer_key and idempotency_key are required")


def _clock(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    return now


def _lock_seat(conn: psycopg.Connection, seat_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM seats WHERE id = %s FOR UPDATE",
        (seat_id,),
    ).fetchone()
    if row is None:
        raise SeatNotFound(seat_id)


def _expire_elapsed(conn: psycopg.Connection, seat_id: int, current: datetime) -> None:
    conn.execute(
        """
        UPDATE holds
           SET status = 'expired',
               updated_at = %s
         WHERE seat_id = %s
           AND status = 'active'
           AND expires_at <= %s
        """,
        (current, seat_id, current),
    )


def _hold_by_key(conn: psycopg.Connection, idempotency_key: str, *, lock: bool):
    statement = f"SELECT {_HOLD_COLUMNS} FROM holds WHERE idempotency_key = %s"
    if lock:
        statement += " FOR UPDATE"
    return conn.execute(statement, (idempotency_key,)).fetchone()


def _to_hold(row: dict) -> Hold:
    return Hold(
        id=row["id"],
        seat_id=row["seat_id"],
        buyer_key=row["buyer_key"],
        idempotency_key=row["idempotency_key"],
        status=row["status"],
        expires_at=row["expires_at"],
    )
