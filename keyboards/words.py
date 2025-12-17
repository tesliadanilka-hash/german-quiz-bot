from typing import List, Tuple, Dict
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.words_repo import (
    get_levels,
    get_topics_for_level,
    get_subtopics_for_level_topic,
    LEVEL_COUNTS,
    TOPIC_COUNTS,
    SUBTOPIC_COUNTS,
    TOPIC_ID_BY_KEY,
    SUBTOPIC_ID_BY_KEY,
    WORDS,
)

def build_themes_keyboard() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    total_words = len(WORDS)
    rows.append([InlineKeyboardButton(text=f"Все слова ({total_words})", callback_data="topic_all")])

    for level in get_levels():
        count = LEVEL_COUNTS.get(level, 0)
        rows.append([InlineKeyboardButton(text=f"Уровень {level} ({count})", callback_data=f"level|{level}")])

    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_topics_keyboard_for_level(level: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    for topic in get_topics_for_level(level):
        key = (level, topic)
        topic_id = TOPIC_ID_BY_KEY.get(key)
        if not topic_id:
            continue
        count = TOPIC_COUNTS.get(key, 0)
        rows.append([InlineKeyboardButton(text=f"{topic} ({count})", callback_data=f"topic_select|{topic_id}")])

    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_subtopics_keyboard(level: str, topic: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    for subtopic in get_subtopics_for_level_topic(level, topic):
        key = (level, topic, subtopic)
        sub_id = SUBTOPIC_ID_BY_KEY.get(key)
        if not sub_id:
            continue
        count = SUBTOPIC_COUNTS.get(key, 0)
        rows.append([InlineKeyboardButton(text=f"{subtopic} ({count})", callback_data=f"subtopic|{sub_id}")])

    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_full_format_keyboard(current_mode: str, current_answer: str) -> InlineKeyboardMarkup:
    de_selected = "✅ " if current_mode == "de_ru" else ""
    ru_selected = "✅ " if current_mode == "ru_de" else ""

    choice_mark = "✅ " if current_answer == "choice" else ""
    typing_mark = "✅ " if current_answer == "typing" else ""

    rows: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=f"{de_selected}🇩🇪 -> 🇷🇺 Немецкое слово", callback_data="mode|de_ru")],
        [InlineKeyboardButton(text=f"{ru_selected}🇷🇺 -> 🇩🇪 Русское слово", callback_data="mode|ru_de")],
        [InlineKeyboardButton(text=f"{choice_mark}Варианты ответа (4)", callback_data="answer_mode|choice")],
        [InlineKeyboardButton(text=f"{typing_mark}Ввод слова вручную", callback_data="answer_mode|typing")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
