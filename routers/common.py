from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.main import build_main_menu_keyboard

import services.access as access

router = Router()


def _has_access(uid: int) -> bool:
    fn = getattr(access, "has_access", None)
    if callable(fn):
        return fn(uid)

    # Fallback, если has_access еще не добавили в services/access.py
    allowed = getattr(access, "allowed_users", set())
    try:
        from config import ADMIN_ID
        return uid == int(ADMIN_ID) or uid in allowed
    except Exception:
        return uid in allowed


@router.callback_query(F.data.in_({"back_main", "main_menu"}))
async def cb_back_main(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if not _has_access(uid):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()

    text = "Главное меню. Выбери режим:"
    kb = build_main_menu_keyboard()

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
