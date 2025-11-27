# bot.py
import asyncio
import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ============================================================
# Настройки
# ============================================================

TOKEN = os.getenv("BOT_TOKEN", "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE")
WORDS_FILE = Path("words.json")

# ============================================================
# Модель слова и загрузка словаря
# ============================================================

@dataclass
class Word:
    id: int
    de: str
    tr: str
    ru: str
    topic: str


WORDS: List[Word] = []
WORDS_BY_ID: Dict[int, Word] = {}
TOPIC_IDS: Dict[str, List[int]] = {}
TOPIC_COUNTS: Dict[str, int] = {}
TOTAL_WORDS: int = 0
ALL_TOPIC_KEY = "ALL"


def load_words() -> None:
    global WORDS, WORDS_BY_ID, TOPIC_IDS, TOPIC_COUNTS, TOTAL_WORDS

    with WORDS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    WORDS = []
    WORDS_BY_ID = {}
    TOPIC_IDS = {}
    TOPIC_COUNTS = {}

    for idx, item in enumerate(data):
        topic = item.get("topic", "Без темы")
        w = Word(
            id=idx,
            de=item["de"],
            tr=item.get("tr", ""),
            ru=item["ru"],
            topic=topic,
        )
        WORDS.append(w)
        WORDS_BY_ID[w.id] = w

        TOPIC_IDS.setdefault(topic, []).append(w.id)
        TOPIC_COUNTS[topic] = TOPIC_COUNTS.get(topic, 0) + 1

    TOTAL_WORDS = len(WORDS)


# ============================================================
# Состояние пользователя
# ============================================================

@dataclass
class UserState:
    mode: str = "de_ru"        # de_ru, ru_de, mixed
    topic: str = ALL_TOPIC_KEY # ALL или конкретная тема
    remaining_ids: List[int] = field(default_factory=list)
    current_word_id: Optional[int] = None
    correct: int = 0
    wrong: int = 0

    def reset_stats(self) -> None:
        self.correct = 0
        self.wrong = 0

    def reset_pool(self) -> None:
        if self.topic == ALL_TOPIC_KEY:
            ids = [w.id for w in WORDS]
        else:
            ids = TOPIC_IDS.get(self.topic, [])

        random.shuffle(ids)
        self.remaining_ids = ids
        self.current_word_id = None


USER_STATES: Dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    state = USER_STATES.get(user_id)
    if state is None:
        state = UserState()
        state.reset_pool()
        USER_STATES[user_id] = state
    return state


# ============================================================
# Вспомогательные функции
# ============================================================

def get_topics_ordered() -> List[str]:
    # Отсортированный список тем по имени
    return sorted(TOPIC_IDS.keys())


def format_word_for_de_ru(w: Word) -> str:
    # Как показывать слово при вопросе "немецкий -> русский"
    return f"{w.de} [{w.tr}]" if w.tr else w.de


def format_word_for_ru_de(w: Word) -> str:
    # Как показывать слово при вопросе "русский -> немецкий"
    base = w.de
    if w.tr:
        base = f"{w.de} [{w.tr}]"
    return base


def pick_wrong_answers(correct_word: Word, direction: str, count: int = 3) -> List[str]:
    # Подбор неправильных ответов того же языка
    pool: List[str] = []

    if direction == "de_ru":
        correct = correct_word.ru
        pool = [w.ru for w in WORDS if w.id != correct_word.id]
    else:
        # ru_de
        correct = format_word_for_ru_de(correct_word)
        pool = [format_word_for_ru_de(w) for w in WORDS if w.id != correct_word.id]

    pool = list(set(pool))  # убираем дубли
    if correct in pool:
        pool.remove(correct)

    if len(pool) <= count:
        return random.sample(pool, k=min(len(pool), count))

    return random.sample(pool, k=count)


async def send_stats(message: Message, state: UserState) -> None:
    total = state.correct + state.wrong
    if total == 0:
        await message.answer("Пока нет статистики по этой теме. Сначала ответь хотя бы на один вопрос.")
        return

    topic_name = "Все темы" if state.topic == ALL_TOPIC_KEY else state.topic
    text = (
        f"Тема: <b>{topic_name}</b>\n"
        f"Всего вопросов: <b>{total}</b>\n"
        f"Правильных ответов: <b>{state.correct}</b>\n"
        f"Ошибок: <b>{state.wrong}</b>"
    )
    await message.answer(text)


async def send_next_question(target, user_id: int) -> None:
    """target - это Message или CallbackQuery.message"""
    state = get_user_state(user_id)

    # Если слова закончились - показываем статистику и начинаем тему заново
    if not state.remaining_ids:
        await send_stats(target, state)
        state.reset_stats()
        state.reset_pool()
        await target.answer(
            "Ты ответил на все слова в этой теме. Статистика выше.\n"
            "Я перемешал слова, можешь продолжать с той же темой или выбрать новую через /themes."
        )
        return

    # Берем следующее слово
    word_id = state.remaining_ids.pop()
    state.current_word_id = word_id
    word = WORDS_BY_ID[word_id]

    # Определяем направление
    if state.mode == "mixed":
        direction = random.choice(["de_ru", "ru_de"])
    else:
        direction = state.mode

    if direction == "de_ru":
        question_text = format_word_for_de_ru(word)
        correct_option = word.ru
    else:
        question_text = word.ru
        correct_option = format_word_for_ru_de(word)

    # Подбираем неправильные ответы
    wrong_options = pick_wrong_answers(word, direction, count=3)
    options = [correct_option] + wrong_options
    random.shuffle(options)

    # Строим клавиатуру
    kb = InlineKeyboardBuilder()
    for option in options:
        is_correct = 1 if option == correct_option else 0
        cb_data = f"ans:{word_id}:{is_correct}"
        kb.button(text=option, callback_data=cb_data)
    kb.adjust(2)

    text = f"Выбери правильный перевод:\n\n<b>{question_text}</b>"
    await target.answer(text, reply_markup=kb.as_markup())


