from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Sequence

from .config import get_settings


settings = get_settings()
DB_PATH = Path(settings.db_path)
_connection: sqlite3.Connection | None = None
_lock = Lock()


def _ensure_connection() -> sqlite3.Connection:
    global _connection
    with _lock:
        if _connection is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _connection = sqlite3.connect(DB_PATH, check_same_thread=False)
            _connection.row_factory = sqlite3.Row
        return _connection


@contextmanager
def get_cursor():
    conn = _ensure_connection()
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def execute(
    query: str,
    params: Sequence[Any] | None = None,
    *,
    fetchone: bool = False,
    fetchall: bool = False,
    commit: bool = False,
):
    if params is None:
        params = ()
    conn = _ensure_connection()
    cur = conn.execute(query, params)
    if commit:
        conn.commit()
    if fetchone:
        return cur.fetchone()
    if fetchall:
        return cur.fetchall()
    return cur


def executemany(query: str, seq_of_params: Iterable[Sequence[Any]]):
    conn = _ensure_connection()
    conn.executemany(query, seq_of_params)
    conn.commit()


def initialize_db():
    schema = """
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        tag TEXT NOT NULL UNIQUE,
        region TEXT
    );

    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nickname TEXT NOT NULL UNIQUE,
        team_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        team_a_id INTEGER NOT NULL,
        team_b_id INTEGER NOT NULL,
        winner_team_id INTEGER NOT NULL,
        date TEXT,
        FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
        FOREIGN KEY (team_a_id) REFERENCES teams(id) ON DELETE CASCADE,
        FOREIGN KEY (team_b_id) REFERENCES teams(id) ON DELETE CASCADE,
        FOREIGN KEY (winner_team_id) REFERENCES teams(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS heroes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        role TEXT,
        game TEXT DEFAULT 'MLBB'
    );

    CREATE TABLE IF NOT EXISTS player_match_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        hero_id INTEGER NOT NULL,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        assists INTEGER DEFAULT 0,
        is_win INTEGER DEFAULT 0,
        FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
        FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
        FOREIGN KEY (hero_id) REFERENCES heroes(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS hero_bans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id INTEGER NOT NULL,
        team_id INTEGER NOT NULL,
        hero_id INTEGER NOT NULL,
        ban_order INTEGER,
        FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
        FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
        FOREIGN KEY (hero_id) REFERENCES heroes(id) ON DELETE CASCADE
    );
    """
    conn = _ensure_connection()
    conn.executescript(schema)
    conn.commit()
