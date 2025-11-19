from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from openai import AsyncOpenAI, OpenAIError

from .config import settings

client: AsyncOpenAI | None = None
if settings.openai_api_key:
    client = AsyncOpenAI(api_key=settings.openai_api_key)


def _fallback_response(title: str, data: Dict[str, Any]) -> str:
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    return f"[offline AI] {title}\n{pretty}"


async def _complete(prompt: str, title: str, payload: Dict[str, Any]) -> str:
    if client is None:
        return _fallback_response(title, payload)
    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": "Ты — аналитик по киберспортивной дисциплине Mobile Legends: Bang Bang. "
                    "Отвечай кратко, структурированно и по делу.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except (OpenAIError, asyncio.TimeoutError) as exc:
        return f"Не удалось получить ответ от ИИ: {exc}\n\n" + _fallback_response(title, payload)


async def generate_player_report(payload: Dict[str, Any]) -> str:
    prompt = (
        "Ты — аналитик по киберспортивной дисциплине MLBB.\n"
        "Используй данные JSON ниже и сформируй краткий анализ игрока:\n"
        "– количество игр, побед, винрейт;\n"
        "– KDA и средние K/D/A;\n"
        "– ключевые герои и их винрейт;\n"
        "– 1–2 предложения о текущей форме.\n"
        "Используй только предоставленные числа.\n"
        f"Данные: {json.dumps(payload, ensure_ascii=False)}"
    )
    return await _complete(prompt, "Player report", payload)


async def generate_team_report(payload: Dict[str, Any]) -> str:
    prompt = (
        "Ты анализируешь форму команды в MLBB. На основе данных JSON опиши:\n"
        "– общий винрейт и количество матчей;\n"
        "– средние командные K/D/A;\n"
        "– характер игры, сильные стороны;\n"
        "– ключевых героев с винрейтом.\n"
        f"Данные: {json.dumps(payload, ensure_ascii=False)}"
    )
    return await _complete(prompt, "Team report", payload)


async def generate_hero_report(payload: Dict[str, Any]) -> str:
    prompt = (
        "Проанализируй героя MLBB по данным JSON:\n"
        "– винрейт и количество игр;\n"
        "– популярность (использование, баны);\n"
        "– топ игроков на герое;\n"
        "– краткий вывод о метовом статусе.\n"
        f"Данные: {json.dumps(payload, ensure_ascii=False)}"
    )
    return await _complete(prompt, "Hero report", payload)
