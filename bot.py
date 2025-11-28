import asyncio
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ============================================================
# 1. BOT TOKEN
# ============================================================

# ВСТАВЬ СВОЙ ТОКЕН ОТ BotFather СЮДА
TOKEN = "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE"

# ============================================================
# 2. DATA: WORDS + THEMES
# ============================================================

# Все слова. Поля:
# id   - уникальный номер
# topic - ключ темы
# de   - немецкое слово
# tr   - транскрипция
# ru   - перевод
WORDS: List[Dict] = [
    # ---------- Примеры. Сюда ты добавляешь весь свой список ----------
    # Тема: приветствия
    {"id": 1, "topic": "greetings", "de": "Hallo", "tr": "хá-ло", "ru": "привет"},
    {"id": 2, "topic": "greetings", "de": "Guten Tag", "tr": "гý-тэн так", "ru": "добрый день"},
    {"id": 3, "topic": "greetings", "de": "Guten Abend", "tr": "гý-тэн á-бэнт", "ru": "добрый вечер"},
    {"id": 4, "topic": "greetings", "de": "Guten Morgen", "tr": "гю́-тэн мóр-гэн", "ru": "доброе утро"},
    {"id": 5, "topic": "greetings", "de": "Gute Nacht", "tr": "гý-те нахт", "ru": "доброй ночи"},
    {"id": 6, "topic": "greetings", "de": "Tschüs", "tr": "чюс", "ru": "пока"},

    # Тема: семья
    {"id": 100, "topic": "family", "de": "Die Familie", "tr": "фа-ми́-ли-е", "ru": "семья"},
    {"id": 101, "topic": "family", "de": "Die Mutter", "tr": "му́т-та", "ru": "мать"},
    {"id": 102, "topic": "family", "de": "Der Vater", "tr": "фа́-та", "ru": "отец"},
    {"id": 103, "topic": "family", "de": "Der Sohn", "tr": "зон", "ru": "сын"},
    {"id": 104, "topic": "family", "de": "Die Tochter", "tr": "то́х-та", "ru": "дочь"},
    {"id": 105, "topic": "family", "de": "Der Bruder", "tr": "бру́-да", "ru": "брат"},
    {"id": 106, "topic": "family", "de": "Die Schwester", "tr": "швэс-та", "ru": "сестра"},

    # Тема: базовые глаголы
    {"id": 200, "topic": "verbs_basic", "de": "Sein", "tr": "зайн", "ru": "быть"},
    {"id": 201, "topic": "verbs_basic", "de": "Ich bin", "tr": "их бин", "ru": "я есть"},
    {"id": 202, "topic": "verbs_basic", "de": "Haben", "tr": "ха́-бэн", "ru": "иметь"},
    {"id": 203, "topic": "verbs_basic", "de": "Sprechen", "tr": "шпрэ́-хен", "ru": "говорить"},
    {"id": 204, "topic": "verbs_basic", "de": "Arbeiten", "tr": "а́р-бай-тэн", "ru": "работать"},
    {"id": 205, "topic": "verbs_basic", "de": "Lernen", "tr": "ле́р-нен", "ru": "учиться"},

    # Здесь просто продолжай добавлять все остальные 897 слов
    # с указанием поля "topic": "greetings", "family", "verbs_basic" и так далее.
]

# Все доступные темы: ключ -> человекочитаемое название
THEMES: Dict[str, str] = {
    "greetings": "Приветствия",
    "family": "Семья",
    "verbs_basic": "Базовые глаголы",
    # Добавляй сюда новые темы, когда разнесешь все слова
}

# Быстрый доступ по id
WORDS_BY_ID: Dict[int, Dict] = {w["id"]: w for w in WORDS}


def get_word_ids_by_theme(topic: str) -> List[int]:
    if topic == "all":
        return [w["id"] for w in WORDS]
    return [w["id"] for w in WORDS if w["topic"] == topic]


# ============================================================
# 3. USER STATE
# ============================================================

