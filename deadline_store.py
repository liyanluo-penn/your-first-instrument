"""Durable, per-user deadline storage in Postgres (Neon in deployment)."""
import os
import uuid
from datetime import datetime

import psycopg

SCHEMA = """
CREATE TABLE IF NOT EXISTS assignment_deadlines (
    id UUID PRIMARY KEY,
    user_id TEXT,
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
    due_at TIMESTAMPTZ NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS assignment_deadlines_owner_due
    ON assignment_deadlines (user_id, due_at);
"""


def db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Copy the connection URL from Neon into your environment.")
    conn = psycopg.connect(url, connect_timeout=10)
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn


def save(user_id: str | None, title: str, due_at: datetime) -> str:
    deadline_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            "INSERT INTO assignment_deadlines (id, user_id, title, due_at) VALUES (%s, %s, %s, %s)",
            (deadline_id, user_id, title, due_at),
        )
    return deadline_id


def list_for(user_id: str | None, include_completed: bool = False):
    with db() as conn:
        return conn.execute(
            "SELECT id, title, due_at, completed FROM assignment_deadlines "
            "WHERE user_id IS NOT DISTINCT FROM %s AND (%s OR NOT completed) "
            "ORDER BY due_at, id", (user_id, include_completed),
        ).fetchall()


def complete(user_id: str | None, deadline_id: str) -> bool:
    try:
        parsed_id = uuid.UUID(deadline_id)
    except ValueError:
        raise ValueError("Use the deadline id returned by save_deadline or list_deadlines.") from None
    with db() as conn:
        row = conn.execute(
            "UPDATE assignment_deadlines SET completed = TRUE "
            "WHERE id = %s AND user_id IS NOT DISTINCT FROM %s RETURNING id",
            (parsed_id, user_id),
        ).fetchone()
    return row is not None
