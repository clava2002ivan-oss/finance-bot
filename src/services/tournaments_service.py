from __future__ import annotations

from typing import List, Optional

from .. import db


def list_tournaments():
    return db.execute(
        "SELECT * FROM tournaments ORDER BY name",
        fetchall=True,
    )


def get_tournament_by_name(name: str):
    return db.execute(
        "SELECT * FROM tournaments WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
        fetchone=True,
    )


def get_tournament_by_id(tournament_id: int):
    return db.execute(
        "SELECT * FROM tournaments WHERE id = ?",
        (tournament_id,),
        fetchone=True,
    )


def get_or_create_tournament(name: str):
    existing = get_tournament_by_name(name)
    if existing:
        return existing["id"]
    cursor = db.execute(
        "INSERT INTO tournaments (name) VALUES (?)",
        (name.strip(),),
        commit=True,
    )
    return cursor.lastrowid