@dataclass
class UserState:
    mode: str = "de-ru"  # "de-ru" или "ru-de"
    theme: str = "greetings"  # ключ темы или "all"
    remaining_ids: List[int] = field(default_factory=list)
    correct: int = 0
    wrong: int = 0
    current_word_id: Optional[int] = None
    current_options: List[str] = field(default_factory=list)
    correct_index: int = 0


user_states: Dict[int, UserState] = {}

# ============================================================
# 4. BOT OBJECTS
# ============================================================

logging.basicConfig(level=logging.INFO)
bot = Bot(TOKEN)
dp = Dispatcher()


# ============================================================
# 5. HELPERS
# ============================================================

def get_state(user_id: int) -> UserState:
    state = user_states.get(user_id)
    if state is None:
        state = UserState()
        reset_theme_state(state)
        user_states[user_id] = state
    return state


def reset_theme_state(state: UserState) -> None:
    ids = get_word_ids_by_theme(state.theme)
    random.shuffle(ids)
    state.remaining_ids = ids
    state.correct = 0
    state.wrong = 0
    state.current_word_id = None
    state.current_options = []
    state.correct_index = 0


def build_themes_keyboard() -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []
    # Кнопка "Все темы"
    buttons.append(
        [InlineKeyboardButton(text="🔀 Все темы", callback_data="theme:all")]
    )
    # Остальные темы
    for key, title in THEMES.items():
        buttons.append(
            [InlineKeyboardButton(text=f"📚 {title}", callback_data=f"theme:{key}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_mode_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(
                text="🇩🇪 → 🇷🇺", callback_data="mode:de-ru"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇷🇺 → 🇩🇪", callback_data="mode:ru-de"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def choose_wrong_options(
    correct_word: Dict, state: UserState, count: int
) -> List[Dict]:
    """Берем неправильные варианты из той же темы, если возможно."""
    if state.theme == "all":
        pool = [w for w in WORDS if w["id"] != correct_word["id"]]
    else:
        pool = [
            w
            for w in WORDS
            if w["topic"] == state.theme and w["id"] != correct_word["id"]
        ]
        if len(pool) < count:
            pool = [w for w in WORDS if w["id"] != correct_word["id"]]

    random.shuffle(pool)
    return pool[:count]


async def send_question(message: Message, state: UserState) -> None:
    """Послать следующую карточку пользователю."""
    # Если слова по теме закончились
    if not state.remaining_ids:
        total = state.correct + state.wrong
        text = (
            f"Тема закончилась.\n\n"
            f"Всего вопросов: {total}\n"
            f"Правильных: {state.correct}\n"
            f"Неправильных: {state.wrong}\n\n"
            f"Я перезапускаю эту тему заново."
        )
        await message.answer(text)
        reset_theme_state(state)

    # Берем следующее слово
    word_id = state.remaining_ids.pop()
    word = WORDS_BY_ID[word_id]
    state.current_word_id = word_id

    # Строим варианты
    wrong_words = choose_wrong_options(word, state, 3)
    options_texts: List[str] = []

    if state.mode == "de-ru":
        correct_option = word["ru"]
        wrong_texts = [w["ru"] for w in wrong_words]
        question_text = f"🇩🇪 {word['de']} [{word['tr']}]"
        options_texts = wrong_texts + [correct_option]
    else:
        correct_option = f"{word['de']} [{word['tr']}]"
        wrong_texts = [f"{w['de']} [{w['tr']}]" for w in wrong_words]
        question_text = f"🇷🇺 {word['ru']}"
        options_texts = wrong_texts + [correct_option]

    random.shuffle(options_texts)
    correct_index = options_texts.index(correct_option)
    state.current_options = options_texts
    state.correct_index = correct_index

    # Клавиатура с вариантами
    rows: List[List[InlineKeyboardButton]] = []
    for idx, text in enumerate(options_texts):
        rows.append(
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=f"ans:{idx}",
                )
            ]
        )
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await message.answer(question_text, reply_markup=kb)


async def send_question_from_callback(callback: CallbackQuery, state: UserState) -> None:
    dummy_message = callback.message
    if dummy_message is None:
        return
    await send_question(dummy_message, state)


