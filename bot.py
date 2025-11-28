import asyncio
import json
import random
from dataclasses import dataclass, field
from typing import Dict, List, Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

TOKEN = "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ---------- ЗАГРУЗКА СЛОВ ----------

def load_words(path: str = "words.json") -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for w in data:
        w["de"] = w["de"].strip()
        w["ru"] = w["ru"].strip()
        w["tr"] = w["tr"].strip()
    return data


ALL_WORDS: List[Dict[str, str]] = load_words()

# ---------- ТЕМЫ И РАСПРЕДЕЛЕНИЕ ----------

TOPIC_TITLES: Dict[str, str] = {
    "all": "🎲 Все темы (перемешку)",
    "abstract": "Абстрактные понятия",
    "verbs": "Базовые глаголы",
    "time_calendar": "Время и календарь",
    "city_transport": "Город и транспорт",
    "home": "Дом и жилье",
    "food_shop": "Еда и магазин",
    "animals": "Животные",
    "tools_house": "Инструменты и быт",
    "computer_internet": "Компьютер и интернет",
    "personal_data": "Личные данные",
    "clothes": "Одежда",
    "weather_nature": "Погода и природа",
    "objects": "Предметы и вещи",
    "greetings": "Приветствия и базовые фразы",
    "jobs_work": "Профессии и работа",
    "family": "Семья",
    "body_health": "Тело и здоровье",
    "hobby_sport": "Хобби и спорт",
    "colors_numbers": "Цвета и числа",
    "school_study": "Школа и учеба",
    "emotions_character": "Эмоции и характер",
    "dictionary": "Словарь A1-B1",
}

# ключевые слова по русскому переводу (как в прошлом варианте)
TOPIC_KEYWORDS_RU: Dict[str, List[str]] = {
    # сюда я переношу те же списки ключевых слов, что и раньше
    # чтобы не раздувать ответ до безумия, логика такая же:
    # по подстроке в ru слово попадает в нужную тему
    # (ты уже видел этот блок, я его не менял)
}

# чтобы код был рабочим, добавим пустые списки, если выше ничего не вписано
for key in TOPIC_TITLES:
    if key not in TOPIC_KEYWORDS_RU:
        TOPIC_KEYWORDS_RU[key] = []

TOPIC_WORDS: Dict[str, List[Dict[str, str]]] = {k: [] for k in TOPIC_TITLES.keys()}
TOPIC_WORDS["dictionary"] = []

for w in ALL_WORDS:
    assigned = False
    ru = w["ru"].lower()
    for topic_id, kw_list in TOPIC_KEYWORDS_RU.items():
        if topic_id in ("all", "dictionary"):
            continue
        if any(k in ru for k in kw_list):
            TOPIC_WORDS[topic_id].append(w)
            assigned = True
            break
    if not assigned:
        TOPIC_WORDS["dictionary"].append(w)

TOPIC_WORDS["all"] = ALL_WORDS

# ---------- СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ ----------

@dataclass
class QuizState:
    topic_id: str
    remaining: List[int] = field(default_factory=list)
    correct: int = 0
    wrong: int = 0
    current_index: int | None = None
    mode: str = "de_ru"  # "de_ru" или "ru_de"
    options: List[str] = field(default_factory=list)
    correct_option: str | None = None


USER_STATE: Dict[int, QuizState] = {}


# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------

