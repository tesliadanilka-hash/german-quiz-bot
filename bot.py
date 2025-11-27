import asyncio
import json
import logging
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
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ===================== НАСТРОЙКИ =====================

TOKEN = "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE"   # <-- вставь сюда свой токен

# Режимы
MODE_DE_RU = "de_ru"   # вопрос по-немецки -> варианты по-русски
MODE_RU_DE = "ru_de"   # вопрос по-русски -> варианты по-немецки

# ====================================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher()

# ---------- Загружаем слова из words.json ----------

with open("words.json", "r", encoding="utf-8") as f:
    WORDS: List[Dict[str, Any]] = json.load(f)

# добавим id и тему по умолчанию
for idx, w in enumerate(WORDS):
    w["id"] = idx
    if "topic" not in w or not w["topic"]:
        w["topic"] = "Разное"

# список тем
TOPICS = sorted(set(w["topic"] for w in WORDS))
# специальная тема "Все"
TOPIC_ALL = "ALL"

# внутренняя структура: id -> слово
ID_TO_WORD = {w["id"]: w for w in WORDS}

# --------- Память настроек пользователя ---------

# user_id -> {"mode": ..., "topic": ...}
user_settings: Dict[int, Dict[str, Any]] = {}


def get_user_settings(user_id: int) -> Dict[str, Any]:
    """Гарантированно возвращает настройки пользователя."""
    if user_id not in user_settings:
        user_settings[user_id] = {
            "mode": MODE_DE_RU,
            "topic": TOPIC_ALL,
        }
    return user_settings[user_id]


# ================== КЛАВИАТУРЫ ==================


def themes_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Кнопка "Все темы"
    builder.button(text="🌍 Все темы", callback_data=f"topic:{TOPIC_ALL}")

    # Остальные темы
    for t in TOPICS:
        builder.button(text=f"📚 {t}", callback_data=f"topic:{t}")

    builder.adjust(2)
    return builder.as_markup()


def modes_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    text_de_ru = "🇩🇪 ➜ 🇷🇺 Немецкий → Русский"
    text_ru_de = "🇷🇺 ➜ 🇩🇪 Русский → Немецкий"

    if current_mode == MODE_DE_RU:
        text_de_ru = "✅ " + text_de_ru
    else:
        text_ru_de = "✅ " + text_ru_de

    builder.button(text=text_de_ru, callback_data=f"mode:{MODE_DE_RU}")
    builder.button(text=text_ru_de, callback_data=f"mode:{MODE_RU_DE}")

    builder.adjust(1)
    return builder.as_markup()


