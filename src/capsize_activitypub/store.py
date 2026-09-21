from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ConnectionStore:
    """Small local store for discovered ActivityPub actors."""

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS actors (actor_id TEXT PRIMARY KEY, payload TEXT NOT NULL, saved_at REAL NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def save_actor(self, actor: dict[str, Any], saved_at: float) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO actors(actor_id, payload, saved_at) VALUES(?, ?, ?) ON CONFLICT(actor_id) DO UPDATE SET payload=excluded.payload, saved_at=excluded.saved_at",
                (str(actor["id"]), json.dumps(actor), saved_at),
            )

    def list_actors(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM actors ORDER BY saved_at DESC").fetchall()
        return [json.loads(row[0]) for row in rows]