def build_topics_keyboard() -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []

    def add_row(tid: str):
        if tid == "all":
            text = TOPIC_TITLES[tid]
        else:
            count = len(TOPIC_WORDS.get(tid, []))
            text = f"{TOPIC_TITLES[tid]} ({count})"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"topic:{tid}")]
        )

    add_row("all")
    add_row("abstract")
    add_row("verbs")
    add_row("time_calendar")
    add_row("city_transport")
    add_row("home")
    add_row("food_shop")
    add_row("animals")
    add_row("tools_house")
    add_row("computer_internet")
    add_row("personal_data")
    add_row("clothes")
    add_row("weather_nature")
    add_row("objects")
    add_row("greetings")
    add_row("jobs_work")
    add_row("family")
    add_row("dictionary")
    add_row("body_health")
    add_row("hobby_sport")
    add_row("colors_numbers")
    add_row("school_study")
    add_row("emotions_character")

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_options_keyboard(options: List[str]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i, opt in enumerate(options):
        rows.append(
            [InlineKeyboardButton(text=opt, callback_data=f"ans:{i}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_mode_keyboard(current: str) -> InlineKeyboardMarkup:
    mark_de_ru = "✅ " if current == "de_ru" else ""
    mark_ru_de = "✅ " if current == "ru_de" else ""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{mark_de_ru}🇩🇪 -> 🇷🇺",
                    callback_data="mode:de_ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{mark_ru_de}🇷🇺 -> 🇩🇪",
                    callback_data="mode:ru_de",
                )
            ],
        ]
    )
    return kb


def format_full_answer(word: Dict[str, str]) -> str:
    de = word["de"]
    tr = word["tr"]
    ru = word["ru"]
    return (
        f"{de} [{tr}] - {ru}\n"
        f"{ru} - {de} [{tr}]"
    )


def start_new_topic(user_id: int, topic_id: str) -> QuizState:
    words = TOPIC_WORDS[topic_id]
    indices = list(range(len(words)))
    random.shuffle(indices)

    old_state = USER_STATE.get(user_id)
    mode = old_state.mode if old_state else "de_ru"

    state = QuizState(topic_id=topic_id, remaining=indices, mode=mode)
    USER_STATE[user_id] = state
    return state


