from __future__ import annotations

from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.filters.command import CommandObject
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..ai_client import generate_player_analysis
from ..services import stats_service, tournaments_service
from ..utils.formatters import format_hero_pool


router = Router(name="player_stats")


class PlayerTournamentCallback(CallbackData, prefix="player_t"):
    player_id: int
    tournament_id: int
    user_id: int


class PlayerHeroPoolCallback(CallbackData, prefix="player_hp"):
    player_id: int
    tournament_id: int
    user_id: int


async def _reply(target: Message | CallbackQuery, text: str, **kwargs):
    if isinstance(target, CallbackQuery):
        if target.message:
            await target.message.answer(text, **kwargs)
        await target.answer()
    else:
        await target.answer(text, **kwargs)


def _resolve_tournament_name(tournament_id: int | None) -> str:
    if not tournament_id:
        return "Все турниры"
    tournament = tournaments_service.get_tournament_by_id(tournament_id)
    return tournament["name"] if tournament else "Неизвестный турнир"


async def _send_player_stats(
    target: Message | CallbackQuery,
    player_id: int,
    tournament_id: Optional[int],
    user_id: int,
):
    player = stats_service.get_player_by_id(player_id)
    if not player:
        await _reply(target, "Игрок больше не существует в базе.")
        return

    stats = stats_service.get_player_stats(player_id, tournament_id)
    if stats["games"] == 0:
        await _reply(target, "Для выбранного турнира пока нет сыгранных карт.")
        return

    tournament_name = _resolve_tournament_name(tournament_id)
    payload = {
        "player": {
            "nickname": player["nickname"],
            "team": player["team_name"],
            "role": player["role"],
        },
        "tournament": tournament_name,
        "summary": {
            "games": stats["games"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "winrate": stats["winrate"],
            "kda": stats["kda"],
            "avg_kills": stats["kills"]["avg"],
            "avg_deaths": stats["deaths"]["avg"],
            "avg_assists": stats["assists"]["avg"],
        },
        "top_heroes": stats["hero_pool"][:5],
    }

    ai_text = generate_player_analysis(payload)
    message_body = (
        f"📊 Статистика {player['nickname']} ({player['team_name']}) — {tournament_name}\n\n"
        f"{ai_text}"
    )
    await _reply(target, message_body)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="Да",
        callback_data=PlayerHeroPoolCallback(
            player_id=player_id,
            tournament_id=tournament_id or 0,
            user_id=user_id,
        ).pack(),
    )
    builder.button(text="Нет", callback_data="player_hp:skip")
    builder.adjust(2)

    message = target.message if isinstance(target, CallbackQuery) else target
    if message:
        await message.answer(
            f"Показать полный список героев для {player['nickname']}?",
            reply_markup=builder.as_markup(),
        )


@router.message(Command("player_stats"))
async def handle_player_stats(message: Message, command: CommandObject):
    args = (command.args or "").strip()
    if not args:
        await message.answer("Использование: /player_stats <ник>")
        return

    player = stats_service.get_player_by_nickname(args)
    if not player:
        await message.answer(f"Игрока с ником {args} не найдено. Проверь написание.")
        return

    tournaments = stats_service.list_player_tournaments(player["id"])
    user_id = message.from_user.id if message.from_user else 0
    if not tournaments:
        await message.answer("Для этого игрока пока нет матчей в базе.")
        return

    if len(tournaments) == 1:
        await _send_player_stats(message, player["id"], tournaments[0]["id"], user_id)
        return

    builder = InlineKeyboardBuilder()
    for tournament in tournaments:
        builder.button(
            text=tournament["name"],
            callback_data=PlayerTournamentCallback(
                player_id=player["id"],
                tournament_id=tournament["id"],
                user_id=user_id,
            ).pack(),
        )
    builder.button(
        text="Все турниры",
        callback_data=PlayerTournamentCallback(
            player_id=player["id"],
            tournament_id=0,
            user_id=user_id,
        ).pack(),
    )
    builder.adjust(1)

    await message.answer(
        f"За какой турнир показать статистику {player['nickname']}?",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(PlayerTournamentCallback.filter())
async def handle_player_tournament_callback(
    callback: CallbackQuery, callback_data: PlayerTournamentCallback
):
    if not callback.from_user or callback_data.user_id != callback.from_user.id:
        await callback.answer("Эта кнопка недоступна.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_reply_markup()
    tournament_id = callback_data.tournament_id or None
    await _send_player_stats(callback, callback_data.player_id, tournament_id, callback_data.user_id)


@router.callback_query(PlayerHeroPoolCallback.filter())
async def handle_player_hero_pool(callback: CallbackQuery, callback_data: PlayerHeroPoolCallback):
    if not callback.from_user or callback_data.user_id != callback.from_user.id:
        await callback.answer("Эта кнопка недоступна.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_reply_markup()

    stats = stats_service.get_player_stats(
        callback_data.player_id,
        callback_data.tournament_id or None,
    )
    player = stats_service.get_player_by_id(callback_data.player_id)
    text = format_hero_pool(stats["hero_pool"])
    tournament_name = _resolve_tournament_name(callback_data.tournament_id or None)
    await _reply(callback, f"Полный hero pool {player['nickname']} ({tournament_name}):\n\n{text}")


@router.callback_query(F.data == "player_hp:skip")
async def handle_player_hero_pool_skip(callback: CallbackQuery):
    if callback.message:
        await callback.message.edit_reply_markup()
    await callback.answer("Ок, ничего не отправляю.")
