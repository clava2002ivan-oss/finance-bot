from __future__ import annotations

from typing import Sequence

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from .config import get_settings


class AdminFilter(BaseFilter):
    def __init__(self, admin_ids: Sequence[int] | None = None):
        settings = get_settings()
        self.admin_ids = list(admin_ids) if admin_ids is not None else settings.admin_ids

    async def __call__(self, event: TelegramObject) -> bool:
        user_id = None
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            user_id = event.from_user.id
        return bool(user_id and user_id in self.admin_ids)
