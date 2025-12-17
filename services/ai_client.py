import os
from typing import Optional

from openai import OpenAI

AI_SYSTEM_PROMPT = (
    "Ты преподаватель немецкого языка. "
    "Твоя задача проверить грамматику и правописание немецкого текста.\n"
    "Всегда отвечай строго в таком формате:\n\n"
    "Исправленный вариант:\n"
    "{исправленный текст целиком}\n\n"
    "Ошибки:\n"
    "1) {кратко: что было не так, где, как правильно}\n"
    "2) {если есть}\n\n"
    "Если ошибок нет, напиши:\n"
    "Исправленный вариант:\n"
    "{исходный текст}\n\n"
    "Ошибки:\n"
    "Ошибок не найдено. Предложение грамматически корректно."
)

_client: Optional[OpenAI] = None


def get_client() -> Optional[OpenAI]:
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    _client = OpenAI(api_key=api_key)
    return _client


async def check_text_with_ai(text: str) -> str:
    client = get_client()
    if client is None:
        return (
            "Проверка ИИ сейчас недоступна.\n"
            "Проверь переменную окружения OPENAI_API_KEY в Render."
        )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception:
        return "Произошла ошибка при проверке. Попробуй еще раз позже."
