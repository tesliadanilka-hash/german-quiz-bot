from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from services.access import has_access
from services.state import user_state, save_user_state
from services.ai_client import check_text_with_ai

router = Router()

@router.message(Command("check"))
async def cmd_check_on(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return

    user_state[uid]["check_mode"] = True
    save_user_state()
    await message.answer(
        "✏️ Режим проверки предложений включен.\n\n"
        "Напиши предложение на немецком, и я предложу исправленный вариант и отмечу ошибки."
    )

@router.message(Command("checkoff"))
async def cmd_check_off(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return

    user_state[uid]["check_mode"] = False
    save_user_state()
    await message.answer("Режим проверки предложений выключен. Можно вернуться к тренировке слов или грамматики.")

@router.callback_query(F.data == "menu_check")
async def cb_menu_check(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    user_state[uid]["check_mode"] = True
    save_user_state()
    await callback.answer()
    await callback.message.answer(
        "✏️ Режим проверки предложений включен.\n\n"
        "Напиши предложение на немецком, и я предложу исправленный вариант и отмечу ошибки."
    )

@router.message(F.text & ~F.text.startswith("/"))
async def handle_check_text(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        return

    if not user_state[uid].get("check_mode", False):
        return

    text = (message.text or "").strip()
    if not text:
        return

    waiting_msg = await message.answer("⌛ Проверяю предложение...")
    result = await check_text_with_ai(text)
    await waiting_msg.edit_text(result)
