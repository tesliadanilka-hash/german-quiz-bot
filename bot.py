import asyncio
import json
import logging
import os
import random
from typing import Dict, List, Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ---------------------------------------------------------
# НАСТРОЙКИ
# ---------------------------------------------------------

# Рекомендуется хранить токен в переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")

WORDS_FILE = "words.json"

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------
# ЗАГРУЗКА СЛОВ
# ---------------------------------------------------------

WORDS: List[Dict[str, Any]] = []
TOPIC_WORDS: Dict[str, List[Dict[str, Any]]] = {}


def load_words() -> None:
    """Загружаем слова из words.json и раскладываем по темам."""
    global WORDS, TOPIC_WORDS
    with open(WORDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Ожидаем список словарей
    if not isinstance(data, list):
        raise ValueError("words.json должен содержать список объектов")

    WORDS = []
    TOPIC_WORDS = {}

    for item in data:
        de = item.get("de")
        tr = item.get("tr")
        ru = item.get("ru")
        topic = item.get("topic", "Без темы")

        if not de or not ru:
            # пропускаем некорректные записи
            continue

        word = {"de": de, "tr": tr or "", "ru": ru, "topic": topic}
        WORDS.append(word)

        TOPIC_WORDS.setdefault(topic, []).append(word)

    if not WORDS:
        raise ValueError("В words.json нет корректных слов")


def get_stats_text() -> str:
    """Текст со статистикой по словам и темам."""
    total = len(WORDS)
    topic_lines = []
    for topic in sorted(TOPIC_WORDS.keys()):
        topic_lines.append(f"• {topic}: {len(TOPIC_WORDS[topic])} слов")

    text = (
        f"📚 В словаре сейчас: <b>{total}</b> слов\n"
        f"🗂 Тем: <b>{len(TOPIC_WORDS)}</b>\n\n"
        + "\n".join(topic_lines)
    )
    return text


# ---------------------------------------------------------
# СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ (ПАМЯТЬ В ОЗУ)
# ---------------------------------------------------------

# mode: 'de-ru', 'ru-de', 'mixed'
# topic: имя темы или 'ALL'
# last_word: последнее показанное слово (dict)
USER_STATE: Dict[int, Dict[str, Any]] = {}


def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in USER_STATE:
        USER_STATE[user_id] = {
            "mode": "de-ru",  # режим по умолчанию
            "topic": "ALL",   # все темы
            "last_word": None,
        }
    return USER_STATE[user_id]


# ---------------------------------------------------------
# КЛАВИАТУРЫ
# ---------------------------------------------------------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🇩🇪 Немецкий → Русский", callback_data="mode:de-ru")],
        [InlineKeyboardButton(text="🇷🇺 Русский → Немецкий", callback_data="mode:ru-de")],
        [InlineKeyboardButton(text="🎲 Смешанный режим", callback_data="mode:mixed")],
        [InlineKeyboardButton(text="📚 Выбрать тему", callback_data="choose_topic")],
        [InlineKeyboardButton(text="▶️ Начать квиз", callback_data="start_quiz")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def topics_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="🌐 Все темы", callback_data="topic:ALL")]]

    for topic in sorted(TOPIC_WORDS.keys()):
        rows.append([InlineKeyboardButton(text=topic, callback_data=f"topic:{topic}")])

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def answers_keyboard(options: List[str], correct_index: int) -> InlineKeyboardMarkup:
    rows = []
    for idx, option in enumerate(options):
        is_correct = "1" if idx == correct_index else "0"
        rows.append(
            [
                InlineKeyboardButton(
                    text=option,
                    callback_data=f"ans:{is_correct}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------------------------------------------------------
# ГЕНЕРАЦИЯ ВОПРОСОВ
# ---------------------------------------------------------

def choose_pool(topic: str) -> List[Dict[str, Any]]:
    if topic == "ALL":
        return WORDS
    return TOPIC_WORDS.get(topic, WORDS)


def build_question(user_id: int) -> (str, InlineKeyboardMarkup, Dict[str, Any]):
    """Создаём вопрос и варианты ответов для пользователя."""
    state = get_user_state(user_id)
    mode = state.get("mode", "de-ru")
    topic = state.get("topic", "ALL")

    pool = choose_pool(topic)
    correct = random.choice(pool)

    # Смешанный режим
    real_mode = mode
    if mode == "mixed":
        real_mode = random.choice(["de-ru", "ru-de"])

    # Текст вопроса и правильный ответ
    if real_mode == "de-ru":
        question_text = f"{correct['de']} [{correct['tr']}]"
        correct_answer = correct["ru"]
        # Для неправильных ответов берём другие русские переводы
        other_values = [w["ru"] for w in pool if w is not correct]
    else:  # ru-de
        question_text = correct["ru"]
        correct_answer = f"{correct['de']} [{correct['tr']}]"
        # Для неправильных ответов берём другие немецкие слова
        other_values = [
            f"{w['de']} [{w['tr']}]" for w in pool if w is not correct
        ]

    # 3 случайных неправильных варианта
    random.shuffle(other_values)
    distractors = other_values[:3]

    # Собираем варианты, перемешиваем
    options = distractors + [correct_answer]
    random.shuffle(options)
    correct_index = options.index(correct_answer)

    kb = answers_keyboard(options, correct_index)
    question_full_text = f"🔤 Слово:\n<b>{question_text}</b>"

    return question_full_text, kb, correct


async def send_new_question(message: Message | CallbackQuery) -> None:
    """Отправляем новое слово пользователю."""
    if isinstance(message, CallbackQuery):
        user_id = message.from_user.id
        send_func = message.message.answer
    else:
        user_id = message.from_user.id
        send_func = message.answer

    q_text, kb, correct = build_question(user_id)
    state = get_user_state(user_id)
    state["last_word"] = correct

    await send_func(q_text, reply_markup=kb)


# ---------------------------------------------------------
# ОБРАБОТЧИКИ
# ---------------------------------------------------------

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    state = get_user_state(message.from_user.id)

    stats_text = get_stats_text()
    text = (
        "🇩🇪 Добро пожаловать в бот для тренировки немецких слов!\n\n"
        "Вот как он работает:\n"
        "• Бот показывает слово и 4 варианта ответа\n"
        "• 1 вариант правильный\n"
        "• Если ты ошибаешься, бот показывает правильный ответ полностью\n"
        "• Если отвечаешь верно, показывает ✅ и сразу даёт следующее слово\n\n"
        f"{stats_text}\n\n"
        "Выбери режим и тему, потом нажми ▶️ <b>Начать квиз</b>."
    )

    await message.answer(text, reply_markup=main_menu_keyboard())


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """Показать статистику по словам и темам."""
    await message.answer(get_stats_text())


# --- КНОПКИ МЕНЮ ---


@dp.callback_query(F.data == "back_to_menu")
async def cb_back_to_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Главное меню.\n\n" + get_stats_text(),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("mode:"))
async def cb_set_mode(callback: CallbackQuery) -> None:
    mode = callback.data.split(":", 1)[1]
    state = get_user_state(callback.from_user.id)
    state["mode"] = mode

    mode_names = {
        "de-ru": "🇩🇪 Немецкий → Русский",
        "ru-de": "🇷🇺 Русский → Немецкий",
        "mixed": "🎲 Смешанный режим",
    }
    human = mode_names.get(mode, mode)

    await callback.answer(f"Режим: {human}")
    await callback.message.edit_text(
        f"Режим установлен: <b>{human}</b>\n\n"
        "Теперь ты можешь выбрать тему или сразу нажать ▶️ Начать квиз.",
        reply_markup=main_menu_keyboard(),
    )


@dp.callback_query(F.data == "choose_topic")
async def cb_choose_topic(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📚 Выбери тему для тренировки:",
        reply_markup=topics_keyboard(),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("topic:"))
async def cb_set_topic(callback: CallbackQuery) -> None:
    topic = callback.data.split(":", 1)[1]
    state = get_user_state(callback.from_user.id)

    if topic == "ALL":
        state["topic"] = "ALL"
        txt = "Все темы"
    else:
        state["topic"] = topic
        txt = topic

    await callback.answer(f"Тема: {txt}")
    await callback.message.edit_text(
        f"Тема установлена: <b>{txt}</b>\n\n"
        "Теперь нажми ▶️ Начать квиз.",
        reply_markup=main_menu_keyboard(),
    )


@dp.callback_query(F.data == "start_quiz")
async def cb_start_quiz(callback: CallbackQuery) -> None:
    await callback.answer("Поехали! 🎯")
    await send_new_question(callback)
    # удалим сообщение с меню, чтобы не мешалось
    try:
        await callback.message.delete()
    except Exception:
        pass


# --- ОТВЕТЫ НА ВОПРОСЫ ---


@dp.callback_query(F.data.startswith("ans:"))
async def cb_answer(callback: CallbackQuery) -> None:
    is_correct = callback.data.split(":", 1)[1] == "1"
    user_id = callback.from_user.id
    state = get_user_state(user_id)
    last_word = state.get("last_word")

    if not last_word:
        # если вдруг нет состояния, просто отправим новый вопрос
        await callback.answer("Попробуем ещё раз 😉")
        await send_new_question(callback)
        return

    if is_correct:
        # просто показываем галочку во всплывающем уведомлении
        await callback.answer("✅ Верно!")
    else:
        # показываем правильный ответ и потом новое слово
        await callback.answer("❌ Неправильно")
        text = (
            "❌ Неправильно.\n"
            "Правильный ответ:\n"
            f"<b>{last_word['de']}</b> [{last_word['tr']}] — {last_word['ru']}"
        )
        await callback.message.answer(text)

    # отправляем следующее слово
    await send_new_question(callback)

    # старое сообщение с вопросом можно удалить, чтобы не копились
    try:
        await callback.message.delete()
    except Exception:
        pass


# ---------------------------------------------------------
# ЗАПУСК БОТА
# ---------------------------------------------------------

async def main() -> None:
    load_words()
    logging.info(
        "Loaded %d words in %d topics",
        len(WORDS),
        len(TOPIC_WORDS),
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
