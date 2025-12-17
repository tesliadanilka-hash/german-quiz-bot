from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Тренировать слова", callback_data="menu_words")],
            [InlineKeyboardButton(text="📘 Грамматика", callback_data="grammar_menu")],
            [InlineKeyboardButton(text="✏️ Проверка предложений", callback_data="menu_check")],
            [InlineKeyboardButton(text="⚙️ Формат ответа", callback_data="menu_answer_mode")],
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="menu_stats")],
        ]
    )

def build_back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")]
        ]
    )
