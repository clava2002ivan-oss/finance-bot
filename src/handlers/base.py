from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="base")


HELP_TEXT = (
    "Привет, я Sil — бот для киберспортивной статистики по MLBB.\n\n"
    "Доступные команды:\n"
    "• /player_stats <ник> — статистика игрока по турнирам\n"
    "• /team_stats <команда> — форма команды и её пул героев\n"
    "• /hero_stats <герой> — эффективность героя и топ игроков\n\n"
    "Ввод матчей и редактирование данных доступны только администраторам."
)


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("help"))
async def on_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
