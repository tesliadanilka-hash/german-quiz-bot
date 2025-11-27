# bot.py
import asyncio
import json
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Text

# ============================================================
# Настройки
# ============================================================

TOKEN = os.getenv("8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE")  # ОБЯЗАТЕЛЬНО задай это в Render

if not TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана!")

# Режимы
MODE_DE_RU = "de_ru"      # Немецкий → Русский
MODE_RU_DE = "ru_de"      # Русский → Немецкий
MODE_MIXED = "mixed"      # Смешанный


# ============================================================
# Загрузка слов
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
WORDS_PATH = BASE_DIR / "words.json"

with WORDS_PATH.open("r", encoding="utf-8") as f:
    RAW_WORDS = json.load(f)

# Разбиваем по темам
topics_dict: Dict[str, list] = defaultdict(list)

for item in RAW_WORDS:
    # Ожидаем ключи "de", "tr", "ru", "topic"
    de = item.get("de")
    tr = item.get("tr")
    ru = item.get("ru")
    topic = item.get("topic", "Общее")

    # Простая фильтрация, чтобы не падать, если чего-то нет
    if not (de and ru):
        continue

    topics_dict[topic].append(
        {
            "de": de,
            "tr": tr or "",
            "ru": ru,
            "topic": topic,
        }
    )

TOPICS: Dict[str, list] = dict(topics_dict)
TOTAL_TOPICS = len(TOPICS)
TOTAL_WORDS = sum(len(words) for words in TOPICS.values())

# ============================================================
# Клавиатуры
# ============================================================

# Тексты кнопок (чтобы не ошибаться)
BTN_DE_RU = "🇩🇪 Немецкий → Русский"
BTN_RU_DE = "🇷🇺 Русский → Немецкий"
BTN_MIXED = "🎲 Смешанный режим"
BTN_CHOOSE_TOPIC = "📚 Выбрать тему"
BTN_START_QUIZ = "▶️ Начать квиз"


def main_menu_kb() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_DE_RU)],
            [KeyboardButton(text=BTN_RU_DE)],
            [KeyboardButton(text=BTN_MIXED)],
            [KeyboardButton(text=BTN_CHOOSE_TOPIC)],
            [KeyboardButton(text=BTN_START_QUIZ)],
        ],
        resize_keyboard=True,
    )
    return kb


