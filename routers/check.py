from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from services.access import has_access
from services.state import user_state, save_user_state
from services.ai_client import check_text_with_ai

router = Router()


def _enable_check_mode(uid: int) -> None:
    st = user_state[uid]
    st["check_mode"] = True
    user_state[uid] = st
    save_user_state()


def _disable_check_mode(uid: int) -> None:
    st = user_state[uid]
    st["check_mode"] = False
    user_state[uid] = st
    save_user_state()


@router.message(Command("check"))
async def cmd_check_on(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return

    _enable_check_mode(uid)
    await message.answer(
        "Режим проверки предложений включен.\n\n"
        "Напиши предложение на немецком, и я предложу исправленный вариант и отмечу ошибки."
    )


@router.message(Command("checkoff"))
async def cmd_check_off(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return

    _disable_check_mode(uid)
    await message.answer("Режим проверки предложений выключен.")


@router.callback_query(F.data == "menu_check")
async def cb_menu_check(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _enable_check_mode(uid)
    await callback.answer()
    await callback.message.answer(
        "Режим проверки предложений включен.\n\n"
        "Напиши предложение на немецком, и я предложу исправленный вариант и отмечу ошибки.\n\n"
        "Чтобы выключить: /checkoff"
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_in_check_mode(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        return

    st = user_state[uid]
    if not st.get("check_mode", False):
        return

    text = (message.text or "").strip()
    if not text:
        return

    waiting = await message.answer("Проверяю...")
    result = await check_text_with_ai(text)

    try:
        await waiting.edit_text(result, parse_mode=None)
    except Exception:
        await message.answer(result, parse_mode=None)
