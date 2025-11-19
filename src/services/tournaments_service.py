from __future__ import annotations

from typing import List

from ..db import db


def list_tournaments() -> List[dict]:
    rows = db.fetchall("SELECT id, name FROM tournaments ORDER BY name ASC")
    return [dict(row) for row in rows]


def get_or_create_tournament(name: str) -> dict:
    existing = db.fetchone("SELECT * FROM tournaments WHERE LOWER(name) = LOWER(?)", (name,))
    if existing:
        return dict(existing)
    tournament_id = db.execute("INSERT INTO tournaments (name) VALUES (?)", (name,))
    created = db.fetchone("SELECT * FROM tournaments WHERE id = ?", (tournament_id,))
    return dict(created)
