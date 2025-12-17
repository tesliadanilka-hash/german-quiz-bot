from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from keyboards.main import build_main_menu_keyboard
from services.access import has_access
from services.state import user_state, save_user_state
from services.words_repo import WORDS, TOPIC_COUNTS, SUBTOPIC_COUNTS

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id

    if not has_access(uid, ADMIN_ID):
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔓 Запросить доступ", callback_data="req_access")]
            ]
        )
        text = (
            "🎓 Willkommen. Добро пожаловать в закрытого бота по немецкому языку.\n\n"
            "Этот бот помогает улучшать немецкий язык через слова, темы, грамматику и проверку предложений.\n\n"
            "Доступ ограничен. Нажми кнопку ниже, чтобы отправить запрос администратору."
        )
        await message.answer(text, reply_markup=kb)
        return

    total_words = len(WORDS)
    total_topics = len(TOPIC_COUNTS)
    total_subtopics = len(SUBTOPIC_COUNTS)

    text = (
        "🎓 Willkommen. Добро пожаловать в бота по немецкому языку.\n\n"
        "Здесь ты можешь:\n"
        "• Тренировать слова по уровням, темам и подтемам\n"
        "• Разбирать грамматику\n"
        "• Проверять свои предложения\n"
        "• Смотреть статистику по темам\n\n"
        f"Сейчас в базе {total_words} слов.\n"
        f"Тем: {total_topics}, подтем: {total_subtopics}.\n\n"
        "Используй главное меню ниже, чтобы выбрать режим."
    )
    await message.answer(text, reply_markup=build_main_menu_keyboard())

    user_state[uid]["check_mode"] = False
    save_user_state()