# ============================================================
# 6. HANDLERS
# ============================================================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    state = get_state(message.from_user.id)
    reset_theme_state(state)

    text = (
        "Привет. Это бот для изучения немецких слов.\n\n"
        "Как пользоваться:\n"
        "• Я показываю слово и четыре варианта перевода.\n"
        "• Нажми на кнопку с вариантом.\n"
        "• Если ответ неверный, я покажу правильный полный ответ и сразу дам новое слово.\n"
        "• Если ответ верный, покажу зеленую галочку и полный ответ, а потом новое слово.\n\n"
        "Команды:\n"
        "/next - следующее слово\n"
        "/themes - выбрать тему\n"
        "/mode - выбрать направление перевода\n\n"
        "По умолчанию включен режим 🇩🇪 → 🇷🇺 и тема Приветствия."
    )
    await message.answer(text)
    await send_question(message, state)


@dp.message(Command("next"))
async def cmd_next(message: Message) -> None:
    state = get_state(message.from_user.id)
    await send_question(message, state)


@dp.message(Command("themes"))
async def cmd_themes(message: Message) -> None:
    text = "Выбери тему:"
    await message.answer(text, reply_markup=build_themes_keyboard())


@dp.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    text = "Выбери направление перевода:"
    await message.answer(text, reply_markup=build_mode_keyboard())


# ---------- смена темы ----------

@dp.callback_query(F.data.startswith("theme:"))
async def callbacks_theme(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    state = get_state(user_id)
    _, topic = callback.data.split(":", 1)

    if topic == "all":
        state.theme = "all"
        theme_name = "Все темы"
    else:
        state.theme = topic
        theme_name = THEMES.get(topic, topic)

    reset_theme_state(state)
    await callback.answer()
    await callback.message.answer(
        f"Тема изменена на: {theme_name}.\nЯ обнулил статистику по этой теме."
    )
    await send_question_from_callback(callback, state)


# ---------- смена режима ----------

@dp.callback_query(F.data.startswith("mode:"))
async def callbacks_mode(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    state = get_state(user_id)
    _, mode = callback.data.split(":", 1)
    state.mode = mode
    reset_theme_state(state)

    if mode == "de-ru":
        text = "Режим изменен на 🇩🇪 → 🇷🇺. Я обнулил статистику."
    else:
        text = "Режим изменен на 🇷🇺 → 🇩🇪. Я обнулил статистику."

    await callback.answer()
    await callback.message.answer(text)
    await send_question_from_callback(callback, state)


# ---------- обработка ответа ----------

@dp.callback_query(F.data.startswith("ans:"))
async def callbacks_answer(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    state = get_state(user_id)

    if state.current_word_id is None:
        await callback.answer("Слово не найдено. Нажми /next.")
        return

    try:
        _, idx_str = callback.data.split(":", 1)
        idx = int(idx_str)
    except ValueError:
        await callback.answer()
        return

    word = WORDS_BY_ID[state.current_word_id]
    is_correct = idx == state.correct_index

    if is_correct:
        state.correct += 1
        if state.mode == "de-ru":
            text = (
                "✅ Правильно.\n\n"
                f"{word['de']} [{word['tr']}] - {word['ru']}"
            )
        else:
            text = (
                "✅ Правильно.\n\n"
                f"{word['ru']} - {word['de']} [{word['tr']}]"
            )
    else:
        state.wrong += 1
        if state.mode == "de-ru":
            text = (
                "❌ Неправильно.\nПравильный ответ:\n\n"
                f"{word['de']} [{word['tr']}] - {word['ru']}"
            )
        else:
            text = (
                "❌ Неправильно.\nПравильный ответ:\n\n"
                f"{word['ru']} - {word['de']} [{word['tr']}]"
            )

    await callback.answer()
    await callback.message.answer(text)

    # Сразу следующее слово
    await send_question_from_callback(callback, state)


# ============================================================
# 7. MAIN
# ============================================================

async def main() -> None:
    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
