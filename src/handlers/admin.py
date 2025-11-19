from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from ..config import settings
from ..services import admin_service, stats_service, tournaments_service


router = Router(name="admin")

ROLE_CHOICES = {"gold", "exp", "mid", "jungle", "roam"}


class AddTeamState(StatesGroup):
    waiting_name = State()
    waiting_tag = State()
    waiting_region = State()


class AddPlayerState(StatesGroup):
    waiting_nickname = State()
    waiting_team = State()
    waiting_role = State()


class AddMatchState(StatesGroup):
    waiting_tournament = State()
    waiting_team_a = State()
    waiting_team_b = State()
    waiting_winner = State()
    confirm_lineups = State()
    collecting_lineups = State()


class MatchLineupCallback(CallbackData, prefix="match_lineup"):
    decision: str  # yes / no


def _is_admin(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in settings.admin_ids)


async def _ensure_admin(message: Message) -> bool:
    if _is_admin(message):
        return True
    await message.answer("Эта команда доступна только администраторам.")
    return False


@router.message(Command("add_team"))
async def cmd_add_team(message: Message, state: FSMContext) -> None:
    if not await _ensure_admin(message):
        return
    await state.set_state(AddTeamState.waiting_name)
    await message.answer("Введи полное название команды:")


@router.message(AddTeamState.waiting_name)
async def add_team_set_name(message: Message, state: FSMContext) -> None:
    await state.update_data(team_name=message.text.strip())
    await state.set_state(AddTeamState.waiting_tag)
    await message.answer("Введи тег команды (до 5 символов):")


@router.message(AddTeamState.waiting_tag)
async def add_team_set_tag(message: Message, state: FSMContext) -> None:
    await state.update_data(team_tag=message.text.strip())
    await state.set_state(AddTeamState.waiting_region)
    await message.answer("Регион (можно пропустить, отправь - ):")


