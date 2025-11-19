from __future__ import annotations

from typing import List, Optional

from ..db import db


def list_teams() -> List[dict]:
    rows = db.fetchall("SELECT id, name, tag FROM teams ORDER BY name")
    return [dict(row) for row in rows]


def add_team(name: str, tag: str, region: Optional[str] = None) -> dict:
    team_id = db.execute(
        "INSERT INTO teams (name, tag, region) VALUES (?, ?, ?)",
        (name.strip(), tag.strip(), region.strip() if region else None),
    )
    team = db.fetchone("SELECT * FROM teams WHERE id = ?", (team_id,))
    return dict(team)


def add_player(nickname: str, team_id: int, role: str) -> dict:
    player_id = db.execute(
        "INSERT INTO players (nickname, team_id, role) VALUES (?, ?, ?)",
        (nickname.strip(), team_id, role),
    )
    player = db.fetchone("SELECT * FROM players WHERE id = ?", (player_id,))
    return dict(player)


def list_players_for_team(team_id: int) -> List[dict]:
    rows = db.fetchall(
        "SELECT id, nickname, role FROM players WHERE team_id = ? ORDER BY nickname",
        (team_id,),
    )
    return [dict(row) for row in rows]


def find_team_by_name_or_tag(query_text: str):
    return db.fetchone(
        "SELECT * FROM teams WHERE LOWER(name)=LOWER(?) OR LOWER(tag)=LOWER(?)",
        (query_text, query_text),
    )


def add_match(tournament_id: int, team_a_id: int, team_b_id: int, winner_team_id: int, date: Optional[str] = None) -> dict:
    match_id = db.execute(
        "INSERT INTO matches (tournament_id, team_a_id, team_b_id, winner_team_id, date) VALUES (?, ?, ?, ?, ?)",
        (tournament_id, team_a_id, team_b_id, winner_team_id, date),
    )
    match = db.fetchone("SELECT * FROM matches WHERE id = ?", (match_id,))
    return dict(match)


def add_player_match_stat(
    match_id: int,
    player_id: int,
    hero_id: int,
    kills: int,
    deaths: int,
    assists: int,
    is_win: int,
) -> dict:
    stat_id = db.execute(
        """
        INSERT INTO player_match_stats (match_id, player_id, hero_id, kills, deaths, assists, is_win)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (match_id, player_id, hero_id, kills, deaths, assists, is_win),
    )
    stat = db.fetchone("SELECT * FROM player_match_stats WHERE id = ?", (stat_id,))
    return dict(stat)


def get_or_create_hero(name: str, role: Optional[str] = None, game: str = "MLBB") -> dict:
    existing = db.fetchone("SELECT * FROM heroes WHERE LOWER(name) = LOWER(?)", (name,))
    if existing:
        return dict(existing)
    hero_id = db.execute(
        "INSERT INTO heroes (name, role, game) VALUES (?, ?, ?)",
        (name.strip(), role, game),
    )
    hero = db.fetchone("SELECT * FROM heroes WHERE id = ?", (hero_id,))
    return dict(hero)
