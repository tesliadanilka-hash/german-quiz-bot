from __future__ import annotations

import sys
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatAction


# -------------------------
# Надежный импорт ai_client.py
# -------------------------
def _import_check_text_with_ai():
    current_file = Path(__file__).resolve()
    src_dir = current_file.parent.parent          # .../src
    repo_root = src_dir.parent                    # .../project

    # добавим пути в sys.path, чтобы "import ai_client" заработал
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from ai_client import check_text_with_ai  # type: ignore
    return check_text_with_ai


check_text_with_ai = _import_check_text_with_ai()

# -------------------------

router = Router()

CHECK_MODE_USERS: set[int] = set()


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
