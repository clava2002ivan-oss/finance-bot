from __future__ import annotations

import sqlite3
from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ..filters import AdminFilter
from ..services import admin_service, tournaments_service


router = Router(name="admin")
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


class AddTeamStates(StatesGroup):
    name = State()
    tag = State()
    region = State()


class AddPlayerStates(StatesGroup):
    nickname = State()
    team = State()
    role = State()


class AddMatchStates(StatesGroup):
    tournament = State()
    team_a = State()
    team_b = State()
    winner = State()
    stats_decision = State()
    stats_count = State()
    stats_entry = State()


class RoleSelectCallback(CallbackData, prefix="role_select"):
    role: str


class MatchWinnerCallback(CallbackData, prefix="match_winner"):
    team: str  # "A" or "B"


class MatchStatsDecisionCallback(CallbackData, prefix="match_stats"):
    action: str  # "yes" or "no"


def _format_team_preview():
    teams = admin_service.list_teams()
    if not teams:
        return "Команды пока не добавлены."
    preview = ", ".join(team["tag"] for team in teams[:10])
    if len(teams) > 10:
        preview += ", ..."
    return f"Доступные теги: {preview}"


@router.message(Command("add_team"))
async def add_team_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddTeamStates.name)
    await message.answer("Введите полное название команды:")


@router.message(AddTeamStates.name)
async def add_team_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddTeamStates.tag)
    await message.answer("Введите короткий тег команды (например, ONIC):")


@router.message(AddTeamStates.tag)
async def add_team_tag(message: Message, state: FSMContext):
    await state.update_data(tag=message.text.strip())
    await state.set_state(AddTeamStates.region)
    await message.answer("Введите регион (или '-' чтобы пропустить):")


@router.message(AddTeamStates.region)
async def add_team_region(message: Message, state: FSMContext):
    region = message.text.strip()
    if region == "-":
        region = None
    data = await state.get_data()
    try:
        team_id = admin_service.add_team(data["name"], data["tag"], region)
    except sqlite3.IntegrityError as exc:
        await message.answer(f"Не удалось добавить команду: {exc}. Проверь уникальность имени/тега.")
        return

    await message.answer(f"Команда добавлена (ID {team_id}).")
    await state.clear()


@router.message(Command("add_player"))
async def add_player_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddPlayerStates.nickname)
    await message.answer("Введите ник игрока:")


@router.message(AddPlayerStates.nickname)
async def add_player_nickname(message: Message, state: FSMContext):
    await state.update_data(nickname=message.text.strip())
    await state.set_state(AddPlayerStates.team)
    await message.answer(
        "Укажите команду (название или тег):\n" + _format_team_preview()
    )


@router.message(AddPlayerStates.team)
async def add_player_team(message: Message, state: FSMContext):
    team = admin_service.get_team_by_name_or_tag(message.text.strip())
    if not team:
        await message.answer("Команда не найдена. Попробуйте снова.")
        return
    await state.update_data(team_id=team["id"])
    await state.set_state(AddPlayerStates.role)

    builder = InlineKeyboardBuilder()
    for role in ("gold", "exp", "mid", "jungle", "roam"):
        builder.button(text=role.upper(), callback_data=RoleSelectCallback(role=role).pack())
    builder.adjust(2, 2, 1)
    await message.answer("Выберите роль игрока:", reply_markup=builder.as_markup())


@router.callback_query(AddPlayerStates.role, RoleSelectCallback.filter())
async def add_player_role_selected(
    callback: CallbackQuery, callback_data: RoleSelectCallback, state: FSMContext
):
    data = await state.get_data()
    if not data.get("team_id"):
        await callback.answer("Неизвестная команда. Начните заново.", show_alert=True)
        await state.clear()
        return

    try:
        player_id = admin_service.add_player(
            data["nickname"],
            data["team_id"],
            callback_data.role,
        )
    except sqlite3.IntegrityError as exc:
        await callback.answer("Ошибка сохранения.", show_alert=True)
        if callback.message:
            await callback.message.answer(f"Не удалось добавить игрока: {exc}")
    else:
        if callback.message:
            await callback.message.edit_reply_markup()
            await callback.message.answer(
                f"Игрок {data['nickname']} добавлен (ID {player_id})."
            )
        await callback.answer("Готово.")
        await state.clear()


@router.message(Command("add_match"))
async def add_match_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddMatchStates.tournament)
    await message.answer("Введите название турнира:")


@router.message(AddMatchStates.tournament)
async def add_match_tournament(message: Message, state: FSMContext):
    tournament_name = message.text.strip()
    tournament_id = tournaments_service.get_or_create_tournament(tournament_name)
    await state.update_data(
        tournament_id=tournament_id,
        tournament_name=tournament_name,
    )
    await state.set_state(AddMatchStates.team_a)
    await message.answer("Введите команду A (название или тег):")


def _resolve_team(value: str):
    team = admin_service.get_team_by_name_or_tag(value.strip())
    return team


@router.message(AddMatchStates.team_a)
async def add_match_team_a(message: Message, state: FSMContext):
    team = _resolve_team(message.text)
    if not team:
        await message.answer("Команда не найдена. Попробуйте снова.")
        return
    await state.update_data(team_a_id=team["id"], team_a_name=team["name"])
    await state.set_state(AddMatchStates.team_b)
    await message.answer("Введите команду B (название или тег):")


