from __future__ import annotations

from typing import Any, Dict, List

from openai import OpenAI

from .config import get_settings


settings = get_settings()
_client = OpenAI(api_key=settings.openai_api_key)


def _run_chat(messages: List[Dict[str, str]], *, temperature: float = 0.3) -> str:
    try:
        response = _client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:  # pragma: no cover - fallback path
        return f"⚠️ Не удалось получить ответ от ИИ ({exc}). Попробуй позже."


def generate_player_analysis(payload: Dict[str, Any]) -> str:
    prompt = (
        "Ты — аналитик по киберспортивной дисциплине MLBB. "
        "Ниже переданы расчётные данные по игроку за конкретный турнир. "
        "Сформируй структурированный разбор: количество игр/побед/WR, KDA и средние K/D/A, "
        "ключевые герои с их винрейтом и 1–2 предложения об общей форме. "
        "Используй только переданные цифры, ничего не придумывай."
    )
    data_block = f"Данные: {payload}"
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": data_block},
    ]
    return _run_chat(messages)


def generate_team_analysis(payload: Dict[str, Any]) -> str:
    prompt = (
        "Ты — аналитик MLBB. На основе данных расскажи о форме команды: "
        "общий винрейт, средние K/D/A, стиль (агрессивный, сбалансированный и т.д.), "
        "ключевые герои с их винрейтом и возможные сильные или слабые стороны."
    )
    data_block = f"Данные: {payload}"
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": data_block},
    ]
    return _run_chat(messages)


def generate_hero_analysis(payload: Dict[str, Any]) -> str:
    prompt = (
        "Ты — аналитик меты MLBB. Проанализируй героя: общий WR, частоту использования, "
        "лучших игроков на нём и (если есть) популярность в банах. "
        "Сделай выводы о том, насколько герой метовый и кому подходит."
    )
    data_block = f"Данные: {payload}"
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": data_block},
    ]
    return _run_chat(messages)
