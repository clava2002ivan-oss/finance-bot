from __future__ import annotations

from typing import Any, Dict, Optional

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from .. import ai_client
from ..services import stats_service


router = Router(name="hero_stats")


class HeroStatsState(StatesGroup):
    waiting_scope = State()


class HeroScopeCallback(CallbackData, prefix="hero_scope"):
    hero_id: int
    tournament_id: int


@router.message(Command("hero_stats"))
async def handle_hero_stats(message: Message, command: CommandObject, state: FSMContext) -> None:
    name = (command.args or "").strip()
    if not name:
        await message.answer("Укажи имя героя: /hero_stats Lancelot")
        return

    hero_row = stats_service.get_hero_by_name(name)
    if not hero_row:
        await message.answer(f"Герой {name} не найден.")
        return
    hero = dict(hero_row)

    tournaments = stats_service.get_hero_tournaments(hero["id"])
    await state.update_data(hero=dict(hero))

    builder = InlineKeyboardBuilder()
    builder.button(
        text="Все турниры",
        callback_data=HeroScopeCallback(hero_id=hero["id"], tournament_id=0).pack(),
    )
    for t in tournaments:
        builder.button(
            text=t["name"],
            callback_data=HeroScopeCallback(hero_id=hero["id"], tournament_id=t["id"]).pack(),
        )
    builder.adjust(1)

    await message.answer(
        f"Выбери турнир для героя {hero['name']} (или Все турниры):",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(HeroStatsState.waiting_scope)


@router.callback_query(HeroScopeCallback.filter(), HeroStatsState.waiting_scope)
async def on_hero_scope_selected(
    callback: CallbackQuery,
    callback_data: HeroScopeCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    hero = data.get("hero")
    if not hero or hero["id"] != callback_data.hero_id:
        await callback.answer("Сессия устарела, запроси заново.")
        await state.clear()
        return

    tournament_id = callback_data.tournament_id or None
    tournament_name = "Все турниры" if callback_data.tournament_id == 0 else None

    if tournament_name is None:
        tournaments = stats_service.get_hero_tournaments(hero["id"])
        tournament = next((t for t in tournaments if t["id"] == callback_data.tournament_id), None)
        tournament_name = tournament["name"] if tournament else "Турнир"

    await _send_hero_stats(callback.message, hero, tournament_id, tournament_name)
    await callback.answer()
    await state.clear()


async def _send_hero_stats(
    message: Message,
    hero: Dict[str, Any],
    tournament_id: Optional[int],
    tournament_name: str,
) -> None:
    stats = stats_service.get_hero_stats(hero["id"], tournament_id)
    if not stats.get("games_total"):
        await message.answer("Для героя нет матчей в выбранном диапазоне.")
        return

    top_players = stats_service.get_hero_top_players(hero["id"], tournament_id)
    bans = stats_service.get_hero_ban_stats(hero["id"], tournament_id)

    payload = {
        "hero": {"name": hero["name"], "role": hero.get("role")},
        "tournament": tournament_name,
        "stats": stats,
        "top_players": top_players,
        "ban_stats": bans,
    }

    analysis = await ai_client.generate_hero_report(payload)

    players_text = "\n".join(
        f"{idx+1}. {player['nickname']} ({player['team_name']}) — {player['wins']}W/"
        f"{player['losses']}L ({player['winrate']}%)"
        for idx, player in enumerate(top_players)
    ) or "Нет игроков с матчами на этом герое."

    lines = [
        f"Герой: {hero['name']}",
        f"Турнир: {tournament_name}",
        f"Матчей: {stats['games_total']} | Победы: {stats['wins']} | WR: {stats['winrate']}%",
        f"Ban count: {bans.get('ban_count', 0)}",
        "",
        "Топ игроки:",
        players_text,
    ]

    await message.answer("\n".join(lines) + f"\n\n{analysis}")
