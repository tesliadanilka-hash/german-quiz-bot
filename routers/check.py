import os
import asyncio
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatAction

from openai import OpenAI


router = Router()

CHECK_MODE_USERS: set[int] = set()

_client: Optional[OpenAI] = None
_LOGGED_ONCE = False

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


def get_client() -> Optional[OpenAI]:
    global _client, _LOGGED_ONCE

    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")

    if not _LOGGED_ONCE:
        print("AI_CHECK: checking OPENAI_API_KEY")
        print(f"AI_CHECK: key exists = {bool(api_key)}")
        _LOGGED_ONCE = True

    if not api_key:
        print("AI_CHECK: OPENAI_API_KEY NOT FOUND")
        return None

    try:
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
        print("AI_CHECK: OpenAI client initialized")
        return _client
    except Exception as e:
        print(f"AI_CHECK: failed to init client: {e}")
        _client = None
        return None


def _chat_completion_sync(text: str) -> str:
    client = get_client()
    if client is None:
        return ""

    model = os.getenv("OPENAI_MODEL_GRAMMAR", "gpt-4.1-mini")

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": AI_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    return (completion.choices[0].message.content or "").strip()


async def check_text_with_ai(text: str) -> str:
    client = get_client()
    if client is None:
        return (
            "Проверка ИИ сейчас недоступна.\n"
            "Проверь переменную окружения OPENAI_API_KEY в Render."
        )

    text = (text or "").strip()
    if not text:
        return "Пустой текст. Напиши предложение на немецком."

    try:
        # В отдельном потоке, чтобы не блокировать aiogram
        result = await asyncio.to_thread(_chat_completion_sync, text)
        if not result:
            return "Не удалось получить ответ ИИ. Попробуй еще раз."
        return result
    except Exception as e:
        print(f"AI_CHECK: check_text_with_ai error: {e}")
        return "Произошла ошибка при проверке. Попробуй еще раз позже."


@router.message(Command("check_on"))
async def check_on(message: Message):
    CHECK_MODE_USERS.add(message.from_user.id)
    await message.answer(
        "Режим проверки предложений включен.\n"
        "Напиши предложение на немецком, и я проверю его через ИИ."
    )


@router.message(Command("check_off"))
async def check_off(message: Message):
    CHECK_MODE_USERS.discard(message.from_user.id)
    await message.answer("Режим проверки предложений выключен.")


@router.message(Command("check"))
async def check_help(message: Message):
    await message.answer(
        "Команды проверки:\n"
        "/check_on включить проверку\n"
        "/check_off выключить проверку\n\n"
        "Когда режим включен, просто отправляй немецкие предложения текстом."
    )


@router.message(F.text)
async def check_text_handler(message: Message):
    text = (message.text or "").strip()

    if not text:
        return

    if text.startswith("/"):
        return

    if message.from_user.id not in CHECK_MODE_USERS:
        return

    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    except Exception:
        pass

    wait_msg = await message.answer("⏳ Проверяю. Подожди немного...")

    result = await check_text_with_ai(text)

    try:
        await wait_msg.edit_text(result)
    except Exception:
        await message.answer(result)
