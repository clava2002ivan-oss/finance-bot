from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence

from .config import settings


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query: str, params: Sequence | None = None, *, commit: bool = True) -> int:
        with self.connect() as conn:
            cursor = conn.execute(query, params or [])
            if commit:
                conn.commit()
            return cursor.lastrowid

    def fetchone(self, query: str, params: Sequence | None = None):
        with self.connect() as conn:
            cursor = conn.execute(query, params or [])
            return cursor.fetchone()

    def fetchall(self, query: str, params: Sequence | None = None):
        with self.connect() as conn:
            cursor = conn.execute(query, params or [])
            return cursor.fetchall()


db = Database(settings.db_path)


SCHEMA_STATEMENTS: Iterable[str] = [
    """
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        tag TEXT NOT NULL UNIQUE,
        region TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL UNIQUE,
        team_id INTEGER NOT NULL,
        role TEXT CHECK (role IN ('gold', 'exp', 'mid', 'jungle', 'roam')),
        FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        team_a_id INTEGER NOT NULL,
        team_b_id INTEGER NOT NULL,
        winner_team_id INTEGER NOT NULL,
        date TEXT,
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
        FOREIGN KEY (team_a_id) REFERENCES teams(id),
        FOREIGN KEY (team_b_id) REFERENCES teams(id),
        FOREIGN KEY (winner_team_id) REFERENCES teams(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS heroes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        role TEXT,
        game TEXT DEFAULT 'MLBB'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS player_match_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        hero_id INTEGER NOT NULL,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0,
        is_win INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
        FOREIGN KEY (player_id) REFERENCES players(id),
        FOREIGN KEY (hero_id) REFERENCES heroes(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hero_bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        hero_id INTEGER NOT NULL,
        ban_order INTEGER,
        FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
        FOREIGN KEY (team_id) REFERENCES teams(id),
        FOREIGN KEY (hero_id) REFERENCES heroes(id)
    )
    """,
]


def init_db() -> None:
    with db.connect() as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.executescript(statement)
        conn.commit()
