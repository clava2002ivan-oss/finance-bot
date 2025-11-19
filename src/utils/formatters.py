from __future__ import annotations

from typing import Iterable, Mapping


def format_hero_pool(hero_pool: Iterable[Mapping[str, object]]) -> str:
    hero_pool = list(hero_pool)
    if not hero_pool:
        return "Нет данных по героям."
    lines = []
    for hero in hero_pool:
        wins = int(hero.get("wins", 0))
        losses = int(hero.get("losses", 0))
        games = int(hero.get("games", wins + losses))
        winrate = hero.get("winrate", 0)
        lines.append(
            f"{hero.get('hero_name')} — {wins}W ({winrate}%) / {losses}L / {games} игр"
        )
    return "\n".join(lines)


def format_top_players(players: Iterable[Mapping[str, object]]) -> str:
    players = list(players)
    if not players:
        return "Нет игроков с играми на этом герое."
    lines = []
    for player in players:
        wins = int(player.get("wins", 0))
        losses = int(player.get("losses", 0))
        games = int(player.get("games", wins + losses))
        winrate = player.get("winrate", 0)
        lines.append(
            f"{player.get('nickname')} — {wins}W ({winrate}%) / {losses}L / {games} игр"
        )
    return "\n".join(lines)
