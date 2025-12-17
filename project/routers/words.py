import random
from typing import List
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID
from keyboards.main import build_main_menu_keyboard
from keyboards.words import (
    build_themes_keyboard,
    build_topics_keyboard_for_level,
    build_subtopics_keyboard,
    build_full_format_keyboard,
)
from services.access import has_access
from services.state import user_state, save_user_state, TOPIC_ALL
from services.words_repo import (
    WORDS,
    WORDS_BY_TOPIC,
    TOPIC_KEY_BY_ID,
    SUBTOPIC_KEY_BY_ID,
    LEVEL_COUNTS,
    TOPIC_COUNTS,
    pretty_topic_name,
)

router = Router()

def get_user_words(uid: int) -> List[int]:
    state = user_state[uid]
    topic = state["topic"]
    if topic not in WORDS_BY_TOPIC or topic == TOPIC_ALL:
        return WORDS_BY_TOPIC.get(TOPIC_ALL, [])
    return WORDS_BY_TOPIC[topic]

def reset_progress(uid: int) -> None:
    state = user_state[uid]
    state["correct"] = 0
    state["wrong"] = 0
    state["waiting_text_answer"] = False
    state["current_word_id"] = None

    ids = get_user_words(uid).copy()
    random.shuffle(ids)
    state["remaining"] = ids
    save_user_state()

def build_options(word_ids: List[int], correct_id: int, mode: str) -> InlineKeyboardMarkup:
    pool = set(word_ids)
    pool.discard(correct_id)
    wrong_ids = random.sample(list(pool), k=3) if len(pool) >= 3 else list(pool)

    all_ids = wrong_ids + [correct_id]
    random.shuffle(all_ids)

    buttons = []
    for wid in all_ids:
        w = WORDS[wid]
        text = w["ru"] if mode == "de_ru" else f'{w["de"]} ({w["tr"]})'
        cb_data = f"ans|{correct_id}|{mode}|{1 if wid == correct_id else 0}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=cb_data)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_new_word(user_id: int, chat_id: int, bot) -> None:
    state = user_state[user_id]
    if state["remaining"] is None:
        reset_progress(user_id)

    if not state["remaining"]:
        await bot.send_message(
            chat_id,
            "В этой подборке пока нет слов или ты уже прошел все слова.\n"
            "Выбери уровень и тему через Тренировку слов.",
        )
        return

    word_id = state["remaining"].pop()
    w = WORDS[word_id]
    answer_mode = state.get("answer_mode", "choice")
    mode = state["mode"]
    word_pool = get_user_words(user_id)

    if answer_mode == "choice":
        if mode == "de_ru":
            text = f'🇩🇪 Слово: {w["de"]} ({w["tr"]})\nВыбери правильный перевод на русский.'
        else:
            text = f'🇷🇺 Слово: {w["ru"]}\nВыбери правильный перевод на немецкий.'
        kb = build_options(word_pool, word_id, mode)
        await bot.send_message(chat_id, text, reply_markup=kb)
    else:
        text = (
            f'🇷🇺 Слово: {w["ru"]}\n\n'
            "Напиши это слово по немецки, только само немецкое слово, без транскрипции и без скобок."
        )
        state["current_word_id"] = word_id
        state["waiting_text_answer"] = True
        save_user_state()
        await bot.send_message(chat_id, text)

async def resend_same_word(chat_id: int, word_id: int, mode: str, uid: int, bot) -> None:
    w = WORDS[word_id]
    word_pool = get_user_words(uid)

    if mode == "de_ru":
        text = (
            "❌ Неправильно.\n"
            "Попробуй еще раз.\n\n"
            f'🇩🇪 Слово: {w["de"]} ({w["tr"]})\nВыбери правильный перевод на русский.'
        )
    else:
        text = (
            "❌ Неправильно.\n"
            "Попробуй еще раз.\n\n"
            f'🇷🇺 Слово: {w["ru"]}\nВыбери правильный перевод на немецкий.'
        )
    kb = build_options(word_pool, word_id, mode)
    await bot.send_message(chat_id, text, reply_markup=kb)

