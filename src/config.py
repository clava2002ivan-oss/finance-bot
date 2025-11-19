from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
from typing import List
import os

from dotenv import load_dotenv


load_dotenv()


DEFAULT_ADMIN_IDS = [123456789]


@dataclass(slots=True)
class Settings:
    bot_token: str
    openai_api_key: str
    openai_model: str
    db_path: Path
    admin_ids: List[int]


def _parse_admin_ids(raw: str | None) -> List[int]:
    if not raw:
        return DEFAULT_ADMIN_IDS
    values: List[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            values.append(int(chunk))
        except ValueError:
            continue
    return values or DEFAULT_ADMIN_IDS


@lru_cache
def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    db_path = Path(os.getenv("DB_PATH", "sil.db")).expanduser().resolve()
    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS"))

    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not configured. Please set it in your .env file.")

    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured. Please set it in your .env file.")

    return Settings(
        bot_token=bot_token,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        db_path=db_path,
        admin_ids=admin_ids,
    )
