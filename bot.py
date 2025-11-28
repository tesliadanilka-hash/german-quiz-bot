import asyncio
import json
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ---------------------------------------------------------
# 1. НАСТРОЙКА ТОКЕНА
# ---------------------------------------------------------
TOKEN = os.getenv("8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE")  # для background worker

# Если запускаешь локально, можешь раскомментировать:
# TOKEN = "ТОКЕН_ОТ_BOTFATHER"

if not TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN (переменная окружения или константа).")

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ---------------------------------------------------------
# 2. МОДЕЛИ И ГЛОБАЛЬНЫЕ СТРУКТУРЫ
# ---------------------------------------------------------

@dataclass
class Word:
    id: int
    topic: str
    de: str
    tr: str
    ru: str


@dataclass
class UserState:
    mode: str = "de-ru"  # "de-ru" или "ru-de"
    topic: Optional[str] = None  # None = все темы
    remaining_ids: List[int] = field(default_factory=list)
    current_word_id: Optional[int] = None
    correct: int = 0
    wrong: int = 0


WORDS: List[Word] = []
WORDS_BY_ID: Dict[int, Word] = {}
TOPIC_TO_WORD_IDS: Dict[str, List[int]] = {}

USERS: Dict[int, UserState] = {}


# ---------------------------------------------------------
# 3. ЗАГРУЗКА СЛОВ ИЗ words.json
# ---------------------------------------------------------
# ОЖИДАЕТСЯ ФОРМАТ:
# [
#   {"id": 1, "topic": "1. Приветствия", "de": "Hallo", "tr": "хá-ло", "ru": "привет"},
#   {"id": 2, "topic": "1. Приветствия", "de": "Guten Tag", "tr": "гý-тэн так", "ru": "добрый день"},
#   {"id": 100, "topic": "2. Семья", "de": "Die Familie", "tr": "фа-ми́-ли-е", "ru": "семья"},
#   ...
# ]

def load_words(path: str = "words.json") -> None:
    global WORDS, WORDS_BY_ID, TOPIC_TO_WORD_IDS
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    WORDS = []
    WORDS_BY_ID = {}
    TOPIC_TO_WORD_IDS = {}

    for item in data:
        w = Word(
            id=int(item["id"]),
            topic=item["topic"],
            de=item["de"],
            tr=item.get("tr", ""),
            ru=item["ru"],
        )
        WORDS.append(w)
        WORDS_BY_ID[w.id] = w
        TOPIC_TO_WORD_IDS.setdefault(w.topic, []).append(w.id)


# ---------------------------------------------------------
# 4. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ---------------------------------------------------------

def get_user_state(user_id: int) -> UserState:
    if user_id not in USERS:
        USERS[user_id] = UserState()
        reset_user_topic(user_id)  # по умолчанию: все темы
    return USERS[user_id]


def reset_user_topic(user_id: int, topic: Optional[str] = None) -> None:
    state = get_user_state(user_id)
    state.topic = topic

    if topic is None:
        pool = [w.id for w in WORDS]
    else:
        pool = TOPIC_TO_WORD_IDS.get(topic, [])

    state.remaining_ids = pool.copy()
    random.shuffle(state.remaining_ids)

    state.current_word_id = None
    state.correct = 0
    state.wrong = 0


def format_word_full_de(word: Word) -> str:
    if word.tr:
        return f"{word.de} [{word.tr}]"
    return word.de


def format_answer_block(word: Word, mode: str, prefix: str) -> str:
    full_de = format_word_full_de(word)
    full_ru = word.ru

    if mode == "de-ru":
        return (
            f"{prefix}\n\n"
            f"🇩🇪 <b>{full_de}</b>\n"
            f"🇷🇺 <b>{full_ru}</b>"
        )
    else:
        return (
            f"{prefix}\n\n"
            f"🇷🇺 <b>{full_ru}</b>\n"
            f"🇩🇪 <b>{full_de}</b>"
        )


def pick_distractors(word: Word, mode: str, count: int = 3) -> List[str]:
    vals: List[str] = []
    candidates = WORDS.copy()
    random.shuffle(candidates)

    for w in candidates:
        if w.id == word.id:
            continue
        val = w.ru if mode == "de-ru" else w.de
        if val in vals:
            continue
        vals.append(val)
        if len(vals) >= count:
            break

    return vals


async def send_next_question(message: Message, user_id: int) -> None:
    state = get_user_state(user_id)

    if not state.remaining_ids:
        total = state.correct + state.wrong
        if total == 0:
            await message.answer("В этой теме пока нет вопросов.")
        else:
            topic_name = state.topic or "Все темы"
            await message.answer(
                f"📊 Тема: <b>{topic_name}</b>\n"
                f"Правильных ответов: <b>{state.correct}</b>\n"
                f"Неправильных ответов: <b>{state.wrong}</b>\n\n"
                f"Чтобы пройти тему ещё раз — выбери её в /themes или нажми /next для перемешки."
            )

        reset_user_topic(user_id, state.topic)
        return

    word_id = state.remaining_ids.pop()
    state.current_word_id = word_id
    word = WORDS_BY_ID[word_id]

    mode = state.mode

    if mode == "de-ru":
        question_text = f"🇩🇪 <b>{format_word_full_de(word)}</b>\n\nВыбери перевод на русский:"
        correct_option = word.ru
    else:
        question_text = f"🇷🇺 <b>{word.ru}</b>\n\nВыбери перевод на немецкий:"
        correct_option = word.de

    distractors = pick_distractors(word, mode, count=3)
    options = [correct_option] + distractors
    random.shuffle(options)

    kb = InlineKeyboardBuilder()
    for opt in options:
        is_correct = 1 if opt == correct_option else 0
        kb.button(
            text=opt,
            callback_data=f"ans:{word_id}:{is_correct}",
        )
    kb.adjust(2)

    await message.answer(question_text, reply_markup=kb.as_markup())


