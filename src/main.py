from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from .config import get_settings
from .db import initialize_db
from .handlers import admin, base, hero_stats, player_stats, team_stats


logging.basicConfig(level=logging.INFO)


async def main():
    settings = get_settings()
    initialize_db()

    bot = Bot(token=settings.bot_token, parse_mode="HTML")
    dp = Dispatcher()

    dp.include_router(base.router)
    dp.include_router(player_stats.router)
    dp.include_router(team_stats.router)
    dp.include_router(hero_stats.router)
    dp.include_router(admin.router)

    logging.info("Bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
