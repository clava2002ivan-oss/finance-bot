from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..db import db


def get_player_by_nickname(nickname: str):
    query = """
        SELECT players.*, teams.name as team_name, teams.tag as team_tag
        FROM players
        JOIN teams ON teams.id = players.team_id
        WHERE LOWER(players.nickname) = LOWER(?)
        LIMIT 1
    """
    return db.fetchone(query, (nickname,))


def get_player_tournaments(player_id: int) -> List[Dict[str, Any]]:
    query = """
        SELECT DISTINCT tournaments.id, tournaments.name
        FROM tournaments
        JOIN matches ON matches.tournament_id = tournaments.id
        JOIN player_match_stats pms ON pms.match_id = matches.id
        WHERE pms.player_id = ?
        ORDER BY tournaments.name
    """
    rows = db.fetchall(query, (player_id,))
    return [dict(row) for row in rows]


def get_player_stats(player_id: int, tournament_id: Optional[int] = None) -> Dict[str, Any]:
    conditions = ["pms.player_id = ?"]
    params: List[Any] = [player_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)

    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            COUNT(*) as games_total,
            SUM(CASE WHEN pms.is_win = 1 THEN 1 ELSE 0 END) as wins,
            SUM(pms.kills) as total_kills,
            SUM(pms.deaths) as total_deaths,
            SUM(pms.assists) as total_assists
        FROM player_match_stats pms
        JOIN matches m ON m.id = pms.match_id
        WHERE {condition_sql}
    """
    row_data = db.fetchone(query, params)
    row = dict(row_data) if row_data else {}
    games_total = row.get("games_total") or 0
    wins = row.get("wins") or 0
    losses = max(games_total - wins, 0)
    total_kills = row.get("total_kills") or 0
    total_deaths = row.get("total_deaths") or 0
    total_assists = row.get("total_assists") or 0

    deaths_for_kda = total_deaths if total_deaths else 1
    stats = {
        "games_total": games_total,
        "wins": wins,
        "losses": losses,
        "winrate": round((wins / games_total * 100) if games_total else 0, 2),
        "total_kills": total_kills,
        "total_deaths": total_deaths,
        "total_assists": total_assists,
        "avg_kills": round(total_kills / games_total, 2) if games_total else 0,
        "avg_deaths": round(total_deaths / games_total, 2) if games_total else 0,
        "avg_assists": round(total_assists / games_total, 2) if games_total else 0,
        "kda": round((total_kills + total_assists) / deaths_for_kda, 2) if games_total else 0,
    }
    return stats


def get_player_hero_pool(player_id: int, tournament_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conditions = ["pms.player_id = ?"]
    params: List[Any] = [player_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)

    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            pms.hero_id,
            COALESCE(h.name, 'Unknown') AS hero_name,
            COUNT(*) AS games,
            SUM(CASE WHEN pms.is_win = 1 THEN 1 ELSE 0 END) AS wins
        FROM player_match_stats pms
        JOIN matches m ON m.id = pms.match_id
        LEFT JOIN heroes h ON h.id = pms.hero_id
        WHERE {condition_sql}
        GROUP BY pms.hero_id
        ORDER BY games DESC, wins DESC
    """
    rows = db.fetchall(query, params)
    pool = []
    for row in rows:
        games = row["games"] or 0
        wins = row["wins"] or 0
        pool.append(
            {
                "hero_id": row["hero_id"],
                "hero_name": row["hero_name"],
                "games": games,
                "wins": wins,
                "losses": max(games - wins, 0),
                "winrate": round((wins / games * 100) if games else 0, 2),
            }
        )
    return pool


def get_team_by_name_or_tag(query_text: str):
    query = """
        SELECT *
        FROM teams
        WHERE LOWER(name) = LOWER(?) OR LOWER(tag) = LOWER(?)
        LIMIT 1
    """
    return db.fetchone(query, (query_text, query_text))


def get_team_tournaments(team_id: int) -> List[Dict[str, Any]]:
    query = """
        SELECT DISTINCT t.id, t.name
        FROM tournaments t
        JOIN matches m ON m.tournament_id = t.id
        WHERE m.team_a_id = ? OR m.team_b_id = ?
        ORDER BY t.name
    """
    rows = db.fetchall(query, (team_id, team_id))
    return [dict(row) for row in rows]


