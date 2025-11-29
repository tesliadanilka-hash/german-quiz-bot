import asyncio
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# ==========================
# НАСТРОЙКИ БОТА
# ==========================

# ВСТАВЬ СВОЙ ТОКЕН ОТ BOTFATHER
TOKEN = "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE"

# ID администратора, которому будут приходить запросы на доступ
# Узнать можно, например, через @userinfobot
ADMIN_ID = 5319848687  # ЗАМЕНИ НА СВОЙ TELEGRAM ID

# Файл со списком пользователей, у которых есть доступ
ALLOWED_USERS_FILE = "allowed_users.txt"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Типы
Word = Dict[str, Any]
GrammarRule = Dict[str, Any]

# ==========================
# ТЕМЫ ДЛЯ СЛОВ
# ==========================

TOPIC_ALL = "Все темы (перемешку)"

TOPIC_GREETINGS = "Приветствия и базовые фразы"
TOPIC_PERSONAL = "Личные данные и знакомство"
TOPIC_PEOPLE = "Люди и внешность"
TOPIC_FAMILY = "Семья"
TOPIC_HOME = "Дом"
TOPIC_FOOD = "Еда и продукты"
TOPIC_TIME = "Время и дни недели"
TOPIC_CITY = "Город и транспорт"
TOPIC_SCHOOL = "Учеба и школа"
TOPIC_SHOPPING = "Покупки и магазины"
TOPIC_HEALTH = "Здоровье и самочувствие"
TOPIC_JOBS = "Работа и профессии"
TOPIC_HOBBY = "Хобби и свободное время"
TOPIC_WEATHER = "Погода и природа"
TOPIC_ANIMALS = "Животные"
TOPIC_HOUSEHOLD = "Быт и дом"
TOPIC_VERBS = "Глаголы"
TOPIC_ADJECTIVES = "Прилагательные"
TOPIC_ADVERBS = "Наречия"
TOPIC_PREPOSITIONS = "Предлоги"
TOPIC_COLORS = "Цвета"
TOPIC_EMOTIONS = "Эмоции"
TOPIC_OBJECTS = "Предметы и техника"

# Внутренняя "общая" тема словаря
TOPIC_DICT = "Словарь"

# Темы, которые будут отображаться в меню /themes
ALL_TOPICS = [
    TOPIC_GREETINGS,
    TOPIC_PERSONAL,
    TOPIC_PEOPLE,
    TOPIC_FAMILY,
    TOPIC_HOME,
    TOPIC_FOOD,
    TOPIC_TIME,
    TOPIC_CITY,
    TOPIC_SCHOOL,
    TOPIC_SHOPPING,
    TOPIC_HEALTH,
    TOPIC_JOBS,
    TOPIC_HOBBY,
    TOPIC_WEATHER,
    TOPIC_ANIMALS,
    TOPIC_HOUSEHOLD,
    TOPIC_VERBS,
    TOPIC_ADJECTIVES,
    TOPIC_ADVERBS,
    TOPIC_PREPOSITIONS,
    TOPIC_COLORS,
    TOPIC_EMOTIONS,
    TOPIC_OBJECTS,
]

# Маппинг названий тем из файла words.json в константы
TOPIC_NAME_MAP: Dict[str, str] = {
    "Приветствия и базовые фразы": TOPIC_GREETINGS,
    "Личные данные и знакомство": TOPIC_PERSONAL,
    "Люди и внешность": TOPIC_PEOPLE,
    "Семья": TOPIC_FAMILY,
    "Дом": TOPIC_HOME,
    "Еда и продукты": TOPIC_FOOD,
    "Время и дни недели": TOPIC_TIME,
    "Город и транспорт": TOPIC_CITY,
    "Учеба и школа": TOPIC_SCHOOL,
    "Покупки и магазины": TOPIC_SHOPPING,
    "Здоровье и самочувствие": TOPIC_HEALTH,
    "Работа и профессии": TOPIC_JOBS,
    "Хобби и свободное время": TOPIC_HOBBY,
    "Погода и природа": TOPIC_WEATHER,
    "Животные": TOPIC_ANIMALS,
    "Быт и дом": TOPIC_HOUSEHOLD,
    "Глаголы": TOPIC_VERBS,
    "Прилагательные": TOPIC_ADJECTIVES,
    "Наречия": TOPIC_ADVERBS,
    "Предлоги": TOPIC_PREPOSITIONS,
    "Цвета": TOPIC_COLORS,
    "Эмоции": TOPIC_EMOTIONS,
    "Предметы и техника": TOPIC_OBJECTS,
}

