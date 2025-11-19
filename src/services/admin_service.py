from __future__ import annotations

from typing import List, Optional

from .. import db


def list_teams():
    return db.execute(
        "SELECT * FROM teams ORDER BY name",
        fetchall=True,
    )


def get_team_by_id(team_id: int):
    return db.execute(
        "SELECT * FROM teams WHERE id = ?",
        (team_id,),
        fetchone=True,
    )


def get_team_by_name_or_tag(value: str):
    return db.execute(
        "SELECT * FROM teams WHERE LOWER(name) = LOWER(?) OR LOWER(tag) = LOWER(?)",
        (value.strip(), value.strip()),
        fetchone=True,
    )


def add_team(name: str, tag: str, region: Optional[str] = None):
    cursor = db.execute(
        "INSERT INTO teams (name, tag, region) VALUES (?, ?, ?)",
        (name.strip(), tag.strip(), region.strip() if region else None),
        commit=True,
    )
    return cursor.lastrowid


def add_player(nickname: str, team_id: int, role: str):
    cursor = db.execute(
        "INSERT INTO players (nickname, team_id, role) VALUES (?, ?, ?)",
        (nickname.strip(), team_id, role),
        commit=True,
    )
    return cursor.lastrowid


def list_players_by_team(team_id: int):
    return db.execute(
        "SELECT * FROM players WHERE team_id = ? ORDER BY nickname",
        (team_id,),
        fetchall=True,
    )


def get_player_by_nickname(nickname: str):
    return db.execute(
        "SELECT * FROM players WHERE LOWER(nickname) = LOWER(?)",
        (nickname.strip(),),
        fetchone=True,
    )


def get_hero_by_name(name: str):
    return db.execute(
        "SELECT * FROM heroes WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
        fetchone=True,
    )


def add_hero(name: str, role: Optional[str] = None, game: str = "MLBB"):
    cursor = db.execute(
        "INSERT INTO heroes (name, role, game) VALUES (?, ?, ?)",
        (name.strip(), role, game),
        commit=True,
    )
    return cursor.lastrowid


def add_match(
    tournament_id: int,
    team_a_id: int,
    team_b_id: int,
    winner_team_id: int,
    date: Optional[str] = None,
):
    cursor = db.execute(
        "INSERT INTO matches (tournament_id, team_a_id, team_b_id, winner_team_id, date) "
        "VALUES (?, ?, ?, ?, ?)",
        (tournament_id, team_a_id, team_b_id, winner_team_id, date),
        commit=True,
    )
    return cursor.lastrowid


def add_player_match_stat(
    match_id: int,
    player_id: int,
    hero_id: int,
    kills: int,
    deaths: int,
    assists: int,
    is_win: int,
):
    db.execute(
        """
        INSERT INTO player_match_stats
        (match_id, player_id, hero_id, kills, deaths, assists, is_win)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (match_id, player_id, hero_id, kills, deaths, assists, is_win),
        commit=True,
    )
