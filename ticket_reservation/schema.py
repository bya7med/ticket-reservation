"""Load the seat and hold tables."""

from __future__ import annotations

from pathlib import Path

import psycopg

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "001_events_seats_holds.sql"


def apply_schema(conn: psycopg.Connection) -> None:
    statements = _statements(SCHEMA_PATH.read_text())
    with conn.cursor() as cur:
        for statement in statements:
            cur.execute(statement)


def _statements(script: str) -> list[str]:
    lines = []
    for line in script.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)
    return [part.strip() for part in body.split(";") if part.strip()]