@router.message(AddMatchStates.team_b)
async def add_match_team_b(message: Message, state: FSMContext):
    team = _resolve_team(message.text)
    if not team:
        await message.answer("Команда не найдена. Попробуйте снова.")
        return

    data = await state.get_data()
    if team["id"] == data.get("team_a_id"):
        await message.answer("Команды не должны совпадать. Укажите другую команду.")
        return

    await state.update_data(team_b_id=team["id"], team_b_name=team["name"])
    await state.set_state(AddMatchStates.winner)

    builder = InlineKeyboardBuilder()
    builder.button(text=data["team_a_name"], callback_data=MatchWinnerCallback(team="A").pack())
    builder.button(text=team["name"], callback_data=MatchWinnerCallback(team="B").pack())
    builder.adjust(2)
    await message.answer("Кто победил?", reply_markup=builder.as_markup())


@router.callback_query(AddMatchStates.winner, MatchWinnerCallback.filter())
async def add_match_winner(
    callback: CallbackQuery, callback_data: MatchWinnerCallback, state: FSMContext
):
    data = await state.get_data()
    tournament_id = data.get("tournament_id")
    team_a_id = data.get("team_a_id")
    team_b_id = data.get("team_b_id")

    if not all([tournament_id, team_a_id, team_b_id]):
        await callback.answer("Не хватает данных. Начните заново.", show_alert=True)
        await state.clear()
        return

    winner_team_id = team_a_id if callback_data.team == "A" else team_b_id
    match_id = admin_service.add_match(
        tournament_id,
        team_a_id,
        team_b_id,
        winner_team_id,
    )
    await state.update_data(match_id=match_id, winner_team_id=winner_team_id)

    if callback.message:
        await callback.message.edit_reply_markup()
        await callback.message.answer(f"Матч сохранён (ID {match_id}).")

    builder = InlineKeyboardBuilder()
    builder.button(text="Да", callback_data=MatchStatsDecisionCallback(action="yes").pack())
    builder.button(text="Нет", callback_data=MatchStatsDecisionCallback(action="no").pack())
    builder.adjust(2)

    if callback.message:
        await callback.message.answer(
            "Добавить игроков и героев для матча?",
            reply_markup=builder.as_markup(),
        )
    await state.set_state(AddMatchStates.stats_decision)
    await callback.answer("Ок")


@router.callback_query(AddMatchStates.stats_decision, MatchStatsDecisionCallback.filter())
async def add_match_stats_decision(
    callback: CallbackQuery, callback_data: MatchStatsDecisionCallback, state: FSMContext
):
    if callback.message:
        await callback.message.edit_reply_markup()

    if callback_data.action == "no":
        await callback.answer("Матч сохранён без статистики.")
        await state.clear()
        return

    await state.set_state(AddMatchStates.stats_count)
    await callback.message.answer(
        "Сколько записей статистики добавить? Введите число (например, 10 для 2 команд по 5 игроков)."
    )
    await callback.answer()


@router.message(AddMatchStates.stats_count)
async def add_match_stats_count(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
    except ValueError:
        await message.answer("Введите целое число.")
        return

    if count <= 0:
        await message.answer("Число должно быть больше 0.")
        return

    await state.update_data(stats_remaining=count)
    await state.set_state(AddMatchStates.stats_entry)
    await message.answer(
        "Вводи данные по игроку в формате:\n"
        "<ник>,<герой>,<kills>,<deaths>,<assists>\n"
        "Например: Kairi,Lancelot,5,1,8"
    )


@router.message(AddMatchStates.stats_entry)
async def add_match_stats_entry(message: Message, state: FSMContext):
    parts = [part.strip() for part in message.text.split(",")]
    if len(parts) != 5:
        await message.answer("Используй формат: ник,герой,k,d,a")
        return

    nickname, hero_name, kills, deaths, assists = parts
    player = admin_service.get_player_by_nickname(nickname)
    if not player:
        await message.answer("Игрок не найден. Добавьте игрока перед вводом статистики.")
        return

    data = await state.get_data()
    if player["team_id"] not in (data.get("team_a_id"), data.get("team_b_id")):
        await message.answer("Этот игрок не относится к участвующим командам.")
        return

    hero = admin_service.get_hero_by_name(hero_name)
    if not hero:
        hero_id = admin_service.add_hero(hero_name)
    else:
        hero_id = hero["id"]

    try:
        kills_val = int(kills)
        deaths_val = int(deaths)
        assists_val = int(assists)
    except ValueError:
        await message.answer("K/D/A должны быть числами.")
        return

    is_win = 1 if player["team_id"] == data.get("winner_team_id") else 0
    admin_service.add_player_match_stat(
        data["match_id"],
        player["id"],
        hero_id,
        kills_val,
        deaths_val,
        assists_val,
        is_win,
    )

    remaining = data.get("stats_remaining", 0) - 1
    await state.update_data(stats_remaining=remaining)

    if remaining <= 0:
        await message.answer("Все записи добавлены. Спасибо!")
        await state.clear()
    else:
        await message.answer(f"Запись сохранена. Осталось {remaining}.")