# ============================================================
# Инициализация бота
# ============================================================

bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher()


# ============================================================
# Обработчики команд
# ============================================================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    state = get_user_state(message.from_user.id)
    state.reset_stats()
    state.reset_pool()

    topics_count = len(TOPIC_IDS)
    text = (
        "🇩🇪 Привет! Это бот для изучения немецких слов.\n\n"
        "Как пользоваться:\n"
        "• Я показываю слово и 4 варианта перевода.\n"
        "• Нажми на кнопку с вариантом.\n"
        "• Если ответ неверный, я покажу правильный ответ и сразу дам новое слово.\n"
        "• Если ответ верный, отмечу карточку галочкой и покажу следующее слово.\n\n"
        f"Сейчас в базе <b>{TOTAL_WORDS}</b> слов.\n"
        f"Тем: <b>{topics_count}</b>.\n\n"
        "Команды:\n"
        "• /next - следующее слово\n"
        "• /themes - выбрать тему слов\n"
        "• /mode - выбрать направление перевода\n"
        "• /stats - статистика по текущей теме\n\n"
        "По умолчанию включен режим 🇩🇪 → 🇷🇺 и все темы вперемешку.\n"
        "Напиши /next, чтобы начать квиз."
    )
    await message.answer(text)


@dp.message(Command("next"))
async def cmd_next(message: Message) -> None:
    await send_next_question(message, message.from_user.id)


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    state = get_user_state(message.from_user.id)
    await send_stats(message, state)


@dp.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇩🇪 → 🇷🇺", callback_data="mode:de_ru")
    kb.button(text="🇷🇺 → 🇩🇪", callback_data="mode:ru_de")
    kb.button(text="🎲 Смешанный", callback_data="mode:mixed")
    kb.adjust(1)

    await message.answer(
        "Выбери направление перевода:",
        reply_markup=kb.as_markup()
    )


@dp.message(Command("themes"))
async def cmd_themes(message: Message) -> None:
    kb = InlineKeyboardBuilder()

    # Кнопка "Все темы"
    kb.button(text="🎲 Все темы (перемешку)", callback_data=f"topic:{ALL_TOPIC_KEY}")

    for topic in get_topics_ordered():
        count = TOPIC_COUNTS.get(topic, 0)
        kb.button(text=f"{topic} ({count})", callback_data=f"topic:{topic}")

    kb.adjust(1)
    await message.answer("Выбери тему слов:", reply_markup=kb.as_markup())


# ============================================================
# Обработчики callback-кнопок
# ============================================================

@dp.callback_query(F.data.startswith("mode:"))
async def callback_mode(call: CallbackQuery) -> None:
    await call.answer()
    mode = call.data.split(":", 1)[1]
    state = get_user_state(call.from_user.id)

    if mode not in {"de_ru", "ru_de", "mixed"}:
        await call.message.answer("Неизвестный режим.")
        return

    state.mode = mode
    mode_name = {
        "de_ru": "🇩🇪 → 🇷🇺 Немецкий на русский",
        "ru_de": "🇷🇺 → 🇩🇪 Русский на немецкий",
        "mixed": "🎲 Смешанный режим",
    }[mode]

    await call.message.answer(f"Режим перевода изменен на: <b>{mode_name}</b>.\nНапиши /next, чтобы продолжить.")


@dp.callback_query(F.data.startswith("topic:"))
async def callback_topic(call: CallbackQuery) -> None:
    await call.answer()
    topic_key = call.data.split(":", 1)[1]
    state = get_user_state(call.from_user.id)

    if topic_key != ALL_TOPIC_KEY and topic_key not in TOPIC_IDS:
        await call.message.answer("Эта тема не найдена.")
        return

    state.topic = topic_key
    state.reset_stats()
    state.reset_pool()

    if topic_key == ALL_TOPIC_KEY:
        title = "Все темы (перемешку)"
        count = TOTAL_WORDS
    else:
        title = topic_key
        count = TOPIC_COUNTS.get(topic_key, 0)

    await call.message.answer(
        f"Тема изменена на <b>{title}</b>.\n"
        f"Слов в этой теме: <b>{count}</b>.\n"
        "Напиши /next, чтобы начать."
    )


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

    # Если это старый вопрос, игнорируем
    if state.current_word_id != word_id:
        await call.answer("Этот вопрос уже неактуален. Нажми /next.", show_alert=True)
        return

    word = WORDS_BY_ID.get(word_id)
    if not word:
        await call.answer("Слово не найдено.", show_alert=True)
        return

    if is_correct:
        state.correct += 1
        await call.answer("Верно!", show_alert=False)
        # Просто даем следующую карточку
        await send_next_question(call.message, call.from_user.id)
    else:
        state.wrong += 1
        await call.answer("Неверно.", show_alert=False)

        # Показываем правильный ответ
        text = (
            "❌ Неверно.\n"
            "Правильный ответ:\n"
            f"🇩🇪 <b>{word.de}</b> [{word.tr}]\n"
            f"🇷🇺 <b>{word.ru}</b>"
        )
        await call.message.answer(text)
        # И сразу новая карточка
        await send_next_question(call.message, call.from_user.id)


# ============================================================
# Точка входа
# ============================================================

async def main() -> None:
    load_words()
    print(f"Loaded {TOTAL_WORDS} words from {WORDS_FILE}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
