from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message


router = Router(name="base")

HELP_TEXT = (
    "Привет, я Sil — бот для киберспортивной статистики (MLBB).\n\n"
    "Доступные команды:\n"
    "• /player_stats <ник> — статистика игрока по турниру\n"
    "• /team_stats <команда> — статистика команды\n"
    "• /hero_stats <герой> — статистика героя\n\n"
    "Ввод матчей и редактирование данных доступны только администраторам."
)


@router.message(CommandStart())
async def handle_start(message: Message):
    await message.answer(HELP_TEXT)


@router.message(Command("help"))
async def handle_help(message: Message):
    await message.answer(HELP_TEXT)