def quiz_keyboard(correct_id: int, options: List[Dict[str, Any]], mode: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for opt in options:
        if mode == MODE_DE_RU:
            btn_text = opt["ru"]
        else:
            # Немецкое слово + транскрипция
            btn_text = f"{opt['de']} [{opt['tr']}]"
        builder.button(
            text=btn_text,
            callback_data=f"ans:{correct_id}:{opt['id']}"
        )

    builder.adjust(2)
    return builder.as_markup()


# ================== ЛОГИКА ИГРЫ ==================


def get_words_for_topic(topic: str) -> List[Dict[str, Any]]:
    if topic == TOPIC_ALL:
        return WORDS
    return [w for w in WORDS if w["topic"] == topic]


async def send_next_question(chat_id: int, user_id: int):
    settings = get_user_settings(user_id)
    mode = settings["mode"]
    topic = settings["topic"]

    words_pool = get_words_for_topic(topic)

    if len(words_pool) < 1:
        await bot.send_message(
            chat_id,
            "⚠️ В этой теме пока нет слов. Выбери другую тему через /themes."
        )
        return

    # если мало слов, уменьшаем количество вариантов
    num_options = 4 if len(words_pool) >= 4 else len(words_pool)

    correct = random.choice(words_pool)

    # другие варианты
    others = [w for w in words_pool if w["id"] != correct["id"]]
    random.shuffle(others)
    others = others[: num_options - 1]

    options = others + [correct]
    random.shuffle(options)

    # Текст вопроса
    if mode == MODE_DE_RU:
        question_text = (
            f"🇩🇪 <b>{correct['de']}</b> [{correct['tr']}]\n\n"
            f"Выбери правильный перевод на русский:"
        )
    else:
        question_text = (
            f"🇷🇺 <b>{correct['ru']}</b>\n\n"
            f"Выбери правильный вариант на немецком:"
        )

    keyboard = quiz_keyboard(correct["id"], options, mode)

    await bot.send_message(
        chat_id,
        question_text,
        reply_markup=keyboard
    )


def format_full_answer(word: Dict[str, Any]) -> str:
    return f"🇩🇪 <b>{word['de']}</b> [{word['tr']}] — 🇷🇺 <b>{word['ru']}</b>"


# ================== ХЭНДЛЕРЫ ==================


@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    settings = get_user_settings(user_id)

    total_words = len(WORDS)
    current_topic = settings["topic"]
    if current_topic == TOPIC_ALL:
        topic_text = "Все темы"
    else:
        topic_text = current_topic

    mode_text = "🇩🇪 → 🇷🇺 Немецкий → Русский" if settings["mode"] == MODE_DE_RU else "🇷🇺 → 🇩🇪 Русский → Немецкий"

    text = (
        "🇩🇪 <b>German Quiz Bot</b>\n\n"
        "Я помогу тебе учить немецкие слова в формате викторины.\n\n"
        f"📚 Всего слов в базе: <b>{total_words}</b>\n"
        f"📂 Текущая тема: <b>{topic_text}</b>\n"
        f"🎯 Текущий режим: <b>{mode_text}</b>\n\n"
        "Команды:\n"
        "• /themes — выбрать тему\n"
        "• /mode — выбрать режим\n\n"
        "Нажми на тему или режим и начнём! 👇"
    )

    await message.answer(text, reply_markup=themes_keyboard())


@dp.message(Command("themes"))
async def cmd_themes(message: Message):
    await message.answer(
        "📂 Выбери тему, с которой хочешь тренироваться:",
        reply_markup=themes_keyboard()
    )


@dp.message(Command("mode"))
async def cmd_mode(message: Message):
    settings = get_user_settings(message.from_user.id)
    await message.answer(
        "🎯 Выбери режим:",
        reply_markup=modes_keyboard(settings["mode"])
    )


@dp.callback_query(F.data.startswith("topic:"))
async def cb_set_topic(callback: CallbackQuery):
    user_id = callback.from_user.id
    topic = callback.data.split(":", 1)[1]

    settings = get_user_settings(user_id)
    settings["topic"] = topic

    if topic == TOPIC_ALL:
        topic_text = "Все темы"
    else:
        topic_text = topic

    await callback.answer()  # закрыть "часики"

    await callback.message.answer(
        f"📂 Тема изменена на: <b>{topic_text}</b>\n"
        "Отлично! Вот твоё следующее слово 👇"
    )

    await send_next_question(callback.message.chat.id, user_id)


@dp.callback_query(F.data.startswith("mode:"))
async def cb_set_mode(callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data.split(":", 1)[1]

    settings = get_user_settings(user_id)
    settings["mode"] = mode

    await callback.answer()

    mode_text = "🇩🇪 → 🇷🇺 Немецкий → Русский" if mode == MODE_DE_RU else "🇷🇺 → 🇩🇪 Русский → Немецкий"

    await callback.message.answer(
        f"🎯 Режим изменён на: <b>{mode_text}</b>\n"
        "Поехали дальше! 👇"
    )

    await send_next_question(callback.message.chat.id, user_id)


@dp.callback_query(F.data.startswith("ans:"))
async def cb_answer(callback: CallbackQuery):
    try:
        _, correct_id_str, chosen_id_str = callback.data.split(":")
        correct_id = int(correct_id_str)
        chosen_id = int(chosen_id_str)
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    user_id = callback.from_user.id
    settings = get_user_settings(user_id)
    mode = settings["mode"]

    correct_word = ID_TO_WORD.get(correct_id)
    chosen_word = ID_TO_WORD.get(chosen_id)

    if not correct_word or not chosen_word:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    await callback.answer()  # закрыть "часики"

    if correct_id == chosen_id:
        # правильный ответ
        await callback.message.answer("✅ Правильно!")
    else:
        # неправильный ответ
        full = format_full_answer(correct_word)
        await callback.message.answer(
            "❌ Неправильно.\n"
            f"Правильный ответ:\n{full}"
        )

    # отправляем следующее слово
    await send_next_question(callback.message.chat.id, user_id)


# ================== ЗАПУСК ==================


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