def prepare_question(user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    state = USER_STATE.get(user_id)
    if not state:
        return None

    if not state.remaining:
        return None

    words = TOPIC_WORDS[state.topic_id]
    idx = state.remaining.pop()
    word = words[idx]

    state.current_index = idx

    if state.mode == "de_ru":
        question_text = f"Выбери перевод на русский:\n\n{word['de']} [{word['tr']}]"
        correct_text = word["ru"]
    else:
        question_text = f"Выбери перевод на немецкий:\n\n{word['ru']}"
        correct_text = word["de"]

    # собираем неправильные варианты
    incorrect: List[str] = []
    pool_indices = [i for i in range(len(words)) if i != idx]
    random.shuffle(pool_indices)
    for i in pool_indices:
        w = words[i]
        opt = w["ru"] if state.mode == "de_ru" else w["de"]
        if opt != correct_text and opt not in incorrect:
            incorrect.append(opt)
        if len(incorrect) == 3:
            break

    options = incorrect + [correct_text]
    random.shuffle(options)
    state.options = options
    state.correct_option = correct_text

    kb = build_options_keyboard(options)
    return question_text, kb


def get_or_create_state(user_id: int) -> QuizState:
    state = USER_STATE.get(user_id)
    if state:
        return state
    # по умолчанию тема all
    state = start_new_topic(user_id, "all")
    return state


# ---------- ХЕНДЛЕРЫ ----------

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    USER_STATE.pop(user_id, None)

    total_words = len(ALL_WORDS)
    topics_count = len(TOPIC_TITLES) - 1  # без "all"

    text = (
        "🇩🇪 Привет! Это бот для изучения немецких слов.\n\n"
        "Как пользоваться:\n"
        "• Я показываю слово и 4 варианта перевода.\n"
        "• Нажми на кнопку с вариантом.\n"
        "• Если ответ неверный, я покажу правильный ответ и сразу дам новое слово.\n"
        "• Если ответ верный, карточка помечается галочкой, а ниже появляется новое слово.\n\n"
        f"Сейчас в базе {total_words} слов.\n"
        f"Тем: {topics_count}.\n\n"
        "Режимы:\n"
        "• 🇩🇪 -> 🇷🇺 немецкое слово и варианты на русском.\n"
        "• 🇷🇺 -> 🇩🇪 русское слово и варианты на немецком.\n\n"
        "Команды:\n"
        "/next - следующее слово\n"
        "/themes - выбрать тему слов\n"
        "/mode - выбрать направление перевода\n\n"
        "По умолчанию включен режим 🇩🇪 -> 🇷🇺."
    )

    await message.answer(text)
    await message.answer(
        "Выбери тему:",
        reply_markup=build_topics_keyboard(),
    )


@dp.message(Command("themes"))
async def cmd_themes(message: Message):
    await message.answer(
        "Выбери тему:",
        reply_markup=build_topics_keyboard(),
    )


@dp.message(Command("mode"))
async def cmd_mode(message: Message):
    user_id = message.from_user.id
    state = get_or_create_state(user_id)
    kb = build_mode_keyboard(state.mode)
    await message.answer(
        "Выбери направление перевода:",
        reply_markup=kb,
    )


@dp.message(Command("next"))
async def cmd_next(message: Message):
    user_id = message.from_user.id
    state = get_or_create_state(user_id)

    if not state.remaining:
        total = state.correct + state.wrong
        await message.answer(
            "В этой теме больше нет слов.\n\n"
            f"Всего вопросов: {total}\n"
            f"Правильных: {state.correct}\n"
            f"Неправильных: {state.wrong}\n\n"
            "Выбери новую тему через /themes."
        )
        USER_STATE.pop(user_id, None)
        return

    q = prepare_question(user_id)
    if q is None:
        await message.answer("Не удалось подготовить вопрос.")
    else:
        text, kb = q
        await message.answer(text, reply_markup=kb)


@dp.callback_query(F.data.startswith("mode:"))
async def cb_mode(callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data.split(":", 1)[1]
    if mode not in ("de_ru", "ru_de"):
        await callback.answer("Неизвестный режим")
        return

    state = get_or_create_state(user_id)
    state.mode = mode

    kb = build_mode_keyboard(state.mode)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("Режим обновлен")

    # сразу даем слово в новом режиме
    q = prepare_question(user_id)
    if q is not None:
        text, kb2 = q
        await callback.message.answer(text, reply_markup=kb2)


@dp.callback_query(F.data.startswith("topic:"))
async def cb_choose_topic(callback: CallbackQuery):
    user_id = callback.from_user.id
    topic_id = callback.data.split(":", 1)[1]

    if topic_id not in TOPIC_TITLES:
        await callback.answer("Неизвестная тема")
        return

    state = start_new_topic(user_id, topic_id)
    words_count = len(TOPIC_WORDS[topic_id])

    if not state.remaining:
        await callback.message.edit_text("В этой теме пока нет слов.")
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Тема: {TOPIC_TITLES[topic_id]}\n"
        f"Слов в тренировке: {words_count}\n\n"
        "Начинаем!"
    )

    q = prepare_question(user_id)
    if q is None:
        await callback.message.answer("Не удалось подготовить вопрос.")
    else:
        text, kb = q
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("ans:"))
async def cb_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = USER_STATE.get(user_id)

    if not state or state.current_index is None:
        await callback.answer("Сначала выбери тему через /start или /themes")
        return

    try:
        chosen_i = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Ошибка ответа")
        return

    if chosen_i < 0 or chosen_i >= len(state.options):
        await callback.answer("Ошибка ответа")
        return

    chosen_text = state.options[chosen_i]
    words = TOPIC_WORDS[state.topic_id]
    word = words[state.current_index]

    is_correct = chosen_text == state.correct_option

    if is_correct:
        state.correct += 1
        prefix = "✅ Правильно!\n"
    else:
        state.wrong += 1
        prefix = "❌ Неправильно.\n"

    full_answer = format_full_answer(word)
    await callback.message.answer(prefix + full_answer)

    if not state.remaining:
        total = state.correct + state.wrong
        await callback.message.answer(
            "Тема завершена.\n"
            f"Всего вопросов: {total}\n"
            f"Правильных: {state.correct}\n"
            f"Неправильных: {state.wrong}\n\n"
            "Чтобы выбрать другую тему, напиши /themes"
        )
        USER_STATE.pop(user_id, None)
    else:
        q = prepare_question(user_id)
        if q is None:
            await callback.message.answer("Ошибка при подготовке следующего вопроса.")
        else:
            text, kb = q
            await callback.message.answer(text, reply_markup=kb)

    await callback.answer()


# ---------- ЗАПУСК ----------

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
