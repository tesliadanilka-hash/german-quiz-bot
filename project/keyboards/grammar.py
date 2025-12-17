from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.grammar_repo import (
    get_sublevels_for_level,
    get_rules_by_sublevel,
)

def kb_grammar_levels() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="Правила уровня A1", callback_data="grammar_level:A1"),
            InlineKeyboardButton(text="Правила уровня A2", callback_data="grammar_level:A2"),
        ],
        [InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def kb_grammar_sublevels(level: str) -> InlineKeyboardMarkup:
    sublevels = get_sublevels_for_level(level)
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []

    for sub in sublevels:
        row.append(InlineKeyboardButton(text=sub, callback_data=f"grammar_sub:{sub}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅ Выбор уровня", callback_data="grammar_menu")])
    rows.append([InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_grammar_rules_list(sublevel: str) -> InlineKeyboardMarkup:
    rules = get_rules_by_sublevel(sublevel)
    rows: List[List[InlineKeyboardButton]] = []

    for r in rules:
        rows.append([InlineKeyboardButton(text=r.get("title", "Правило"), callback_data=f"grammar_rule:{r['id']}")])

    rows.append([InlineKeyboardButton(text="⬅ Подуровни", callback_data=f"grammar_level:{sublevel.split('.')[0]}")])
    rows.append([InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_rule_after_explanation(rule_id: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🧠 Практиковать упражнение по этой теме", callback_data=f"grammar_quiz_start:{rule_id}")],
        [InlineKeyboardButton(text="⬅ К списку правил", callback_data="grammar_back_rules")],
        [InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def kb_quiz_answers(rule_id: str, q_index: int, options: List[str]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i, opt in enumerate(options):
        rows.append([InlineKeyboardButton(text=opt, callback_data=f"grammar_quiz_ans:{rule_id}:{q_index}:{i}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_after_quiz(rule_id: str) -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔁 Практиковать еще раз", callback_data=f"grammar_quiz_start:{rule_id}")],
        [InlineKeyboardButton(text="📚 К выбору правил", callback_data="grammar_menu")],
        [InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