def get_team_stats(team_id: int, tournament_id: Optional[int] = None) -> Dict[str, Any]:
    conditions = ["(m.team_a_id = ? OR m.team_b_id = ?)"]
    params: List[Any] = [team_id, team_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)

    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            m.id,
            m.winner_team_id
        FROM matches m
        WHERE {condition_sql}
    """
    matches = db.fetchall(query, params)
    games_total = len(matches)
    wins = sum(1 for match in matches if match["winner_team_id"] == team_id)
    losses = max(games_total - wins, 0)
    winrate = round((wins / games_total * 100) if games_total else 0, 2)

    match_ids = [match["id"] for match in matches]
    total_kills = total_deaths = total_assists = 0
    if match_ids:
        placeholders = ",".join("?" for _ in match_ids)
        kda_query = f"""
            SELECT
                SUM(pms.kills) AS kills,
                SUM(pms.deaths) AS deaths,
                SUM(pms.assists) AS assists
            FROM player_match_stats pms
            JOIN players p ON p.id = pms.player_id
            WHERE p.team_id = ?
              AND pms.match_id IN ({placeholders})
        """
        row_data = db.fetchone(kda_query, [team_id, *match_ids])
        row = dict(row_data) if row_data else {}
        total_kills = row.get("kills") or 0
        total_deaths = row.get("deaths") or 0
        total_assists = row.get("assists") or 0

    stats = {
        "games_total": games_total,
        "wins": wins,
        "losses": losses,
        "winrate": winrate,
        "avg_kills": round(total_kills / games_total, 2) if games_total else 0,
        "avg_deaths": round(total_deaths / games_total, 2) if games_total else 0,
        "avg_assists": round(total_assists / games_total, 2) if games_total else 0,
    }
    return stats


def get_team_hero_pool(team_id: int, tournament_id: Optional[int] = None) -> List[Dict[str, Any]]:
    conditions = ["p.team_id = ?"]
    params: List[Any] = [team_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)

    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            pms.hero_id,
            COALESCE(h.name, 'Unknown') AS hero_name,
            COUNT(*) AS games,
            SUM(CASE WHEN pms.is_win = 1 THEN 1 ELSE 0 END) AS wins
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id
        JOIN matches m ON m.id = pms.match_id
        LEFT JOIN heroes h ON h.id = pms.hero_id
        WHERE {condition_sql}
        GROUP BY pms.hero_id
        ORDER BY games DESC, wins DESC
    """
    rows = db.fetchall(query, params)
    pool = []
    for row in rows:
        games = row["games"] or 0
        wins = row["wins"] or 0
        pool.append(
            {
                "hero_id": row["hero_id"],
                "hero_name": row["hero_name"],
                "games": games,
                "wins": wins,
                "losses": max(games - wins, 0),
                "winrate": round((wins / games * 100) if games else 0, 2),
            }
        )
    return pool


def get_hero_by_name(name: str):
    query = "SELECT * FROM heroes WHERE LOWER(name) = LOWER(?) LIMIT 1"
    return db.fetchone(query, (name,))


def get_hero_stats(hero_id: int, tournament_id: Optional[int] = None) -> Dict[str, Any]:
    conditions = ["pms.hero_id = ?"]
    params: List[Any] = [hero_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)
    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            COUNT(*) AS games_total,
            SUM(CASE WHEN pms.is_win = 1 THEN 1 ELSE 0 END) AS wins
        FROM player_match_stats pms
        JOIN matches m ON m.id = pms.match_id
        WHERE {condition_sql}
    """
    row_data = db.fetchone(query, params)
    row = dict(row_data) if row_data else {}
    games_total = row.get("games_total") or 0
    wins = row.get("wins") or 0
    losses = max(games_total - wins, 0)
    winrate = round((wins / games_total * 100) if games_total else 0, 2)
    return {"games_total": games_total, "wins": wins, "losses": losses, "winrate": winrate}


def get_hero_tournaments(hero_id: int) -> List[Dict[str, Any]]:
    query = """
        SELECT DISTINCT t.id, t.name
        FROM tournaments t
        JOIN matches m ON m.tournament_id = t.id
        JOIN player_match_stats pms ON pms.match_id = m.id
        WHERE pms.hero_id = ?
        ORDER BY t.name
    """
    rows = db.fetchall(query, (hero_id,))
    return [dict(row) for row in rows]


def get_hero_top_players(hero_id: int, tournament_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
    conditions = ["pms.hero_id = ?"]
    params: List[Any] = [hero_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)
    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT
            p.id as player_id,
            p.nickname,
            t.name as team_name,
            COUNT(*) AS games,
            SUM(CASE WHEN pms.is_win = 1 THEN 1 ELSE 0 END) AS wins
        FROM player_match_stats pms
        JOIN players p ON p.id = pms.player_id
        JOIN teams t ON t.id = p.team_id
        JOIN matches m ON m.id = pms.match_id
        WHERE {condition_sql}
        GROUP BY p.id
        ORDER BY games DESC, wins DESC
        LIMIT ?
    """
    rows = db.fetchall(query, [*params, limit])
    top_players = []
    for row in rows:
        games = row["games"] or 0
        wins = row["wins"] or 0
        top_players.append(
            {
                "player_id": row["player_id"],
                "nickname": row["nickname"],
                "team_name": row["team_name"],
                "games": games,
                "wins": wins,
                "losses": max(games - wins, 0),
                "winrate": round((wins / games * 100) if games else 0, 2),
            }
        )
    return top_players


def get_hero_ban_stats(hero_id: int, tournament_id: Optional[int] = None) -> Dict[str, Any]:
    conditions = ["hb.hero_id = ?"]
    params: List[Any] = [hero_id]
    if tournament_id:
        conditions.append("m.tournament_id = ?")
        params.append(tournament_id)
    condition_sql = " AND ".join(conditions)
    query = f"""
        SELECT COUNT(*) AS ban_count
        FROM hero_bans hb
        JOIN matches m ON m.id = hb.match_id
        WHERE {condition_sql}
    """
    row_data = db.fetchone(query, params)
    row = dict(row_data) if row_data else {}
    return {"ban_count": row.get("ban_count") or 0}
