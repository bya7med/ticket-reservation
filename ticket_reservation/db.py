"""Open a Postgres connection for the reservation service."""

from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row


def connect(database_url: str | None = None) -> psycopg.Connection:
    url = database_url if database_url is not None else os.environ["DATABASE_URL"]
    return psycopg.connect(url, row_factory=dict_row)
