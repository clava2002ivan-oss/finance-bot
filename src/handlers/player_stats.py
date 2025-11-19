from __future__ import annotations

from typing import Any, Dict, List, Optional

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from .. import ai_client
from ..services import stats_service


router = Router(name="player_stats")


class PlayerStatsState(StatesGroup):
    waiting_tournament = State()
    waiting_pool_confirmation = State()


class PlayerTournamentCallback(CallbackData, prefix="player_tournament"):
    player_id: int
    tournament_id: int


class PlayerPoolCallback(CallbackData, prefix="player_pool"):
    player_id: int
    action: str  # yes/no


@router.message(Command("player_stats"))
async def handle_player_stats(message: Message, command: CommandObject, state: FSMContext) -> None:
    nickname = (command.args or "").strip()
    if not nickname:
        await message.answer("Укажи ник игрока: /player_stats Kairi")
        return

    player_row = stats_service.get_player_by_nickname(nickname)
    if not player_row:
        await message.answer(f"Игрока с ником {nickname} не найдено. Проверь написание.")
        return
    player = dict(player_row)

    tournaments = stats_service.get_player_tournaments(player["id"])
    if not tournaments:
        await message.answer("Для этого игрока пока нет сыгранных матчей.")
        return

    await state.update_data(player=dict(player))

    if len(tournaments) == 1:
        tournament = tournaments[0]
        await _send_player_stats(message, state, player, tournament["id"], tournament["name"])
        return

    builder = InlineKeyboardBuilder()
    for tournament in tournaments:
        builder.button(
            text=tournament["name"],
            callback_data=PlayerTournamentCallback(player_id=player["id"], tournament_id=tournament["id"]).pack(),
        )
    builder.button(
        text="Все турниры",
        callback_data=PlayerTournamentCallback(player_id=player["id"], tournament_id=0).pack(),
    )
    builder.adjust(1)
    await message.answer(f"За какой турнир показать статистику {player['nickname']}?", reply_markup=builder.as_markup())
    await state.set_state(PlayerStatsState.waiting_tournament)


@router.callback_query(PlayerTournamentCallback.filter(), PlayerStatsState.waiting_tournament)
async def on_player_tournament_choice(
    callback: CallbackQuery,
    callback_data: PlayerTournamentCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    player = data.get("player")
    if not player or player["id"] != callback_data.player_id:
        await callback.answer("Сессия устарела. Запроси статистику заново.")
        await state.clear()
        return

    tournament_id = callback_data.tournament_id or None
    tournament_name = "Все турниры" if callback_data.tournament_id == 0 else None

    if tournament_name is None:
        tournaments = stats_service.get_player_tournaments(player["id"])
        tournament = next((t for t in tournaments if t["id"] == callback_data.tournament_id), None)
        tournament_name = tournament["name"] if tournament else "Турнир"

    await _send_player_stats(callback.message, state, player, tournament_id, tournament_name)
    await callback.answer()


@router.callback_query(PlayerPoolCallback.filter(), PlayerStatsState.waiting_pool_confirmation)
async def on_player_pool_choice(
    callback: CallbackQuery,
    callback_data: PlayerPoolCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    player = data.get("player")
    if not player or player["id"] != callback_data.player_id:
        await callback.answer("Сессия устарела.")
        await state.clear()
        return

    if callback_data.action == "yes":
        hero_pool: List[Dict[str, Any]] = data.get("hero_pool", [])
        nickname: str = player["nickname"]
        tournament_name = data.get("tournament_name", "турнир")
        if hero_pool:
            lines = [
                f"{entry['hero_name']} — {entry['wins']}W ({entry['winrate']}%) / "
                f"{entry['losses']}L / {entry['games']} игр"
                for entry in hero_pool
            ]
            text = "\n".join(lines)
        else:
            text = "Нет сыгранных героев для выбранного турнира."
        await callback.message.answer(f"Пул героев {nickname} ({tournament_name}):\n{text}")
    else:
        await callback.message.answer("Ок, если потребуется полный пул — запроси позже.")

    await callback.answer()
    await state.clear()


async def _send_player_stats(
    message: Message,
    state: FSMContext,
    player: Dict[str, Any],
    tournament_id: Optional[int],
    tournament_name: str,
) -> None:
    stats = stats_service.get_player_stats(player["id"], tournament_id)
    if not stats.get("games_total"):
        await message.answer("Нет матчей для выбранного турнира.")
        await state.clear()
        return

    hero_pool = stats_service.get_player_hero_pool(player["id"], tournament_id)

    payload = {
        "player": {
            "nickname": player["nickname"],
            "team": player.get("team_name"),
            "role": player.get("role"),
        },
        "tournament": tournament_name,
        "stats": stats,
        "top_heroes": hero_pool[:5],
    }
    analysis = await ai_client.generate_player_report(payload)

    summary_lines = [
        f"Игрок: {player['nickname']} ({player.get('team_name', 'без команды')})",
        f"Турнир: {tournament_name}",
        f"Игры: {stats['games_total']} | Победы: {stats['wins']} | WR: {stats['winrate']}%",
        f"KDA: {stats['kda']} (Avg {stats['avg_kills']}/{stats['avg_deaths']}/{stats['avg_assists']})",
    ]
    text = "\n".join(summary_lines) + f"\n\n{analysis}"
    await message.answer(text)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="Да",
        callback_data=PlayerPoolCallback(player_id=player["id"], action="yes").pack(),
    )
    builder.button(
        text="Нет",
        callback_data=PlayerPoolCallback(player_id=player["id"], action="no").pack(),
    )
    builder.adjust(2)
    await message.answer(
        f"Показать полный список всех героев, на которых играл {player['nickname']}?",
        reply_markup=builder.as_markup(),
    )

    await state.set_state(PlayerStatsState.waiting_pool_confirmation)
    await state.update_data(hero_pool=hero_pool, tournament_name=tournament_name)
