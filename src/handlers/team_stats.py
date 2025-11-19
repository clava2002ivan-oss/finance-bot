from __future__ import annotations

from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..ai_client import generate_team_analysis
from ..services import stats_service, tournaments_service
from ..utils.formatters import format_hero_pool


router = Router(name="team_stats")


class TeamStatsCallback(CallbackData, prefix="team_stats"):
    team_id: int
    tournament_id: int
    user_id: int


async def _reply(target: Message | CallbackQuery, text: str):
    if isinstance(target, CallbackQuery):
        if target.message:
            await target.message.answer(text)
        await target.answer()
    else:
        await target.answer(text)


def _tournament_name(tournament_id: Optional[int]) -> str:
    if not tournament_id:
        return "Все турниры"
    record = tournaments_service.get_tournament_by_id(tournament_id)
    return record["name"] if record else "Неизвестный турнир"


async def _send_team_stats(
    target: Message | CallbackQuery,
    team_id: int,
    tournament_id: Optional[int],
):
    team = stats_service.get_team_by_id(team_id)
    if not team:
        await _reply(target, "Команда не найдена.")
        return

    stats = stats_service.get_team_stats(team["id"], tournament_id)
    if stats["games"] == 0:
        await _reply(target, "Нет матчей для выбранного диапазона.")
        return

    tournament_name = _tournament_name(tournament_id)
    payload = {
        "team": team["name"],
        "tag": team["tag"],
        "tournament": tournament_name,
        "summary": {
            "games": stats["games"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "winrate": stats["winrate"],
            "kills_avg": stats["kills_avg"],
            "deaths_avg": stats["deaths_avg"],
            "assists_avg": stats["assists_avg"],
        },
        "top_heroes": stats["hero_pool"][:5],
    }

    ai_text = generate_team_analysis(payload)
    body = (
        f"🏆 {team['name']} ({team['tag']}) — {tournament_name}\n\n"
        f"{ai_text}\n\n"
        f"🔑 Топ героев:\n{format_hero_pool(stats['hero_pool'][:5])}"
    )
    await _reply(target, body)


@router.message(Command("team_stats"))
async def handle_team_stats(message: Message, command: CommandObject):
    args = (command.args or "").strip()
    if not args:
        await message.answer("Использование: /team_stats <название или тег>")
        return

    team = stats_service.get_team_by_identifier(args)
    if not team:
        await message.answer(f"Команда {args} не найдена.")
        return

    tournaments = stats_service.list_team_tournaments(team["id"])
    user_id = message.from_user.id if message.from_user else 0
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Все турниры",
        callback_data=TeamStatsCallback(
            team_id=team["id"], tournament_id=0, user_id=user_id
        ).pack(),
    )
    for tournament in tournaments:
        builder.button(
            text=tournament["name"],
            callback_data=TeamStatsCallback(
                team_id=team["id"], tournament_id=tournament["id"], user_id=user_id
            ).pack(),
        )
    builder.adjust(1)

    await message.answer(
        "Показать статистику за все время или конкретный турнир?",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(TeamStatsCallback.filter())
async def handle_team_stats_callback(callback: CallbackQuery, callback_data: TeamStatsCallback):
    if not callback.from_user or callback_data.user_id != callback.from_user.id:
        await callback.answer("Команда недоступна.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_reply_markup()

    await _send_team_stats(
        callback,
        callback_data.team_id,
        callback_data.tournament_id or None,
    )