@router.message(Command("next"))
async def cmd_next(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return

    state = user_state[uid]
    if state["remaining"] is not None and not state["remaining"]:
        reset_progress(uid)

    await send_new_word(uid, message.chat.id, message.bot)

@router.message(F.text & ~F.text.startswith("/"))
async def handle_typing_answer(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        return

    state = user_state[uid]

    # Если включен режим проверки, этим займется router check.py (он тоже ловит текст),
    # поэтому тут просто выходим, чтобы не мешать.
    if state.get("check_mode", False):
        return

    if state.get("answer_mode") != "typing" or not state.get("waiting_text_answer"):
        return

    text = (message.text or "").strip()
    if not text:
        return

    word_id = state.get("current_word_id")
    if word_id is None or word_id < 0 or word_id >= len(WORDS):
        state["waiting_text_answer"] = False
        state["current_word_id"] = None
        save_user_state()
        await message.answer("Что то пошло не так. Попробуй запросить новое слово.")
        return

    w = WORDS[word_id]
    user_answer = text.lower().strip()
    correct_answer = w["de"].lower().strip()

    if user_answer == correct_answer:
        state["correct"] += 1
        reply = "✅ Правильно.\n\n" + f'{w["de"]} ({w["tr"]}) - {w["ru"]}'
    else:
        state["wrong"] += 1
        reply = (
            "❌ Неправильно.\n\n"
            "Правильный ответ:\n"
            f'{w["de"]} ({w["tr"]}) - {w["ru"]}\n\n'
            "Пиши только немецкое слово, без транскрипции."
        )

    state["waiting_text_answer"] = False
    state["current_word_id"] = None
    save_user_state()

    await message.answer(reply)
    await send_new_word(uid, message.chat.id, message.bot)

@router.callback_query(F.data == "menu_words")
async def cb_menu_words(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "Выбери уровень, затем тему и подтему. В скобках показано количество слов.",
        reply_markup=build_themes_keyboard(),
    )

@router.callback_query(F.data == "topic_all")
async def cb_topic_all(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    user_state[uid]["topic"] = TOPIC_ALL
    reset_progress(uid)

    count = len(WORDS_BY_TOPIC.get(TOPIC_ALL, []))
    await callback.answer("Режим обновлен.")
    text = (
        "🔁 Ты выбрал режим: все слова.\n\n"
        f"Всего слов в базе: {count}.\n\n"
        "Буду давать слова из всех уровней, тем и подтем."
    )
    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)

    await send_new_word(uid, callback.message.chat.id, callback.bot)

@router.callback_query(F.data.startswith("level|"))
async def cb_level(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, level = callback.data.split("|", maxsplit=1)
    if level not in LEVEL_COUNTS:
        await callback.answer("Для этого уровня пока нет слов.", show_alert=True)
        return

    await callback.answer()
    kb = build_topics_keyboard_for_level(level)
    text = (
        f"Ты выбрал уровень {level}.\n\n"
        "Теперь выбери тему. В скобках указано, сколько слов во всех подтемах этой темы."
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("topic_select|"))
async def cb_topic_select(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, topic_id = callback.data.split("|", maxsplit=1)
    if topic_id not in TOPIC_KEY_BY_ID:
        await callback.answer("Тема не найдена.", show_alert=True)
        return

    level, topic = TOPIC_KEY_BY_ID[topic_id]
    await callback.answer()

    kb = build_subtopics_keyboard(level, topic)
    total_in_topic = TOPIC_COUNTS.get((level, topic), 0)

    text = (
        f"Уровень: {level}\n"
        f"Тема: {topic}\n"
        f"Всего слов в этой теме: {total_in_topic}\n\n"
        "Теперь выбери подтему. В скобках указано количество слов в каждой подтеме."
    )
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("subtopic|"))
async def cb_subtopic(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, sub_id = callback.data.split("|", maxsplit=1)
    if sub_id not in SUBTOPIC_KEY_BY_ID:
        await callback.answer("Подтема не найдена.", show_alert=True)
        return

    level, topic, subtopic = SUBTOPIC_KEY_BY_ID[sub_id]
    topic_key = f"{level}|{topic}|{subtopic}"

    user_state[uid]["topic"] = topic_key
    reset_progress(uid)

    count = len(WORDS_BY_TOPIC.get(topic_key, []))
    await callback.answer("Тема выбрана.")

    text = (
        f"Уровень: {level}\n"
        f"Тема: {topic}\n"
        f"Подтема: {subtopic}\n"
        f"Слов в этой подтеме: {count}\n\n"
        "Теперь я буду давать слова только из этой подтемы."
    )
    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)

    await send_new_word(uid, callback.message.chat.id, callback.bot)

@router.callback_query(F.data == "menu_answer_mode")
async def cb_menu_answer_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    state = user_state[uid]
    kb = build_full_format_keyboard(state.get("mode", "de_ru"), state.get("answer_mode", "choice"))
    text = (
        "⚙️ Формат ответа.\n\n"
        "1) Направление перевода:\n"
        "   • 🇩🇪 -> 🇷🇺 Немецкое слово -> выбираешь перевод на русский\n"
        "   • 🇷🇺 -> 🇩🇪 Русское слово -> выбираешь или вводишь вариант на немецком\n\n"
        "2) Формат ответа:\n"
        "   • Варианты ответа (4) - как тест\n"
        "   • Ввод слова вручную - ты пишешь немецкое слово сам"
    )
    await callback.message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("mode|"))
async def cb_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, mode = callback.data.split("|", maxsplit=1)
    if mode not in ("de_ru", "ru_de"):
        await callback.answer("Неизвестное направление.", show_alert=True)
        return

    user_state[uid]["mode"] = mode
    save_user_state()

    state = user_state[uid]
    kb = build_full_format_keyboard(state.get("mode", "de_ru"), state.get("answer_mode", "choice"))

    txt = "Теперь я буду показывать немецкое слово, а ты отвечаешь по русски." if mode == "de_ru" else \
          "Теперь я буду показывать русское слово, а ты отвечаешь по немецки."

    await callback.answer("Направление перевода обновлено.")
    try:
        await callback.message.edit_text(txt, reply_markup=kb)
    except Exception:
        await callback.message.answer(txt, reply_markup=kb)

@router.callback_query(F.data.startswith("answer_mode|"))
async def cb_answer_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, mode = callback.data.split("|", maxsplit=1)
    if mode not in ("choice", "typing"):
        await callback.answer("Неизвестный формат ответа.", show_alert=True)
        return

    state = user_state[uid]
    state["answer_mode"] = mode
    state["waiting_text_answer"] = False
    state["current_word_id"] = None
    save_user_state()

    kb = build_full_format_keyboard(state.get("mode", "de_ru"), state.get("answer_mode", "choice"))
    text = (
        "Теперь формат ответа: варианты.\n\nПо каждому слову будет 4 варианта ответа на кнопках."
        if mode == "choice"
        else
        "Теперь формат ответа: ввод слова вручную.\n\nЯ показываю русское слово, а ты пишешь его по немецки."
    )

    await callback.answer("Формат ответа обновлен.")
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("ans|"))
async def cb_answer(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return

    state = user_state[uid]
    _, word_id_str, mode, is_correct_str = callback.data.split("|")

    word_id = int(word_id_str)
    is_correct = is_correct_str == "1"
    w = WORDS[word_id]

    await callback.answer()

    if is_correct:
        state["correct"] += 1
        save_user_state()

        text = (
            "✅ Правильно.\n\n" + (f'{w["de"]} ({w["tr"]}) - {w["ru"]}' if mode == "de_ru" else f'{w["ru"]} - {w["de"]} ({w["tr"]})')
        )

        finished_now = not state["remaining"]
        if finished_now:
            # Сохранение статистики по кругу делает router stats.py (там общий текст),
            # но тут оставим прежнее поведение.
            text += (
                "\n\nТы прошел все слова в этой подборке.\n"
                f"✅ Правильных ответов: {state['correct']}\n"
                f"❌ Неправильных ответов: {state['wrong']}\n\n"
                "Можно выбрать другую подтему в Тренировке слов или начать новую тренировку."
            )

        try:
            await callback.message.edit_text(text)
        except Exception:
            await callback.message.answer(text)

        if not finished_now:
            await send_new_word(uid, callback.message.chat.id, callback.bot)
    else:
        state["wrong"] += 1
        save_user_state()
        try:
            await callback.message.edit_text("❌ Неправильно. Сейчас повторим это слово.")
        except Exception:
            await callback.message.answer("❌ Неправильно. Сейчас повторим это слово.")
        await resend_same_word(callback.message.chat.id, word_id, mode, uid, callback.bot)
