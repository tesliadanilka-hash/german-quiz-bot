from aiogram import Router, F
from aiogram.types import CallbackQuery

from config import ADMIN_ID
from keyboards.main import build_main_menu_keyboard
from services.access import has_access

router = Router()

@router.callback_query(F.data.in_({"back_main", "main_menu"}))
async def cb_back_main(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    text = "Главное меню. Выбери режим:"
    kb = build_main_menu_keyboard()
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