# ==========================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ==========================

# Состояние по словам
user_state: Dict[int, Dict[str, Any]] = defaultdict(
    lambda: {
        "mode": "de_ru",        # "de_ru" или "ru_de"
        "topic": TOPIC_ALL,     # текущая тема
        "correct": 0,
        "wrong": 0,
        "remaining": None,      # список id еще не показанных слов в текущем круге
    }
)

# Состояние по грамматике: grammar_state[user_id][rule_id] = {"correct": X, "wrong": Y, "q_index": N}
grammar_state: Dict[int, Dict[int, Dict[str, int]]] = defaultdict(dict)

# Список разрешенных пользователей
allowed_users: set[int] = set()

# Слова
WORDS: List[Word] = []
WORDS_BY_TOPIC: Dict[str, List[int]] = defaultdict(list)

# ==========================
# ГРАММАТИКА - ЗАГОТОВКА
# ==========================
# Сюда потом вставишь свой список GRAMMAR_RULES по примеру:
# GRAMMAR_RULES = [
#   {
#     "id": 1,
#     "level": "A1",
#     "title": "Название темы",
#     "description": "Объяснение правила",
#     "examples": [{"de": "Пример", "ru": "Перевод"}],
#     "questions": [
#         {
#             "prompt": "Текст подсказки",
#             "question_de": "Вопрос на немецком",
#             "options": ["вариант 1", "вариант 2", "вариант 3", "вариант 4"],
#             "correct": 0,
#             "answer_de": "Правильное предложение",
#             "answer_ru": "Перевод",
#         },
#     ],
#   },
# ]

GRAMMAR_RULES: List[GrammarRule] = [
    # ВСТАВЬ СЮДА СВОИ ПРАВИЛА ГРАММАТИКИ
]

# ==========================
# ФУНКЦИИ РАБОТЫ С ДОСТУПОМ
# ==========================

