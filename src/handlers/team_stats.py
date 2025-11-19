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

router = Router(name="team_stats")


class TeamStatsState(StatesGroup):
    waiting_scope = State()


class TeamScopeCallback(CallbackData, prefix="team_scope"):
    team_id: int
    tournament_id: int


@router.message(Command("team_stats"))
async def handle_team_stats(message: Message, command: CommandObject, state: FSMContext) -> None:
    query_text = (command.args or "").strip()
    if not query_text:
        await message.answer("Укажи название или тег команды: /team_stats ONIC")
        return

    team = stats_service.get_team_by_name_or_tag(query_text)
    if not team:
        await message.answer(f"Команда {query_text} не найдена.")
        return

    await state.update_data(team=dict(team))

    tournaments = stats_service.get_team_tournaments(team["id"])

    builder = InlineKeyboardBuilder()
    builder.button(
        text="Все время",
        callback_data=TeamScopeCallback(team_id=team["id"], tournament_id=0).pack(),
    )
    for t in tournaments:
        builder.button(
            text=t["name"],
            callback_data=TeamScopeCallback(team_id=team["id"], tournament_id=t["id"]).pack(),
        )
    builder.adjust(1)

    await message.answer(
        f"Показать статистику {team['name']} за:",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(TeamStatsState.waiting_scope)


@router.callback_query(TeamScopeCallback.filter(), TeamStatsState.waiting_scope)
async def on_team_scope_selected(
    callback: CallbackQuery,
    callback_data: TeamScopeCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    team = data.get("team")
    if not team or team["id"] != callback_data.team_id:
        await callback.answer("Сессия устарела. Запусти команду заново.")
        await state.clear()
        return

    tournament_id = callback_data.tournament_id or None
    tournament_name = "Все турниры" if callback_data.tournament_id == 0 else None

    if tournament_name is None:
        tournaments = stats_service.get_team_tournaments(team["id"])
        tournament = next((t for t in tournaments if t["id"] == callback_data.tournament_id), None)
        tournament_name = tournament["name"] if tournament else "Турнир"

    await _send_team_stats(callback.message, team, tournament_id, tournament_name)
    await callback.answer()
    await state.clear()


async def _send_team_stats(
    message: Message,
    team: Dict[str, Any],
    tournament_id: Optional[int],
    tournament_name: str,
) -> None:
    stats = stats_service.get_team_stats(team["id"], tournament_id)
    if not stats.get("games_total"):
        await message.answer("Нет матчей для выбранного набора.")
        return

    hero_pool = stats_service.get_team_hero_pool(team["id"], tournament_id)
    top_heroes = hero_pool[:5]
    heroes_text = "\n".join(
        f"{idx+1}. {hero['hero_name']} — {hero['wins']}W/{hero['losses']}L ({hero['winrate']}%)"
        for idx, hero in enumerate(top_heroes)
    ) or "Нет данных по героям."

    payload = {
        "team": {"name": team["name"], "tag": team["tag"]},
        "tournament": tournament_name,
        "stats": stats,
        "top_heroes": top_heroes,
    }

    analysis = await ai_client.generate_team_report(payload)

    summary_lines = [
        f"Команда: {team['name']} ({team['tag']})",
        f"Турнир: {tournament_name}",
        f"Матчей: {stats['games_total']} | Победы: {stats['wins']} | WR: {stats['winrate']}%",
        f"Средние K/D/A: {stats['avg_kills']}/{stats['avg_deaths']}/{stats['avg_assists']}",
        "",
        "Топ герои:",
        heroes_text,
    ]

    await message.answer("\n".join(summary_lines) + f"\n\n{analysis}")
