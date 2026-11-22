"""Database setup for the reservation tests."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import psycopg
import pytest
from psycopg.rows import dict_row

from ticket_reservation.schema import apply_schema

TEST_URL = os.environ.get("DATABASE_URL", "postgresql:///ticket_reservation_test")


@pytest.fixture
def db():
    with psycopg.connect(TEST_URL, autocommit=True) as admin:
        admin.execute("DROP SCHEMA IF EXISTS public CASCADE")
        admin.execute("CREATE SCHEMA public")
    with psycopg.connect(TEST_URL, row_factory=dict_row) as conn:
        apply_schema(conn)
        conn.commit()
        yield conn


@pytest.fixture
def open_db():
    def _open() -> psycopg.Connection:
        return psycopg.connect(TEST_URL, row_factory=dict_row)

    return _open


def seed_seat(conn: psycopg.Connection, label: str = "A1") -> int:
    event = conn.execute(
        """
        INSERT INTO events (name, starts_at)
        VALUES (%s, %s)
        RETURNING id
        """,
        ("Opening night", datetime(2026, 12, 1, 19, 0, tzinfo=timezone.utc)),
    ).fetchone()
    seat = conn.execute(
        """
        INSERT INTO seats (event_id, label)
        VALUES (%s, %s)
        RETURNING id
        """,
        (event["id"], label),
    ).fetchone()
    conn.commit()
    return seat["id"]