def load_allowed_users() -> None:
    """Загружаем список разрешенных пользователей из файла."""
    global allowed_users
    try:
        ids: List[int] = []
        with open(ALLOWED_USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.append(int(line))
                except ValueError:
                    continue
        allowed_users = set(ids)
        print(f"Загружено разрешенных пользователей: {len(allowed_users)}")
    except FileNotFoundError:
        allowed_users = set()
        print("Файл allowed_users.txt не найден, начинаем с пустого списка.")


def save_allowed_users() -> None:
    """Сохраняем список разрешенных пользователей в файл."""
    with open(ALLOWED_USERS_FILE, "w", encoding="utf-8") as f:
        for uid in sorted(allowed_users):
            f.write(str(uid) + "\n")
    print(f"Сохранено разрешенных пользователей: {len(allowed_users)}")

# ==========================
# ЗАГРУЗКА СЛОВ ИЗ words.json
# ==========================

def load_words(path: str = "words.json") -> None:
    """
    Загружаем слова из JSON файла words.json и заполняем WORDS и WORDS_BY_TOPIC.
    """

    global WORDS, WORDS_BY_TOPIC

    WORDS = []
    WORDS_BY_TOPIC = defaultdict(list)

    # Проверяем наличие файла
    file_path = Path(path)
    if not file_path.exists():
        print(f"Файл {path} не найден. Положи words.json рядом с bot.py")
        return

    # Читаем JSON
    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Функция для добавления одного слова
    def add_word(raw: Dict[str, Any], topic_raw: str) -> None:
        de = raw.get("de")
        tr = raw.get("tr")
        ru = raw.get("ru")

        if not de or not tr or not ru:
            print("Пропускаю запись без нужных полей:", raw)
            return

        topic_raw = (topic_raw or "").strip()

        # Если тема известна — используем её
        if topic_raw in ALL_TOPICS:
            topic = topic_raw
        else:
            print("Неизвестная тема в words.json, кладу в общий словарь:", repr(topic_raw))
            topic = TOPIC_DICT

        idx = len(WORDS)
        word: Word = {
            "id": idx,
            "de": de,
            "tr": tr,
            "ru": ru,
            "topic": topic,
        }

        WORDS.append(word)
        WORDS_BY_TOPIC[topic].append(idx)
        WORDS_BY_TOPIC[TOPIC_DICT].append(idx)

    # === Разбор 3 поддерживаемых форматов ===

    # Вариант 1: Плоский список слов
    if isinstance(data, list) and data and "de" in data[0]:
        for raw in data:
            topic_raw = raw.get("topic") or raw.get("theme") or ""
            add_word(raw, topic_raw)

    # Вариант 3: Список блоков тем
    elif isinstance(data, list) and data and "words" in data[0]:
        for block in data:
            topic_raw = block.get("topic") or ""
            words_list = block.get("words", [])
            for raw in words_list:
                add_word(raw, topic_raw)

    # Вариант 2: Объект с ключом topics
    elif isinstance(data, dict) and "topics" in data:
        for block in data["topics"]:
            topic_raw = block.get("topic") or ""
            words_list = block.get("words", [])
            for raw in words_list:
                add_word(raw, topic_raw)

    else:
        print("Непонятный формат words.json")
        return

    # Создаем виртуальную тему
    WORDS_BY_TOPIC[TOPIC_ALL] = list(range(len(WORDS)))

    print(f"Загружено слов: {len(WORDS)}")
    for topic in ALL_TOPICS:
        count = len(WORDS_BY_TOPIC.get(topic, []))
        print(f"Тема '{topic}': {count} слов")


# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СЛОВ
# ==========================

def get_user_words(uid: int) -> List[int]:
    state = user_state[uid]
    topic = state["topic"]
    if topic not in WORDS_BY_TOPIC or topic == TOPIC_ALL:
        return WORDS_BY_TOPIC.get(TOPIC_ALL, [])
    return WORDS_BY_TOPIC[topic]


def reset_progress(uid: int) -> None:
    """Сброс статистики и новый круг слов по текущей теме."""
    state = user_state[uid]
    state["correct"] = 0
    state["wrong"] = 0
    ids = get_user_words(uid)
    ids = ids.copy()
    random.shuffle(ids)
    state["remaining"] = ids


def build_options(word_ids: List[int], correct_id: int, mode: str) -> InlineKeyboardMarkup:
    """
    Строим клавиатуру с 4 вариантами ответа.
    В callback_data кодируем:
    ans|<word_id>|<mode>|<is_correct>
    """
    pool = set(word_ids)
    pool.discard(correct_id)
    wrong_ids = random.sample(list(pool), k=3) if len(pool) >= 3 else list(pool)

    all_ids = wrong_ids + [correct_id]
    random.shuffle(all_ids)

    buttons = []
    for wid in all_ids:
        w = WORDS[wid]
        if mode == "de_ru":
            text = w["ru"]
        else:
            text = f'{w["de"]} [{w["tr"]}]'
        cb_data = f"ans|{correct_id}|{mode}|{1 if wid == correct_id else 0}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=cb_data)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_new_word(user_id: int, chat_id: int) -> None:
    """
    Отправляем пользователю новое слово.
    Слово выбирается из списка remaining и удаляется из него.
    """
    state = user_state[user_id]
    if state["remaining"] is None:
        reset_progress(user_id)

    if not state["remaining"]:
        await bot.send_message(
            chat_id,
            "В этой теме пока нет слов или ты уже прошел все слова.\n"
            "Выбери другую тему через /themes или начни заново через /next."
        )
        return

    word_id = state["remaining"].pop()
    w = WORDS[word_id]
    mode = state["mode"]
    word_pool = get_user_words(user_id)

    if mode == "de_ru":
        text = f'🇩🇪 Слово: {w["de"]} [{w["tr"]}]\nВыбери правильный перевод на русский.'
    else:
        text = f'🇷🇺 Слово: {w["ru"]}\nВыбери правильный перевод на немецкий.'

    kb = build_options(word_pool, word_id, mode)
    await bot.send_message(chat_id, text, reply_markup=kb)


async def resend_same_word(chat_id: int, word_id: int, mode: str, uid: int) -> None:
    """
    Переотправляем то же самое слово после неправильного ответа.
    Список remaining не трогаем, чтобы слово не повторялось как новое.
    """
    w = WORDS[word_id]
    word_pool = get_user_words(uid)

    if mode == "de_ru":
        text = (
            f'❌ Неправильно.\n'
            f'Попробуй еще раз.\n\n'
            f'🇩🇪 Слово: {w["de"]} [{w["tr"]}]\nВыбери правильный перевод на русский.'
        )
    else:
        text = (
            f'❌ Неправильно.\n'
            f'Попробуй еще раз.\n\n'
            f'🇷🇺 Слово: {w["ru"]}\nВыбери правильный перевод на немецкий.'
        )

    kb = build_options(word_pool, word_id, mode)
    await bot.send_message(chat_id, text, reply_markup=kb)

# ==========================
# КЛАВИАТУРЫ
# ==========================

def build_themes_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for topic in ALL_TOPICS:
        count = len(WORDS_BY_TOPIC.get(topic, []))
        text = f"{topic} ({count})"
        cb = f"topic|{topic}"
        rows.append([InlineKeyboardButton(text=text, callback_data=cb)])

    rows.insert(
        0,
        [InlineKeyboardButton(
            text=f"{TOPIC_ALL} ({len(WORDS)})",
            callback_data=f"topic|{TOPIC_ALL}",
        )],
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇩🇪 → 🇷🇺 Немецкое слово",
                    callback_data="mode|de_ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇷🇺 → 🇩🇪 Русское слово",
                    callback_data="mode|ru_de",
                )
            ],
        ]
    )


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧠 Тренировать слова",
                    callback_data="menu_words",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📘 Грамматика",
                    callback_data="menu_grammar",
                )
            ],
        ]
    )


