from __future__ import annotations

from typing import List, Optional

from .. import db


def _winrate(wins: int, games: int) -> float:
    if games == 0:
        return 0.0
    return round(wins / games * 100, 2)


def _average(value: int, games: int) -> float:
    if games == 0:
        return 0.0
    return round(value / games, 2)


def get_player_by_nickname(nickname: str):
    return db.execute(
        "SELECT players.*, teams.name AS team_name "
        "FROM players "
        "JOIN teams ON teams.id = players.team_id "
        "WHERE LOWER(players.nickname) = LOWER(?)",
        (nickname,),
        fetchone=True,
    )


def get_player_by_id(player_id: int):
    return db.execute(
        "SELECT players.*, teams.name AS team_name "
        "FROM players "
        "JOIN teams ON teams.id = players.team_id "
        "WHERE players.id = ?",
        (player_id,),
        fetchone=True,
    )


def list_player_tournaments(player_id: int):
    return db.execute(
        """
        SELECT DISTINCT t.id, t.name
        FROM tournaments t
        JOIN matches m ON m.tournament_id = t.id
        JOIN player_match_stats pms ON pms.match_id = m.id
        WHERE pms.player_id = ?
        ORDER BY t.name
        """,
        (player_id,),
        fetchall=True,
    )


def get_player_stats(player_id: int, tournament_id: Optional[int] = None):
    filter_clause = ""
    params: List[int | None] = [player_id]
    if tournament_id:
        filter_clause = "AND m.tournament_id = ?"
        params.append(tournament_id)

    rows = db.execute(
        f"""
        SELECT pms.*, h.name as hero_name, m.tournament_id
        FROM player_match_stats pms
        JOIN matches m ON m.id = pms.match_id
        JOIN heroes h ON h.id = pms.hero_id
        WHERE pms.player_id = ?
        {filter_clause}
        """,
        tuple(params),
        fetchall=True,
    )

    games = len(rows)
    wins = sum(row["is_win"] for row in rows)
    losses = games - wins
    kills = sum(row["kills"] for row in rows)
    deaths = sum(row["deaths"] for row in rows)
    assists = sum(row["assists"] for row in rows)
    kda = round((kills + assists) / max(1, deaths), 2) if games else 0.0

    hero_pool = db.execute(
        f"""
        SELECT pms.hero_id,
               h.name AS hero_name,
               COUNT(*) AS games,
               SUM(pms.is_win) AS wins
        FROM player_match_stats pms
        JOIN matches m ON m.id = pms.match_id
        JOIN heroes h ON h.id = pms.hero_id
        WHERE pms.player_id = ?
        {filter_clause}
        GROUP BY pms.hero_id, h.name
        ORDER BY games DESC, h.name ASC
        """,
        tuple(params),
        fetchall=True,
    )

    hero_pool_data = []
    for item in hero_pool:
        hero_games = item["games"]
        hero_wins = item["wins"] or 0
        hero_pool_data.append(
            {
                "hero_id": item["hero_id"],
                "hero_name": item["hero_name"],
                "games": hero_games,
                "wins": hero_wins,
                "losses": hero_games - hero_wins,
                "winrate": _winrate(hero_wins, hero_games),
            }
        )

    return {
        "games": games,
        "wins": wins,
        "losses": losses,
        "winrate": _winrate(wins, games),
        "kills": {"total": kills, "avg": _average(kills, games)},
        "deaths": {"total": deaths, "avg": _average(deaths, games)},
        "assists": {"total": assists, "avg": _average(assists, games)},
        "kda": kda,
        "hero_pool": hero_pool_data,
    }


def get_team_by_identifier(identifier: str):
    identifier = identifier.strip()
    return db.execute(
        "SELECT * FROM teams WHERE LOWER(name) = LOWER(?) OR LOWER(tag) = LOWER(?)",
        (identifier, identifier),
        fetchone=True,
    )


def get_team_by_id(team_id: int):
    return db.execute(
        "SELECT * FROM teams WHERE id = ?",
        (team_id,),
        fetchone=True,
    )


def list_team_tournaments(team_id: int):
    return db.execute(
        """
        SELECT DISTINCT t.id, t.name
        FROM tournaments t
        JOIN matches m ON m.tournament_id = t.id
        WHERE m.team_a_id = ? OR m.team_b_id = ?
        ORDER BY t.name
        """,
        (team_id, team_id),
        fetchall=True,
    )