def topics_inline_kb(current_topic: str | None) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура со списком тем.
    current_topic – текущая выбранная тема пользователя (для галочки).
    """
    buttons = []

    # Делаем красивый список: максимум 2 кнопки в ряд
    row: list[InlineKeyboardButton] = []
    for topic in sorted(TOPICS.keys()):
        text = topic
        if topic == current_topic:
            text = f"✅ {topic}"
        row.append(
            InlineKeyboardButton(
                text=text,
                callback_data=f"topic:{topic}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Отдельная кнопка "Любая тема"
    any_text = "🎯 Любая тема"
    if current_topic is None:
        any_text = "✅ Любая тема"

    buttons.append(
        [
            InlineKeyboardButton(
                text=any_text,
                callback_data="topic:any",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def answers_kb(options: list[str]) -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура вариантов ответа.
    В callback_data передаём индекс варианта: ans:0, ans:1, ...
    """
    buttons = []
    for i, opt in enumerate(options):
        buttons.append(
            [
                InlineKeyboardButton(
                    text=opt,
                    callback_data=f"ans:{i}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================================
# Хранилище состояний пользователей
# ============================================================

# Простейшее in-memory хранилище.
# Для продакшена можно заменить на Redis/Bot Storage.
users: Dict[int, Dict[str, Any]] = {}


def get_user_state(user_id: int) -> Dict[str, Any]:
    """
    Возвращает состояние пользователя.
    Если нет – создаёт с настройками по умолчанию.
    """
    if user_id not in users:
        users[user_id] = {
            "mode": MODE_DE_RU,   # режим по умолчанию
            "topic": None,        # None = любая тема
            "current_word": None,
            "current_options": None,
            "correct_index": None,
        }
    return users[user_id]


# ============================================================
# Логика выбора слов и вопросов
# ============================================================

def get_words_for_user(user_state: Dict[str, Any]) -> list[dict]:
    """Возвращает список слов с учётом выбранной темы."""
    topic = user_state.get("topic")
    if topic is None or topic == "Любая тема":
        # Все слова
        result = []
        for words in TOPICS.values():
            result.extend(words)
        return result
    else:
        return TOPICS.get(topic, [])


def prepare_question(user_state: Dict[str, Any]) -> dict | None:
    """
    Формирует один вопрос:
    - выбирает слово
    - генерирует 4 варианта ответов
    Возвращает dict с полями:
        question_text, options, correct_index
    или None, если нет слов.
    """
    words = get_words_for_user(user_state)
    if not words:
        return None

    word = random.choice(words)
    mode = user_state["mode"]

    # В зависимости от режима выбираем направление
    if mode == MODE_DE_RU:
        question_side = "de"
        answer_side = "ru"
        direction = "🇩🇪 → 🇷🇺"
    elif mode == MODE_RU_DE:
        question_side = "ru"
        answer_side = "de"
        direction = "🇷🇺 → 🇩🇪"
    else:  # MODE_MIXED
        if random.random() < 0.5:
            question_side = "de"
            answer_side = "ru"
            direction = "🇩🇪 → 🇷🇺"
        else:
            question_side = "ru"
            answer_side = "de"
            direction = "🇷🇺 → 🇩🇪"

    correct_answer = word[answer_side]

    # Собираем неправильные варианты
    all_words = words  # можно брать только в рамках темы
    wrong_answers = set()
    while len(wrong_answers) < 3 and len(wrong_answers) < max(0, len(all_words) - 1):
        w = random.choice(all_words)
        if w is word:
            continue
        wrong_answers.add(w[answer_side])

    options = list(wrong_answers)
    options.append(correct_answer)
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    # Текст вопроса
    # Добавляем транскрипцию, если есть
    tr_part = word.get("tr")
    if question_side == "de":
        base = word["de"]
    else:
        base = word["ru"]

    if tr_part and question_side == "de":
        question_word = f"{base} [{tr_part}]"
    else:
        question_word = base

    question_text = f"{direction}\n\nСлово:\n<b>{question_word}</b>"

    return {
        "word": word,
        "question_text": question_text,
        "options": options,
        "correct_index": correct_index,
        "question_side": question_side,
        "answer_side": answer_side,
    }


# ============================================================
# Инициализация бота
# ============================================================

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()


# ============================================================
# Хэндлеры
# ============================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    state = get_user_state(message.from_user.id)

    text = (
        "🇩🇪 Добро пожаловать в бот для тренировки немецких слов!\n\n"
        "Вот как он работает:\n"
        "• Бот показывает слово и 4 варианта ответа\n"
        "• 1 вариант правильный\n"
        "• Если ты ошибаешься, бот показывает правильный ответ полностью\n"
        "• Если отвечаешь верно, показывает ✅ и сразу даёт следующее слово\n\n"
        f"📚 В словаре сейчас: <b>{TOTAL_WORDS}</b> слов\n"
        f"🗂 Тем: <b>{TOTAL_TOPICS}</b>\n\n"
        "Выбери режим и тему, потом нажми ▶️ <b>Начать квиз</b>."
    )

    await message.answer(text, reply_markup=main_menu_kb())


# --------- Выбор режима ---------

@dp.message(Text(BTN_DE_RU))
async def set_mode_de_ru(message: Message):
    state = get_user_state(message.from_user.id)
    state["mode"] = MODE_DE_RU
    await message.answer("Режим: 🇩🇪 Немецкий → 🇷🇺 Русский", reply_markup=main_menu_kb())


@dp.message(Text(BTN_RU_DE))
async def set_mode_ru_de(message: Message):
    state = get_user_state(message.from_user.id)
    state["mode"] = MODE_RU_DE
    await message.answer("Режим: 🇷🇺 Русский → 🇩🇪 Немецкий", reply_markup=main_menu_kb())


@dp.message(Text(BTN_MIXED))
async def set_mode_mixed(message: Message):
    state = get_user_state(message.from_user.id)
    state["mode"] = MODE_MIXED
    await message.answer("Режим: 🎲 Смешанный", reply_markup=main_menu_kb())


# --------- Выбор темы ---------

@dp.message(Text(BTN_CHOOSE_TOPIC))
async def choose_topic(message: Message):
    state = get_user_state(message.from_user.id)
    current_topic = state.get("topic")
    kb = topics_inline_kb(current_topic)
    await message.answer(
        "Выбери тему для квиза (можно выбрать любую тему в любой момент):",
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("topic:"))
async def topic_chosen(callback: CallbackQuery):
    await callback.answer()  # просто закрываем "часики"

    state = get_user_state(callback.from_user.id)
    data = callback.data.split(":", 1)[1]

    if data == "any":
        state["topic"] = None
        text = "Тема: 🎯 Любая (будут использоваться все слова)."
    else:
        state["topic"] = data
        text = f"Тема: <b>{data}</b>"

    # Обновляем клавиатуру с темами (но это INLINE, здесь всё ок)
    kb = topics_inline_kb(state.get("topic"))
    await callback.message.edit_reply_markup(reply_markup=kb)
    # И отправляем отдельным сообщением информацию
    await callback.message.answer(text, reply_markup=main_menu_kb())


# --------- Старт квиза ---------

@dp.message(Text(BTN_START_QUIZ))
async def start_quiz(message: Message):
    state = get_user_state(message.from_user.id)

    question = prepare_question(state)
    if question is None:
        await message.answer(
            "Для выбранной темы пока нет слов. Попробуй выбрать другую тему.",
            reply_markup=main_menu_kb(),
        )
        return

    # Сохраняем текущий вопрос в состоянии пользователя
    state["current_word"] = question["word"]
    state["current_options"] = question["options"]
    state["correct_index"] = question["correct_index"]
    state["question_side"] = question["question_side"]
    state["answer_side"] = question["answer_side"]

    await message.answer(
        question["question_text"],
        reply_markup=answers_kb(question["options"]),
    )


# --------- Обработка ответов ---------

@dp.callback_query(F.data.startswith("ans:"))
async def answer_handler(callback: CallbackQuery):
    await callback.answer()  # закрываем "часики" у пользователя

    user_id = callback.from_user.id
    state = get_user_state(user_id)

    if state.get("current_word") is None:
        # Если по какой-то причине нет вопроса – просто игнор
        await callback.message.answer(
            "Вопрос не найден. Нажми ▶️ Начать квиз, чтобы начать заново.",
            reply_markup=main_menu_kb(),
        )
        return

    chosen_index = int(callback.data.split(":", 1)[1])
    correct_index = state["correct_index"]
    word = state["current_word"]

    # Удаляем клавиатуру у старого вопроса, чтобы по нему нельзя было нажимать повторно
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        # Если сообщение уже изменено / старое – просто пропускаем
        pass

    if chosen_index == correct_index:
        # Правильный ответ: просто поздравляем и даём следующее слово
        await callback.message.answer("✅ Верно!")

    else:
        # Неправильный ответ – показываем правильный вариант полностью
        de = word["de"]
        tr = word.get("tr") or ""
        ru = word["ru"]

        if tr:
            full = f"{de} [{tr}] — {ru}"
        else:
            full = f"{de} — {ru}"

        await callback.message.answer(
            f"❌ Неправильно.\nПравильный ответ:\n<b>{full}</b>"
        )

    # После любого ответа сразу даём следующий вопрос
    question = prepare_question(state)
    if question is None:
        await callback.message.answer(
            "Слова для выбранной темы закончились. Выбери другую тему или режим.",
            reply_markup=main_menu_kb(),
        )
        # Сбрасываем текущий вопрос
        state["current_word"] = None
        state["current_options"] = None
        state["correct_index"] = None
        return

    # Сохраняем новый вопрос
    state["current_word"] = question["word"]
    state["current_options"] = question["options"]
    state["correct_index"] = question["correct_index"]
    state["question_side"] = question["question_side"]
    state["answer_side"] = question["answer_side"]

    await callback.message.answer(
        question["question_text"],
        reply_markup=answers_kb(question["options"]),
    )


# ============================================================
# Запуск бота
# ============================================================

async def main():
    print(f"Loaded {TOTAL_WORDS} words in {TOTAL_TOPICS} topics.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())



