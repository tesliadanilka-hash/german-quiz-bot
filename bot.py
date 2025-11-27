import asyncio
import json
import logging
import os
import random
from typing import Dict, Any, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ======================================
#  НАСТРОЙКИ
# ======================================

TOKEN = os.getenv("BOT_TOKEN", "ТОКЕН_СЮДА")  # на Render лучше задать BOT_TOKEN в env

logging.basicConfig(level=logging.INFO)

# ======================================
#  ЗАГРУЗКА СЛОВ
# ======================================

WORDS: List[Dict[str, Any]] = []          # все слова
TOPICS: List[str] = []                   # список тем

def load_words() -> None:
    global WORDS, TOPICS
    with open("words.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # гарантируем поле "topic"
    for w in data:
        if "topic" not in w or not w["topic"]:
            w["topic"] = "Общее"

    WORDS = data
    TOPICS = sorted({w["topic"] for w in WORDS})


load_words()

# ======================================
#  СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ======================================

# mode: "de_ru", "ru_de", "mixed"
# topic: str | None
# last_question_id: int (для защиты от старых нажатий)
USER_STATE: Dict[int, Dict[str, Any]] = {}

def get_state(chat_id: int) -> Dict[str, Any]:
    if chat_id not in USER_STATE:
        USER_STATE[chat_id] = {
            "mode": "de_ru",
            "topic": None,
            "last_question_id": 0,
        }
    return USER_STATE[chat_id]

# ======================================
#  КЛАВИАТУРЫ
# ======================================

def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="🇩🇪 Немецкий → Русский")],
            [KeyboardButton(text="🇷🇺 Русский → Немецкий")],
            [KeyboardButton(text="🎲 Смешанный режим")],
            [KeyboardButton(text="📚 Выбрать тему")],
            [KeyboardButton(text="▶️ Начать квиз")],
        ],
    )