# ---------------------------------------------------------
# 5. КОМАНДЫ
# ---------------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    reset_user_topic(user_id, None)
    total_words = len(WORDS)
    topics_count = len(TOPIC_TO_WORD_IDS)

    text = (
        "🇩🇪 Привет! Это бот для изучения немецких слов.\n\n"
        "Как работает:\n"
        "• Я показываю слово и 4 варианта перевода.\n"
        "• Если ответ верный – ✅ и показываю полный правильный ответ.\n"
        "• Если ответ неверный – ❌ и показываю правильный ответ.\n\n"
        f"Сейчас в базе <b>{total_words}</b> слов.\n"
        f"Тем: <b>{topics_count}</b>.\n\n"
        "Команды:\n"
        "/next  – следующее слово\n"
        "/themes – выбрать тему (слова уже разделены по темам)\n"
        "/mode   – направление перевода\n"
        "/stats  – статистика по текущей теме\n\n"
        "По умолчанию: все темы вперемешку, режим 🇩🇪 → 🇷🇺.\n"
        "Нажми /next, чтобы начать."
    )
    await message.answer(text)


@dp.message(Command("next"))
async def cmd_next(message: Message) -> None:
    await send_next_question(message, message.from_user.id)


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    state = get_user_state(message.from_user.id)
    topic_name = state.topic or "Все темы"
    total = state.correct + state.wrong

    await message.answer(
        f"📊 Тема: <b>{topic_name}</b>\n"
        f"Правильных: <b>{state.correct}</b>\n"
        f"Неправильных: <b>{state.wrong}</b>\n"
        f"Всего отвечено: <b>{total}</b>"
    )


@dp.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇩🇪 → 🇷🇺", callback_data="mode:de-ru")
    kb.button(text="🇷🇺 → 🇩🇪", callback_data="mode:ru-de")
    kb.adjust(2)
    await message.answer("Выбери направление перевода:", reply_markup=kb.as_markup())


@dp.message(Command("themes"))
async def cmd_themes(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="Все темы (перемешка)", callback_data="theme:__all__")

    for topic in sorted(TOPIC_TO_WORD_IDS.keys()):
        kb.button(text=topic, callback_data=f"theme:{topic}")

    kb.adjust(1)
    await message.answer("Выбери тему:", reply_markup=kb.as_markup())


# ---------------------------------------------------------
# 6. CALLBACK'И
# ---------------------------------------------------------

@dp.callback_query(F.data.startswith("mode:"))
async def callback_mode(call: CallbackQuery) -> None:
    mode = call.data.split(":", maxsplit=1)[1]
    state = get_user_state(call.from_user.id)

    if mode not in ("de-ru", "ru-de"):
        await call.answer("Неизвестный режим.", show_alert=True)
        return

    state.mode = mode
    reset_user_topic(call.from_user.id, state.topic)

    if mode == "de-ru":
        text = "Режим: 🇩🇪 → 🇷🇺."
    else:
        text = "Режим: 🇷🇺 → 🇩🇪."

    await call.message.answer(text)
    await call.answer()


@dp.callback_query(F.data.startswith("theme:"))
async def callback_theme(call: CallbackQuery) -> None:
    raw = call.data.split(":", maxsplit=1)[1]

    if raw == "__all__":
        reset_user_topic(call.from_user.id, None)
        await call.message.answer("Тема: все слова вперемешку. Нажми /next.")
    else:
        if raw not in TOPIC_TO_WORD_IDS:
            await call.answer("Неизвестная тема.", show_alert=True)
            return
        reset_user_topic(call.from_user.id, raw)
        await call.message.answer(f"Тема переключена на: <b>{raw}</b>. Нажми /next.")

    await call.answer()


@dp.callback_query(F.data.startswith("ans:"))
async def callback_answer(call: CallbackQuery) -> None:
    try:
        _, word_id_str, is_correct_str = call.data.split(":")
        word_id = int(word_id_str)
        is_correct = is_correct_str == "1"
    except Exception:
        await call.answer("Ошибка данных.", show_alert=True)
        return

    state = get_user_state(call.from_user.id)

    if state.current_word_id != word_id:
        await call.answer("Этот вопрос уже неактуален. Нажми /next.", show_alert=True)
        return

    word = WORDS_BY_ID.get(word_id)
    if not word:
        await call.answer("Слово не найдено.", show_alert=True)
        return

    mode = state.mode

    if is_correct:
        state.correct += 1
        text = format_answer_block(word, mode, "✅ Верно!\n\nПравильный ответ:")
    else:
        state.wrong += 1
        text = format_answer_block(word, mode, "❌ Неверно.\n\nПравильный ответ:")

    await call.message.answer(text)
    await call.answer()
    await send_next_question(call.message, call.from_user.id)


# ---------------------------------------------------------
# 7. ЗАПУСК
# ---------------------------------------------------------

async def main() -> None:
    load_words("words.json")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