def get_team_stats(team_id: int, tournament_id: Optional[int] = None):
    match_filter = ""
    match_params: List[int | None] = [team_id, team_id]
    if tournament_id:
        match_filter = "AND m.tournament_id = ?"
        match_params.append(tournament_id)

    matches = db.execute(
        f"""
        SELECT m.*, t.name as tournament_name
        FROM matches m
        LEFT JOIN tournaments t ON t.id = m.tournament_id
        WHERE (m.team_a_id = ? OR m.team_b_id = ?)
        {match_filter}
        """,
        tuple(match_params),
        fetchall=True,
    )

    games = len(matches)
    wins = sum(1 for m in matches if m["winner_team_id"] == team_id)
    losses = games - wins

    player_filter = ""
    player_params: List[int | None] = [team_id]
    if tournament_id:
        player_filter = "AND m.tournament_id = ?"
        player_params.append(tournament_id)

    player_rows = db.execute(
        f"""
        SELECT pms.*
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id
        JOIN matches m ON m.id = pms.match_id
        WHERE p.team_id = ?
        {player_filter}
        """,
        tuple(player_params),
        fetchall=True,
    )

    kills = sum(row["kills"] for row in player_rows)
    deaths = sum(row["deaths"] for row in player_rows)
    assists = sum(row["assists"] for row in player_rows)
    stats_games = games if games else 0

    hero_filter = ""
    hero_params: List[int | None] = [team_id]
    if tournament_id:
        hero_filter = "AND m.tournament_id = ?"
        hero_params.append(tournament_id)

    hero_pool = db.execute(
        f"""
        SELECT pms.hero_id,
               h.name AS hero_name,
               COUNT(*) AS games,
               SUM(pms.is_win) AS wins
        FROM player_match_stats pms
        JOIN players pl ON pl.id = pms.player_id
        JOIN matches m ON m.id = pms.match_id
        JOIN heroes h ON h.id = pms.hero_id
        WHERE pl.team_id = ?
        {hero_filter}
        GROUP BY pms.hero_id, h.name
        ORDER BY games DESC, h.name ASC
        """,
        tuple(hero_params),
        fetchall=True,
    )

    hero_pool_data = []
    for item in hero_pool:
        hero_games = item["games"]
        hero_wins = item["wins"] or 0
        hero_pool_data.append(
            {
                "hero_id": item["hero_id"],
                "hero_name": item["hero_name"],
                "games": hero_games,
                "wins": hero_wins,
                "losses": hero_games - hero_wins,
                "winrate": _winrate(hero_wins, hero_games),
            }
        )

    return {
        "games": games,
        "wins": wins,
        "losses": losses,
        "winrate": _winrate(wins, games),
        "kills_avg": _average(kills, stats_games) if stats_games else 0.0,
        "deaths_avg": _average(deaths, stats_games) if stats_games else 0.0,
        "assists_avg": _average(assists, stats_games) if stats_games else 0.0,
        "hero_pool": hero_pool_data,
    }


def get_hero_by_name(name: str):
    return db.execute(
        "SELECT * FROM heroes WHERE LOWER(name) = LOWER(?)",
        (name.strip(),),
        fetchone=True,
    )


def get_hero_by_id(hero_id: int):
    return db.execute(
        "SELECT * FROM heroes WHERE id = ?",
        (hero_id,),
        fetchone=True,
    )


def list_hero_tournaments(hero_id: int):
    return db.execute(
        """
        SELECT DISTINCT t.id, t.name
        FROM tournaments t
        JOIN matches m ON m.tournament_id = t.id
        JOIN player_match_stats pms ON pms.match_id = m.id
        WHERE pms.hero_id = ?
        ORDER BY t.name
        """,
        (hero_id,),
        fetchall=True,
    )


def get_hero_stats(hero_id: int, tournament_id: Optional[int] = None):
    filter_clause = ""
    params: List[int | None] = [hero_id]
    if tournament_id:
        filter_clause = "AND m.tournament_id = ?"
        params.append(tournament_id)

    rows = db.execute(
        f"""
        SELECT pms.*, m.tournament_id
        FROM player_match_stats pms
        JOIN matches m ON m.id = pms.match_id
        WHERE pms.hero_id = ?
        {filter_clause}
        """,
        tuple(params),
        fetchall=True,
    )

    games = len(rows)
    wins = sum(row["is_win"] for row in rows)
    losses = games - wins

    top_players = db.execute(
        f"""
        SELECT pms.player_id,
               pl.nickname,
               COUNT(*) AS games,
               SUM(pms.is_win) AS wins
        FROM player_match_stats pms
        JOIN players pl ON pl.id = pms.player_id
        JOIN matches m ON m.id = pms.match_id
        WHERE pms.hero_id = ?
        {filter_clause}
        GROUP BY pms.player_id, pl.nickname
        ORDER BY games DESC, pl.nickname ASC
        LIMIT 5
        """,
        tuple(params),
        fetchall=True,
    )

    top_players_data = []
    for player in top_players:
        player_games = player["games"]
        player_wins = player["wins"] or 0
        top_players_data.append(
            {
                "player_id": player["player_id"],
                "nickname": player["nickname"],
                "games": player_games,
                "wins": player_wins,
                "losses": player_games - player_wins,
                "winrate": _winrate(player_wins, player_games),
            }
        )

    bans = db.execute(
        f"""
        SELECT COUNT(*) AS ban_count
        FROM hero_bans hb
        JOIN matches m ON m.id = hb.match_id
        WHERE hb.hero_id = ?
        {filter_clause}
        """,
        tuple(params),
        fetchone=True,
    )

    ban_count = bans["ban_count"] if bans else 0

    return {
        "games": games,
        "wins": wins,
        "losses": losses,
        "winrate": _winrate(wins, games),
        "top_players": top_players_data,
        "ban_count": ban_count or 0,
    }
