from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str | None) -> List[int]:
    if not raw:
        return [123456789]
    ids: List[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.append(int(chunk))
        except ValueError:
            continue
    return ids or [123456789]


@dataclass(slots=True)
class Settings:
    bot_token: str
    openai_api_key: str | None
    openai_model: str
    db_path: str
    admin_ids: List[int]


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set. Please configure your .env file.")

    return Settings(
        bot_token=bot_token,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        db_path=os.getenv("DB_PATH", "sil.db"),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS")),
    )


settings = load_settings()
