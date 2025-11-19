from __future__ import annotations

from typing import Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..ai_client import generate_hero_analysis
from ..services import stats_service, tournaments_service
from ..utils.formatters import format_top_players


router = Router(name="hero_stats")


class HeroStatsCallback(CallbackData, prefix="hero_stats"):
    hero_id: int
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
    tournament = tournaments_service.get_tournament_by_id(tournament_id)
    return tournament["name"] if tournament else "Неизвестный турнир"


async def _send_hero_stats(
    target: Message | CallbackQuery,
    hero_id: int,
    tournament_id: Optional[int],
):
    hero = stats_service.get_hero_by_id(hero_id)
    if not hero:
        await _reply(target, "Герой не найден.")
        return

    stats = stats_service.get_hero_stats(hero_id, tournament_id)
    if stats["games"] == 0:
        await _reply(target, "Нет игр с этим героем в выбранном диапазоне.")
        return

    tournament_name = _tournament_name(tournament_id)
    payload = {
        "hero": hero["name"],
        "tournament": tournament_name,
        "summary": {
            "games": stats["games"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "winrate": stats["winrate"],
            "ban_count": stats["ban_count"],
        },
        "top_players": stats["top_players"],
    }

    ai_text = generate_hero_analysis(payload)
    top_players_text = format_top_players(stats["top_players"])
    ban_text = f"Баны: {stats['ban_count']}" if stats["ban_count"] else "Баны: нет данных"
    message = (
        f"🦸 {hero['name']} — {tournament_name}\n\n"
        f"{ai_text}\n\n"
        f"{ban_text}\n"
        f"Лучшие игроки:\n{top_players_text}"
    )
    await _reply(target, message)


@router.message(Command("hero_stats"))
async def handle_hero_stats(message: Message, command: CommandObject):
    args = (command.args or "").strip()
    if not args:
        await message.answer("Использование: /hero_stats <название героя>")
        return

    hero = stats_service.get_hero_by_name(args)
    if not hero:
        await message.answer(f"Герой {args} не найден.")
        return

    tournaments = stats_service.list_hero_tournaments(hero["id"])
    user_id = message.from_user.id if message.from_user else 0
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Все турниры",
        callback_data=HeroStatsCallback(
            hero_id=hero["id"], tournament_id=0, user_id=user_id
        ).pack(),
    )
    for tournament in tournaments:
        builder.button(
            text=tournament["name"],
            callback_data=HeroStatsCallback(
                hero_id=hero["id"], tournament_id=tournament["id"], user_id=user_id
            ).pack(),
        )
    builder.adjust(1)

    await message.answer(
        "Показать статистику по всем турнирам или выбрать конкретный?",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(HeroStatsCallback.filter())
async def handle_hero_stats_callback(callback: CallbackQuery, callback_data: HeroStatsCallback):
    if not callback.from_user or callback_data.user_id != callback.from_user.id:
        await callback.answer("Недоступно.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_reply_markup()

    await _send_hero_stats(
        callback,
        callback_data.hero_id,
        callback_data.tournament_id or None,
    )