def topics_kb() -> InlineKeyboardMarkup:
    # отправляем темы как inline-кнопки (по индексам)
    rows = []
    for idx, topic in enumerate(TOPICS):
        rows.append(
            [InlineKeyboardButton(text=topic, callback_data=f"topic:{idx}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def answers_kb(options: List[str], correct_index: int, question_id: int) -> InlineKeyboardMarkup:
    # callback_data: ans:<question_id>:<chosen>:<correct>
    rows = []
    for i, opt in enumerate(options):
        cb = f"ans:{question_id}:{i}:{correct_index}"
        rows.append([InlineKeyboardButton(text=opt, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ======================================
#  ЛОГИКА ВЫБОРА СЛОВА
# ======================================

def choose_word_for_user(chat_id: int) -> (Dict[str, Any], str):
    """
    Возвращает (слово, направление).
    Направление: "de_ru" или "ru_de".
    В режиме mixed – направление выбирается случайно.
    """
    state = get_state(chat_id)
    mode = state["mode"]
    topic = state["topic"]

    # фильтрация по теме
    if topic is None:
        words_pool = WORDS
    else:
        words_pool = [w for w in WORDS if w["topic"] == topic]

    if not words_pool:
        # если в теме нет слов, берём все
        words_pool = WORDS

    word = random.choice(words_pool)

    if mode == "mixed":
        direction = random.choice(["de_ru", "ru_de"])
    else:
        direction = mode

    return word, direction


def build_question(chat_id: int) -> Dict[str, Any]:
    """
    Формирует вопрос для пользователя:
    {
        "text": str,
        "options": [str, str, str, str],
        "correct_index": int,
        "direction": "de_ru" | "ru_de",
        "word": {...}
    }
    """
    word, direction = choose_word_for_user(chat_id)

    # правильный ответ
    if direction == "de_ru":
        correct = word["ru"]
        question_text = f"🇩🇪 → 🇷🇺\n\nСлово: *{word['de']}* [{word.get('tr', '')}]"
        # берём другие переводы
        pool = [w for w in WORDS if w["ru"] != correct]
        wrongs = random.sample(pool, k=3) if len(pool) >= 3 else random.choices(pool, k=3)
        options = [correct] + [w["ru"] for w in wrongs]
    else:
        correct = word["de"]
        question_text = f"🇷🇺 → 🇩🇪\n\nСлово: *{word['ru']}*"
        pool = [w for w in WORDS if w["de"] != correct]
        wrongs = random.sample(pool, k=3) if len(pool) >= 3 else random.choices(pool, k=3)
        options = [correct] + [w["de"] for w in wrongs]

    random.shuffle(options)
    correct_index = options.index(correct)

    return {
        "text": question_text,
        "options": options,
        "correct_index": correct_index,
        "direction": direction,
        "word": word,
    }

# ======================================
#  ОБРАБОТЧИКИ
# ======================================

async def cmd_start(message: Message):
    state = get_state(message.chat.id)
    state["mode"] = "de_ru"
    state["topic"] = None

    await message.answer(
        "Привет! 👋\n"
        "Я бот для тренировки немецких слов.\n\n"
        "Выбери режим или просто нажми «▶️ Начать квиз».",
        reply_markup=main_menu_kb(),
    )


async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start – главное меню\n"
        "/help – помощь\n\n"
        "Кнопки внизу:\n"
        "🇩🇪 Немецкий → Русский\n"
        "🇷🇺 Русский → Немецкий\n"
        "🎲 Смешанный режим\n"
        "📚 Выбрать тему\n"
        "▶️ Начать квиз",
        reply_markup=main_menu_kb(),
    )


async def set_mode_de_ru(message: Message):
    state = get_state(message.chat.id)
    state["mode"] = "de_ru"
    await message.answer("Режим: 🇩🇪 Немецкий → Русский.\nНажми «▶️ Начать квиз».", reply_markup=main_menu_kb())


async def set_mode_ru_de(message: Message):
    state = get_state(message.chat.id)
    state["mode"] = "ru_de"
    await message.answer("Режим: 🇷🇺 Русский → Немецкий.\nНажми «▶️ Начать квиз».", reply_markup=main_menu_kb())


async def set_mode_mixed(message: Message):
    state = get_state(message.chat.id)
    state["mode"] = "mixed"
    await message.answer("Режим: 🎲 Смешанный.\nНажми «▶️ Начать квиз».", reply_markup=main_menu_kb())


async def choose_topic(message: Message):
    if not TOPICS:
        await message.answer("Темы не найдены. Добавь поле \"topic\" в words.json.")
        return

    await message.answer(
        "Выбери тему ⬇️",
        reply_markup=topics_kb(),
    )


async def on_topic_chosen(callback: CallbackQuery):
    await callback.answer()  # закрыть "часики"

    try:
        _, idx_str = callback.data.split(":")
        idx = int(idx_str)
    except Exception:
        await callback.message.answer("Ошибка выбора темы.")
        return

    if idx < 0 or idx >= len(TOPICS):
        await callback.message.answer("Тема не найдена.")
        return

    topic = TOPICS[idx]
    state = get_state(callback.message.chat.id)
    state["topic"] = topic

    await callback.message.answer(
        f"Тема выбрана: *{topic}*.\nНажми «▶️ Начать квиз».",
        parse_mode="Markdown",
        reply_markup=main_menu_kb(),
    )


async def start_quiz(message: Message):
    chat_id = message.chat.id
    state = get_state(chat_id)

    # увеличиваем id вопроса, чтобы защититься от старых нажатий
    state["last_question_id"] += 1
    qid = state["last_question_id"]

    q = build_question(chat_id)

    kb = answers_kb(q["options"], q["correct_index"], qid)

    # сохраняем текущий вопрос в состоянии
    state["current_question"] = q

    await message.answer(
        q["text"],
        parse_mode="Markdown",
        reply_markup=kb,
    )


async def on_answer(callback: CallbackQuery):
    await callback.answer()

    chat_id = callback.message.chat.id
    state = get_state(chat_id)

    try:
        _, qid_str, chosen_str, correct_str = callback.data.split(":")
        qid = int(qid_str)
        chosen = int(chosen_str)
        correct = int(correct_str)
    except Exception:
        await callback.message.answer("Ошибка обработки ответа.")
        return

    # игнорируем старые нажатия, если уже был другой вопрос
    if qid != state.get("last_question_id"):
        return

    q = state.get("current_question")
    if not q:
        await callback.message.answer("Вопрос не найден. Нажми «▶️ Начать квиз».")
        return

    word = q["word"]
    direction = q["direction"]

    # формируем строку с правильным ответом
    correct_line = f"{word['de']} [{word.get('tr', '')}] – {word['ru']}"

    if chosen == correct:
        await callback.message.answer(f"✅ Правильно!\n{correct_line}")
    else:
        await callback.message.answer(f"❌ Неправильно.\nПравильно: {correct_line}")

    # задаём новый вопрос
    state["last_question_id"] += 1
    new_qid = state["last_question_id"]
    new_q = build_question(chat_id)
    state["current_question"] = new_q

    kb = answers_kb(new_q["options"], new_q["correct_index"], new_qid)

    await callback.message.answer(
        new_q["text"],
        parse_mode="Markdown",
        reply_markup=kb,
    )

# ======================================
#  РЕГИСТРАЦИЯ ХЕНДЛЕРОВ И ЗАПУСК
# ======================================

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    # команды
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_help, Command("help"))

    # режимы
    dp.message.register(set_mode_de_ru, F.text == "🇩🇪 Немецкий → Русский")
    dp.message.register(set_mode_ru_de, F.text == "🇷🇺 Русский → Немецкий")
    dp.message.register(set_mode_mixed, F.text == "🎲 Смешанный режим")

    # выбор темы и старт квиза
    dp.message.register(choose_topic, F.text == "📚 Выбрать тему")
    dp.message.register(start_quiz, F.text == "▶️ Начать квиз")

    # callback-кнопки
    dp.callback_query.register(on_topic_chosen, F.data.startswith("topic:"))
    dp.callback_query.register(on_answer, F.data.startswith("ans:"))

    logging.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

