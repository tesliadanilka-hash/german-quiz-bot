from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatAction

from ai_client import check_text_with_ai  # если файл ai_client.py в корне проекта


router = Router()

# Простой режим проверки в памяти процесса.
# На Render после перезапуска сбросится. Это нормально для старта.
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
        "Когда режим включен, просто отправляй немецкие предложения обычным текстом."
    )


@router.message(F.text)
async def check_text_handler(message: Message):
    # Не трогаем команды
    text = (message.text or "").strip()
    if not text or text.startswith("/"):
        return

    # Проверяем только если режим включен
    if message.from_user.id not in CHECK_MODE_USERS:
        return

    # Сразу показать, что бот работает
    try:
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    except Exception:
        pass

    wait_msg = await message.answer("⏳ Проверяю. Подожди немного...")

    result = await check_text_with_ai(text)

    # Лучше редактировать сообщение "подожди" на результат
    try:
        await wait_msg.edit_text(result)
    except Exception:
        await message.answer(result)
