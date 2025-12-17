from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from services.access import has_access, add_allowed_user
from keyboards.main import build_main_menu_keyboard


router = Router()


def _kb_request_access() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Запросить доступ", callback_data="req_access")]
        ]
    )


def _kb_allow_user(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разрешить доступ", callback_data=f"allow|{user_id}")]
        ]
    )


@router.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if has_access(uid, ADMIN_ID):
        await message.answer("У тебя уже есть доступ. Открой главное меню.")
        return

    text = (
        "Доступ к боту ограничен.\n\n"
        "Нажми кнопку ниже, чтобы отправить запрос администратору."
    )
    await message.answer(text, reply_markup=_kb_request_access())


@router.callback_query(F.data == "req_access")
async def cb_req_access(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if has_access(uid, ADMIN_ID):
        await callback.answer("Доступ уже есть.")
        return

    text_to_admin = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {callback.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await callback.bot.send_message(
            ADMIN_ID,
            text_to_admin,
            reply_markup=_kb_allow_user(uid),
        )
        await callback.answer("Запрос отправлен администратору.")
        await callback.message.answer("Запрос отправлен. Ожидай решение администратора.")
    except Exception:
        await callback.answer("Не удалось отправить запрос.", show_alert=True)


@router.callback_query(F.data.startswith("allow|"))
async def cb_allow(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return

    _, user_id_str = callback.data.split("|", maxsplit=1)

    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer("Некорректный ID.", show_alert=True)
        return

    add_allowed_user(user_id)

    await callback.answer("Доступ разрешен.")
    try:
        await callback.message.edit_text(f"✅ Доступ пользователю {user_id} разрешен.")
    except Exception:
        pass

    try:
        await callback.bot.send_message(
            user_id,
            "✅ Доступ одобрен.\n\nТеперь открой главное меню и выбирай режим.",
            reply_markup=build_main_menu_keyboard(),
        )
    except Exception:
        pass
