from typing import Dict, Any, List
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from services.access import has_access
from services.grammar_repo import (
    load_grammar_rules,
    GRAMMAR_RULES,
    get_sublevels_for_level,
    get_rules_by_sublevel,
    get_rule_by_id,
    strip_html_tags,
)
from services.ai_client import generate_quiz_for_rule
from keyboards.grammar import (
    kb_grammar_levels,
    kb_grammar_sublevels,
    kb_grammar_rules_list,
    kb_rule_after_explanation,
    kb_quiz_answers,
    kb_after_quiz,
)

router = Router()

# user_id -> quiz state
USER_QUIZ_STATE: Dict[int, Dict[str, Any]] = {}

# rule_id -> cached questions
QUIZ_CACHE: Dict[str, List[Dict[str, Any]]] = {}

def get_quiz_instruction_ru() -> str:
    return (
        "📝 Задание: выбери один правильный вариант ответа, "
        "который грамматически подходит к этому предложению по текущему правилу."
    )

@router.message(Command("grammar"))
async def cmd_grammar(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return

    load_grammar_rules()
    if not GRAMMAR_RULES:
        await message.answer("Файл grammar.json не найден или в нем нет правил.")
        return

    await message.answer("Выбери уровень грамматики:", reply_markup=kb_grammar_levels())

@router.callback_query(F.data == "grammar_menu")
async def cb_grammar_menu(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    load_grammar_rules()
    if not GRAMMAR_RULES:
        await callback.answer("Правила не найдены.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("Выбери уровень грамматики:", reply_markup=kb_grammar_levels())

@router.callback_query(F.data.startswith("grammar_level:"))
async def cb_grammar_level(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, level = callback.data.split(":", 1)
    sublevels = get_sublevels_for_level(level)
    if not sublevels:
        await callback.answer("Для этого уровня пока нет правил.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(f"Выбери подуровень для {level}:", reply_markup=kb_grammar_sublevels(level))

@router.callback_query(F.data.startswith("grammar_sub:"))
async def cb_grammar_sub(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, sub = callback.data.split(":", 1)
    rules = get_rules_by_sublevel(sub)
    if not rules:
        await callback.answer("В этом подуровне пока нет правил.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(f"Правила для {sub}:", reply_markup=kb_grammar_rules_list(sub))

@router.callback_query(F.data.startswith("grammar_rule:"))
async def cb_grammar_rule(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id = callback.data.split(":", 1)
    rule = get_rule_by_id(rule_id)
    if not rule:
        await callback.answer("Правило не найдено.", show_alert=True)
        return

    title_clean = strip_html_tags(rule.get("title", "Правило"))
    expl_clean = strip_html_tags(rule.get("explanation", ""))

    text = f"*{title_clean}*\n\n{expl_clean}"
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=kb_rule_after_explanation(rule_id))

@router.callback_query(F.data == "grammar_back_rules")
async def cb_grammar_back_rules(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text("Выбери уровень грамматики:", reply_markup=kb_grammar_levels())

@router.callback_query(F.data.startswith("grammar_quiz_start:"))
async def cb_quiz_start(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id = callback.data.split(":", 1)
    rule = get_rule_by_id(rule_id)
    if not rule:
        await callback.answer("Правило не найдено.", show_alert=True)
        return

    await callback.answer()
    wait_msg = await callback.message.answer("⌛ Генерирую упражнения по этой теме, подожди немного...")

    questions = await generate_quiz_for_rule(rule, QUIZ_CACHE)
    if not questions:
        await wait_msg.edit_text("Не удалось создать упражнения для этой темы. Попробуй еще раз позже.")
        return

    USER_QUIZ_STATE[uid] = {
        "rule_id": rule_id,
        "questions": questions,
        "index": 0,
        "correct": 0,
        "wrong": 0,
    }

    await wait_msg.edit_text("Упражнения готовы. Начинаем первый вопрос.", parse_mode=None)
    await send_current_quiz_question(callback.message, uid, new_message=True)

async def send_current_quiz_question(message: Message, user_id: int, new_message: bool = False):
    state = USER_QUIZ_STATE.get(user_id)
    if not state:
        return

    idx = state["index"]
    questions = state["questions"]
    if idx >= len(questions):
        await send_quiz_result(message, user_id)
        return

    q = questions[idx]
    instr_ru = get_quiz_instruction_ru()

    text = (
        "📘 Грамматика: упражнение\n\n"
        f"Вопрос {idx + 1} из {len(questions)}\n\n"
        f"{instr_ru}\n\n"
        f"🇩🇪 {q['question']}"
    )

    kb = kb_quiz_answers(state["rule_id"], idx, q["options"])

    if new_message:
        await message.answer(text, reply_markup=kb, parse_mode=None)
    else:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode=None)
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode=None)

@router.callback_query(F.data.startswith("grammar_quiz_ans:"))
async def cb_quiz_answer(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id, q_index_str, opt_index_str = callback.data.split(":", 3)
    state = USER_QUIZ_STATE.get(uid)

    if not state or state["rule_id"] != rule_id:
        await callback.answer("Состояние викторины потеряно. Начни заново.", show_alert=True)
        return

    q_index = int(q_index_str)
    opt_index = int(opt_index_str)

    questions = state["questions"]
    if q_index != state["index"]:
        await callback.answer()
        return

    current = questions[q_index]
    correct = int(current.get("correct_index", 0))
    total_questions = len(questions)
    number = q_index + 1

    if opt_index == correct:
        state["correct"] += 1
        state["index"] += 1
        await callback.answer("Правильно ✅")

        if state["index"] >= len(questions):
            await send_quiz_result(callback.message, uid)
            return

        next_q = questions[state["index"]]
        instr_ru = get_quiz_instruction_ru()

        text = (
            "✅ Ответ правильный!\n\n"
            "📘 Грамматика: следующее упражнение\n\n"
            f"Вопрос {state['index'] + 1} из {total_questions}\n\n"
            f"{instr_ru}\n\n"
            f"🇩🇪 {next_q['question']}"
        )
        kb = kb_quiz_answers(rule_id, state["index"], next_q["options"])

        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode=None)
    else:
        state["wrong"] += 1
        await callback.answer("Неправильно. Попробуй еще раз.", show_alert=False)

        wrong_text = current["options"][opt_index]
        instr_ru = get_quiz_instruction_ru()

        text = (
            "❌ Это неверный ответ.\n\n"
            "📘 Грамматика: упражнение\n\n"
            f"Вопрос {number} из {total_questions}\n\n"
            f"{instr_ru}\n\n"
            f"🇩🇪 {current['question']}\n\n"
            f"Выбранный вариант: {wrong_text}\n"
            "Попробуй еще раз."
        )
        kb = kb_quiz_answers(rule_id, q_index, current["options"])

        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode=None)

async def send_quiz_result(message: Message, user_id: int):
    state = USER_QUIZ_STATE.get(user_id)
    if not state:
        return

    total = len(state["questions"])
    correct = state["correct"]
    wrong = state["wrong"]
    percent = round(correct / total * 100) if total else 0

    if percent == 100:
        comment = "Отлично! Ты владеешь этой темой на очень высоком уровне."
    elif percent >= 80:
        comment = "Очень хорошо! Есть пара мелочей, которые можно повторить."
    elif percent >= 50:
        comment = "Неплохо, но стоит еще потренироваться."
    else:
        comment = "Пока уровень слабый, лучше повторить правило и пройти упражнения еще раз."

    text = (
        "📊 Результат по грамматике\n\n"
        f"Правильных ответов: {correct} из {total} ({percent} %)\n"
        f"Неправильных попыток: {wrong}\n\n"
        f"{comment}"
    )

    await message.edit_text(text, reply_markup=kb_after_quiz(state["rule_id"]), parse_mode=None)