def build_grammar_keyboard() -> InlineKeyboardMarkup:
    if not GRAMMAR_RULES:
        return InlineKeyboardMarkup(inline_keyboard=[])
    rows = []
    for rule in GRAMMAR_RULES:
        text = f'{rule["level"]}: {rule["title"]}'
        cb = f'gram|{rule["id"]}'
        rows.append([InlineKeyboardButton(text=text, callback_data=cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ДЛЯ ГРАММАТИКИ
# ==========================

def get_grammar_rule_by_id(rule_id: int) -> Optional[GrammarRule]:
    for rule in GRAMMAR_RULES:
        if rule["id"] == rule_id:
            return rule
    return None


def build_grammar_explanation_text(rule: GrammarRule) -> str:
    lines: List[str] = []
    lines.append(f'📘 Уровень {rule["level"]}')
    lines.append(f'Тема: {rule["title"]}\n')
    lines.append(rule["description"])
    lines.append("\nПримеры:\n")
    for ex in rule["examples"]:
        lines.append(f'{ex["de"]}\n{ex["ru"]}\n')
    lines.append("Сейчас будут вопросы по этой теме. Выбирай один правильный ответ из четырех.")
    return "\n".join(lines)


def build_grammar_question_text(rule: GrammarRule, q_index: int) -> str:
    question = rule["questions"][q_index]
    num = q_index + 1
    text = (
        f'📗 Упражнение {num} по теме: {rule["title"]}\n\n'
        f'{question["prompt"]}\n\n'
        f'{question["question_de"]}'
    )
    return text


def build_grammar_question_keyboard(rule_id: int, q_index: int) -> InlineKeyboardMarkup:
    rule = get_grammar_rule_by_id(rule_id)
    if rule is None:
        return InlineKeyboardMarkup(inline_keyboard=[])
    question = rule["questions"][q_index]
    buttons = []
    for idx, option in enumerate(question["options"]):
        cb_data = f"gramq|{rule_id}|{q_index}|{idx}"
        buttons.append([InlineKeyboardButton(text=option, callback_data=cb_data)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_grammar_question(chat_id: int, rule_id: int, q_index: int) -> None:
    rule = get_grammar_rule_by_id(rule_id)
    if rule is None:
        return
    if q_index < 0 or q_index >= len(rule["questions"]):
        await bot.send_message(chat_id, "Вопросы по этой теме закончились.")
        return
    text = build_grammar_question_text(rule, q_index)
    kb = build_grammar_question_keyboard(rule_id, q_index)
    await bot.send_message(chat_id, text, reply_markup=kb)

# ==========================
# ХЕНДЛЕРЫ КОМАНД
# ==========================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id

    # Если нет доступа - показываем описание бота и просим запросить доступ
    if uid != ADMIN_ID and uid not in allowed_users:
        text = (
            "🎓 Willkommen. Добро пожаловать в закрытого бота по немецкому языку.\n\n"
            "Этот бот помогает:\n"
            "• Учить слова по темам\n"
            "• Тренировать перевод 🇩🇪 ↔ 🇷🇺 с вариантами ответа\n"
            "• Работать с базовой грамматикой\n\n"
            "Доступ к боту ограничен.\n\n"
            "Чтобы получить доступ:\n"
            "1️⃣ Нажми команду /access\n"
            "2️⃣ Запрос уйдет администратору\n"
            "3️⃣ После одобрения ты получишь сообщение о доступе и инструкции по использованию бота."
        )
        await message.answer(text)
        return

    # Есть доступ - показываем полную информацию и меню
    total_words = len(WORDS)
    used_topics = {w["topic"] for w in WORDS}
    total_topics = len(used_topics)

    text = (
        "🎓 *Willkommen. Добро пожаловать в бота по немецкому языку*\n\n"
        "Этот бот помогает учить немецкий язык через слова и грамматику.\n\n"
        "📚 Возможности бота:\n"
        "• Учить слова по темам\n"
        "• Тренировать перевод слов в режиме викторины\n"
        "• Отслеживать статистику правильных и неправильных ответов\n"
        "• Изучать грамматику с объяснениями и упражнениями\n\n"
        f"Сейчас в базе *{total_words}* слов.\n"
        f"Тем по словам: *{total_topics}*.\n\n"
        "⚙ Режимы тренировки слов:\n"
        "• 🇩🇪 → 🇷🇺 немецкое слово, нужно выбрать русский перевод\n"
        "• 🇷🇺 → 🇩🇪 русское слово, нужно выбрать немецкий вариант с транскрипцией\n\n"
        "📌 Основные команды:\n"
        "• /next - следующее слово в текущей теме\n"
        "• /themes - выбрать тему слов\n"
        "• /mode - выбрать направление перевода\n"
        "• /grammar - грамматика\n\n"
        "🧠 Правило тренировки:\n"
        "Если ответ неправильный, новое слово не дается,\n"
        "пока ты не ответишь правильно на текущее.\n"
        "После правильного ответа бот покажет полный перевод и транскрипцию.\n\n"
        "👇 Выбери действие в меню:"
    )

    kb = build_main_menu_keyboard()
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

    reset_progress(uid)


@dp.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if uid == ADMIN_ID or uid in allowed_users:
        await message.answer(
            "У тебя уже есть доступ к боту.\n"
            "Можешь пользоваться командами как обычно: /start, /themes, /next, /mode, /grammar."
        )
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Разрешить доступ",
                    callback_data=f"allow|{uid}"
                )
            ]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {message.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            txt,
            reply_markup=kb,
        )
        await message.answer(
            "Запрос на доступ отправлен администратору.\n"
            "После одобрения ты получишь сообщение с инструкциями."
        )
    except Exception:
        await message.answer(
            "Не получилось отправить запрос администратору.\n"
            "Попробуй позже."
        )


@dp.message(Command("next"))
async def cmd_next(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа. Напиши /access для запроса.")
        return

    state = user_state[uid]
    if state["remaining"] is not None and not state["remaining"]:
        reset_progress(uid)

    await send_new_word(uid, message.chat.id)


@dp.message(Command("themes"))
async def cmd_themes(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа. Напиши /access для запроса.")
        return

    kb = build_themes_keyboard()
    await message.answer("Выбери тему для изучения слов.", reply_markup=kb)


@dp.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа. Напиши /access для запроса.")
        return

    kb = build_mode_keyboard()
    await message.answer(
        "Выбери направление перевода для тренировки слов:",
        reply_markup=kb,
    )


@dp.message(Command("grammar"))
async def cmd_grammar(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа. Напиши /access для запроса.")
        return

    if not GRAMMAR_RULES:
        await message.answer(
            "Раздел грамматики пока не настроен.\n"
            "Добавь свои правила в список GRAMMAR_RULES в main.py."
        )
        return

    kb = build_grammar_keyboard()
    await message.answer("Выбери грамматическое правило:", reply_markup=kb)

# ==========================
# CALLBACK ХЕНДЛЕРЫ
# ==========================

@dp.callback_query(F.data.startswith("allow|"))
async def cb_allow_user(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return

    _, user_id_str = callback.data.split("|", maxsplit=1)
    user_id = int(user_id_str)

    allowed_users.add(user_id)
    save_allowed_users()

    await callback.answer("Доступ разрешен.")
    await callback.message.edit_text(
        f"✅ Доступ пользователю {user_id} разрешен."
    )

    # После одобрения даем пользователю полные инструкции
    try:
        text = (
            "✅ Доступ к боту одобрен.\n\n"
            "Теперь ты можешь использовать все функции бота.\n\n"
            "Что делает бот:\n"
            "• Тренирует слова по темам\n"
            "• Проверяет перевод слов в формате теста\n"
            "• Показывает статистику по теме\n"
            "• Позволяет изучать грамматику\n\n"
            "Режимы тренировки слов:\n"
            "• 🇩🇪 → 🇷🇺 немецкое слово, выбираешь русский перевод\n"
            "• 🇷🇺 → 🇩🇪 русское слово, выбираешь немецкий вариант с транскрипцией\n\n"
            "Основные команды:\n"
            "• /start - информация о боте и главное меню\n"
            "• /themes - выбор темы слов\n"
            "• /mode - выбор направления перевода\n"
            "• /next - следующее слово в текущей теме\n"
            "• /grammar - грамматика\n\n"
            "Важно:\n"
            "Если ответ неправильный, новое слово не дается.\n"
            "Нужно ответить правильно на текущее слово.\n"
            "После правильного ответа бот покажет полный перевод с транскрипцией.\n"
        )
        await bot.send_message(user_id, text)
    except Exception:
        pass


@dp.callback_query(F.data == "menu_words")
async def cb_menu_words(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    reset_progress(uid)
    await callback.message.answer(
        "🧠 Режим тренировки слов.\n"
        "Я покажу слово и 4 варианта ответа.\n"
        "Если ответ неправильный, то новое слово не появится,\n"
        "пока ты не ответишь правильно на текущее слово.\n\n"
        "После правильного ответа ты увидишь полный ответ\n"
        "(немецкое слово, транскрипция и перевод),\n"
        "а затем бот покажет следующее слово."
    )
    await send_new_word(uid, callback.message.chat.id)


@dp.callback_query(F.data == "menu_grammar")
async def cb_menu_grammar(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()

    if not GRAMMAR_RULES:
        await callback.message.answer(
            "Раздел грамматики пока не настроен.\n"
            "Добавь свои правила в список GRAMMAR_RULES в main.py."
        )
        return

    kb = build_grammar_keyboard()
    await callback.message.answer("Выбери грамматическое правило:", reply_markup=kb)


@dp.callback_query(F.data.startswith("mode|"))
async def cb_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, mode = callback.data.split("|", maxsplit=1)
    user_state[uid]["mode"] = mode
    if mode == "de_ru":
        txt = "Режим установлен: 🇩🇪 → 🇷🇺. Буду показывать немецкое слово, а ты выбирай русский перевод."
    else:
        txt = "Режим установлен: 🇷🇺 → 🇩🇪. Буду показывать русское слово, а ты выбирай немецкий вариант с транскрипцией."
    await callback.answer("Режим обновлен.")
    try:
        await callback.message.edit_text(txt)
    except Exception:
        await callback.message.answer(txt)


@dp.callback_query(F.data.startswith("topic|"))
async def cb_topic(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, topic = callback.data.split("|", maxsplit=1)
    user_state[uid]["topic"] = topic

    reset_progress(uid)
    count = len(WORDS_BY_TOPIC.get(topic, []))

    await callback.answer("Тема выбрана.")
    await callback.message.edit_text(f"Тема установлена: {topic}.\nСлов в теме: {count}.")
    await send_new_word(uid, callback.message.chat.id)


@dp.callback_query(F.data.startswith("ans|"))
async def cb_answer(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
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

        # Показываем полный правильный ответ
        if mode == "de_ru":
            text = (
                f'✅ Правильно.\n\n'
                f'{w["de"]} [{w["tr"]}] - {w["ru"]}'
            )
        else:
            text = (
                f'✅ Правильно.\n\n'
                f'{w["ru"]} - {w["de"]} [{w["tr"]}]'
            )

        finished_now = not state["remaining"]

        if finished_now:
            text += (
                "\n\nТы прошел все слова в этой теме.\n"
                f'✅ Правильных ответов: {state["correct"]}\n'
                f'❌ Неправильных ответов: {state["wrong"]}\n\n'
                "Чтобы начать круг заново, набери /next или выбери другую тему через /themes."
            )

        try:
            await callback.message.edit_text(text)
        except Exception:
            await callback.message.answer(text)

        if not finished_now:
            await send_new_word(uid, callback.message.chat.id)

    else:
        state["wrong"] += 1
        # Не даем новое слово, пока не ответит правильно
        # Переотправляем это же слово с новыми вариантами
        try:
            await callback.message.edit_text("❌ Неправильно. Сейчас повторим это слово.")
        except Exception:
            await callback.message.answer("❌ Неправильно. Сейчас повторим это слово.")
        await resend_same_word(callback.message.chat.id, word_id, mode, uid)


@dp.callback_query(F.data.startswith("gram|"))
async def cb_grammar_rule(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id_str = callback.data.split("|", maxsplit=1)
    rule_id = int(rule_id_str)

    rule = get_grammar_rule_by_id(rule_id)
    if rule is None:
        await callback.answer("Правило не найдено.", show_alert=True)
        return

    grammar_state[uid][rule_id] = {"correct": 0, "wrong": 0, "q_index": 0}

    text = build_grammar_explanation_text(rule)
    await callback.message.answer(text)

    await callback.answer()
    await send_grammar_question(callback.message.chat.id, rule_id, 0)


@dp.callback_query(F.data.startswith("gramq|"))
async def cb_grammar_question(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id_str, q_index_str, chosen_idx_str = callback.data.split("|")
    rule_id = int(rule_id_str)
    q_index = int(q_index_str)
    chosen_idx = int(chosen_idx_str)

    rule = get_grammar_rule_by_id(rule_id)
    if rule is None:
        await callback.answer("Правило не найдено.", show_alert=True)
        return

    questions = rule["questions"]
    if q_index < 0 or q_index >= len(questions):
        await callback.answer("Вопросы по этой теме закончились.", show_alert=True)
        return

    question = questions[q_index]
    correct_idx = question["correct"]
    is_correct = chosen_idx == correct_idx

    user_rule_state = grammar_state[uid].setdefault(rule_id, {"correct": 0, "wrong": 0, "q_index": 0})

    if is_correct:
        user_rule_state["correct"] += 1
        result_text = "✅ Правильно."
    else:
        user_rule_state["wrong"] += 1
        result_text = "❌ Неправильно."

    answer_de = question["answer_de"]
    answer_ru = question["answer_ru"]

    text = (
        f"{result_text}\n\n"
        f"Правильный ответ:\n"
        f"{answer_de}\n{answer_ru}"
    )

    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)

    await callback.answer()

    next_index = q_index + 1
    user_rule_state["q_index"] = next_index

    if next_index >= len(questions):
        total_correct = user_rule_state["correct"]
        total_wrong = user_rule_state["wrong"]
        summary = (
            f"Ты прошел все упражнения по теме: {rule['title']}.\n\n"
            f"✅ Правильных ответов: {total_correct}\n"
            f'❌ Неправильных ответов: {total_wrong}\n\n'
            "Можешь выбрать другую тему через /grammar или повторить эту же тему."
        )
        await callback.message.answer(summary)
        return

    await send_grammar_question(callback.message.chat.id, rule_id, next_index)

# ==========================
# ЗАПУСК БОТА
# ==========================

async def main() -> None:
    load_allowed_users()
    load_words("words.json")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())








