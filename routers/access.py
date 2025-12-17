from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import F

from config import ADMIN_ID
from services.access import has_access, add_allowed_user


router = Router()


@router.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if has_access(uid, ADMIN_ID):
        await message.answer("У тебя уже есть доступ к боту.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Разрешить доступ",
                    callback_data=f"allow|{uid}",
                )
            ]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {message.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await message.bot.send_message(ADMIN_ID, txt, reply_markup=kb)
        await message.answer("Запрос на доступ отправлен администратору.")
    except Exception:
        await message.answer("Не получилось отправить запрос администратору. Попробуй позже.")


@router.callback_query(F.data == "req_access")
async def cb_req_access(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if has_access(uid, ADMIN_ID):
        await callback.answer("Доступ уже есть.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Разрешить доступ",
                    callback_data=f"allow|{uid}",
                )
            ]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {callback.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await callback.message.bot.send_message(ADMIN_ID, txt, reply_markup=kb)
        await callback.answer("Запрос отправлен администратору.")
        await callback.message.answer("Запрос на доступ отправлен. Ожидай решение администратора.")
    except Exception:
        await callback.answer("Ошибка отправки запроса.", show_alert=True)


@router.callback_query(F.data.startswith("allow|"))
async def cb_allow_user(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return

    _, user_id_str = callback.data.split("|", maxsplit=1)
    user_id = int(user_id_str)

    add_allowed_user(user_id)

    await callback.answer("Доступ разрешен.")
    try:
        await callback.message.edit_text(f"✅ Доступ пользователю {user_id} разрешен.")
    except Exception:
        await callback.message.answer(f"✅ Доступ пользователю {user_id} разрешен.")

    try:
        await callback.message.bot.send_message(
            user_id,
            "✅ Доступ к боту одобрен.\n\nНапиши /start чтобы открыть меню."
        )
    except Exception:
        pass
