from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from keyboards.main import build_main_menu_keyboard
from services.access import allowed_users, save_allowed_users, has_access

router = Router()

@router.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if has_access(uid, ADMIN_ID):
        await message.answer("У тебя уже есть доступ к боту. Пользуйся главным меню ниже.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разрешить доступ", callback_data=f"allow|{uid}")]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {message.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await message.bot.send_message(ADMIN_ID, txt, reply_markup=kb)
        await message.answer("Запрос на доступ отправлен администратору.\nПосле одобрения ты получишь сообщение.")
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
            [InlineKeyboardButton(text="✅ Разрешить доступ", callback_data=f"allow|{uid}")]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {callback.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await callback.bot.send_message(ADMIN_ID, txt, reply_markup=kb)
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

    allowed_users.add(user_id)
    save_allowed_users()

    await callback.answer("Доступ разрешен.")
    await callback.message.edit_text(f"✅ Доступ пользователю {user_id} разрешен.")

    try:
        text = (
            "✅ Доступ к боту одобрен.\n\n"
            "Теперь ты можешь пользоваться всеми режимами через главное меню.\n\n"
            "Выбирай тренировки слов, грамматику, проверку предложений, формат ответа или статистику с помощью кнопок."
        )
        await callback.bot.send_message(user_id, text, reply_markup=build_main_menu_keyboard())
    except Exception:
        pass