@router.message(AddTeamState.waiting_region)
async def add_team_finish(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    region = message.text.strip()
    region = None if region == "-" else region
    team = admin_service.add_team(data["team_name"], data["team_tag"], region)
    await message.answer(f"Команда {team['name']} ({team['tag']}) добавлена.")
    await state.clear()


@router.message(Command("add_player"))
async def cmd_add_player(message: Message, state: FSMContext) -> None:
    if not await _ensure_admin(message):
        return
    teams = admin_service.list_teams()
    if not teams:
        await message.answer("Сначала добавь хотя бы одну команду через /add_team.")
        return
    await state.update_data(teams=teams)
    await state.set_state(AddPlayerState.waiting_nickname)
    await message.answer("Введи ник игрока:")


@router.message(AddPlayerState.waiting_nickname)
async def add_player_set_nickname(message: Message, state: FSMContext) -> None:
    await state.update_data(player_nickname=message.text.strip())
    teams = await state.get_data()
    teams_list = "\n".join(f"- {item['name']} ({item['tag']})" for item in teams["teams"])
    await state.set_state(AddPlayerState.waiting_team)
    await message.answer(f"Выбери команду (введи тег или название):\n{teams_list}")


@router.message(AddPlayerState.waiting_team)
async def add_player_set_team(message: Message, state: FSMContext) -> None:
    team_row = admin_service.find_team_by_name_or_tag(message.text.strip())
    if not team_row:
        await message.answer("Команда не найдена, попробуй ещё раз.")
        return
    await state.update_data(player_team=dict(team_row))
    await state.set_state(AddPlayerState.waiting_role)
    await message.answer("Введи роль игрока (gold/exp/mid/jungle/roam):")


@router.message(AddPlayerState.waiting_role)
async def add_player_finish(message: Message, state: FSMContext) -> None:
    role = message.text.strip().lower()
    if role not in ROLE_CHOICES:
        await message.answer("Некорректная роль. Доступны: gold, exp, mid, jungle, roam.")
        return
    data = await state.get_data()
    player = admin_service.add_player(data["player_nickname"], data["player_team"]["id"], role)
    await message.answer(
        f"Игрок {player['nickname']} добавлен в команду {data['player_team']['name']} ({role})."
    )
    await state.clear()


@router.message(Command("add_match"))
async def cmd_add_match(message: Message, state: FSMContext) -> None:
    if not await _ensure_admin(message):
        return
    if len(admin_service.list_teams()) < 2:
        await message.answer("Нужно минимум две команды в БД, добавь их через /add_team.")
        return
    await state.set_state(AddMatchState.waiting_tournament)
    await message.answer("Введи название турнира (если нет — будет создан):")


@router.message(AddMatchState.waiting_tournament)
async def add_match_set_tournament(message: Message, state: FSMContext) -> None:
    tournament = tournaments_service.get_or_create_tournament(message.text.strip())
    await state.update_data(tournament=tournament)
    await state.set_state(AddMatchState.waiting_team_a)
    await message.answer("Введи название или тег команды A:")


@router.message(AddMatchState.waiting_team_a)
async def add_match_team_a(message: Message, state: FSMContext) -> None:
    team_row = admin_service.find_team_by_name_or_tag(message.text.strip())
    if not team_row:
        await message.answer("Команда не найдена. Попробуй снова.")
        return
    await state.update_data(team_a=dict(team_row))
    await state.set_state(AddMatchState.waiting_team_b)
    await message.answer("Введи название или тег команды B:")


@router.message(AddMatchState.waiting_team_b)
async def add_match_team_b(message: Message, state: FSMContext) -> None:
    team_b_row = admin_service.find_team_by_name_or_tag(message.text.strip())
    if not team_b_row:
        await message.answer("Команда не найдена. Попробуй снова.")
        return
    data = await state.get_data()
    if team_b_row["id"] == data["team_a"]["id"]:
        await message.answer("Команда B должна отличаться от команды A.")
        return
    await state.update_data(team_b=dict(team_b_row))
    await state.set_state(AddMatchState.waiting_winner)
    await message.answer("Кто победил? (введи A или B):")


@router.message(AddMatchState.waiting_winner)
async def add_match_set_winner(message: Message, state: FSMContext) -> None:
    choice = message.text.strip().lower()
    data = await state.get_data()
    if choice not in {"a", "b"}:
        await message.answer("Ответь A или B.")
        return
    winner = data["team_a"] if choice == "a" else data["team_b"]
    match = admin_service.add_match(
        tournament_id=data["tournament"]["id"],
        team_a_id=data["team_a"]["id"],
        team_b_id=data["team_b"]["id"],
        winner_team_id=winner["id"],
    )
    await state.update_data(match=match, winner_team=winner)

    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=MatchLineupCallback(decision="yes").pack())
    builder.button(text="Нет", callback_data=MatchLineupCallback(decision="no").pack())
    builder.adjust(2)

    await message.answer(
        f"Матч сохранён (ID {match['id']}). Добавить игроков и героев?",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(AddMatchState.confirm_lineups)


@router.callback_query(MatchLineupCallback.filter(), AddMatchState.confirm_lineups)
async def add_match_lineup_decision(
    callback: CallbackQuery,
    callback_data: MatchLineupCallback,
    state: FSMContext,
) -> None:
    if callback_data.decision == "yes":
        await state.set_state(AddMatchState.collecting_lineups)
        await callback.message.answer(
            "Отправляй строки вида: nickname, hero, kills, deaths, assists\n"
            "Например: Kairi, Lancelot, 5, 1, 7\n"
            "Когда закончишь, напиши 'готово'."
        )
    else:
        await callback.message.answer("Матч сохранён без статистики игроков.")
        await state.clear()
    await callback.answer()


@router.message(AddMatchState.collecting_lineups)
async def add_match_collect_lineups(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if text.lower() in {"готово", "done", "нет"}:
        await message.answer("Данные о матче сохранены.")
        await state.clear()
        return

    parts = [part.strip() for part in text.split(",")]
    if len(parts) < 5:
        await message.answer("Используй формат: nickname, hero, kills, deaths, assists")
        return

    nickname, hero_name, kills, deaths, assists = parts[:5]
    try:
        kills = int(kills)
        deaths = int(deaths)
        assists = int(assists)
    except ValueError:
        await message.answer("Kills/Deaths/Assists должны быть числами.")
        return

    data = await state.get_data()
    match = data.get("match")
    if not match:
        await message.answer("Нет активного матча. Начни заново.")
        await state.clear()
        return

    player = stats_service.get_player_by_nickname(nickname)
    if not player:
        await message.answer(f"Игрок {nickname} не найден в БД.")
        return

    if player["team_id"] not in {data["team_a"]["id"], data["team_b"]["id"]}:
        await message.answer("Этот игрок не относится к командам матча.")
        return

    hero_row = stats_service.get_hero_by_name(hero_name)
    if hero_row:
        hero = dict(hero_row)
    else:
        hero = admin_service.get_or_create_hero(hero_name)

    is_win = 1 if player["team_id"] == data["winner_team"]["id"] else 0
    admin_service.add_player_match_stat(
        match_id=match["id"],
        player_id=player["id"],
        hero_id=hero["id"],
        kills=kills,
        deaths=deaths,
        assists=assists,
        is_win=is_win,
    )
    await message.answer(
        f"Добавлено: {player['nickname']} на {hero['name']} "
        f"({kills}/{deaths}/{assists}) — {'WIN' if is_win else 'LOSS'}"
    )
