import asyncio
import json
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from openai import OpenAI

# ==========================
# НАСТРОЙКИ БОТА
# ==========================

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
)

ADMIN_ID = 5319848687  # ЗАМЕНИ НА СВОЙ TELEGRAM ID

ALLOWED_USERS_FILE = "allowed_users.txt"
USER_STATE_FILE = "user_state.json"

if not TOKEN:
    raise RuntimeError(
        "Не найден токен бота. "
        "Проверь, что в настройках Render есть переменная окружения "
        "BOT_TOKEN (или TELEGRAM_TOKEN, TELEGRAM_BOT_TOKEN, TOKEN) "
        "и в ней записан токен от BotFather."
    )

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ==========================
# НАСТРОЙКИ ПРОВЕРКИ ПРЕДЛОЖЕНИЙ
# ==========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

AI_SYSTEM_PROMPT = (
    "Ты преподаватель немецкого языка. "
    "Твоя задача - проверять грамматику и правописание немецких предложений.\n"
    "Всегда отвечай строго в таком формате:\n\n"
    "Исправленный вариант:\n"
    "{здесь напиши исправленный вариант всего текста целиком}\n\n"
    "Ошибки:\n"
    "1) {кратко опиши первую ошибку, укажи фрагмент и как правильно}\n"
    "2) {вторая ошибка, если есть}\n"
    "Если ошибок нет, напиши:\n"
    "Исправленный вариант:\n"
    "{исходный текст}\n\n"
    "Ошибки:\n"
    "Ошибок не найдено. Предложение грамматически корректно."
)

# Типы
Word = Dict[str, Any]
GrammarRule = Dict[str, Any]

# ==========================
# ТЕМЫ ДЛЯ СЛОВ
# ==========================

# Внутренний ключ для режима "все слова вперемешку"
TOPIC_ALL = "ALL"

# ==========================
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ==========================

user_state: Dict[int, Dict[str, Any]] = defaultdict(
    lambda: {
        "mode": "de_ru",
        "topic": TOPIC_ALL,
        "correct": 0,
        "wrong": 0,
        "remaining": None,
        "check_mode": False,
        "topic_stats": {},
    }
)

grammar_state: Dict[int, Dict[int, Dict[str, int]]] = defaultdict(dict)

allowed_users: set[int] = set()

# Слова и индексы
WORDS: List[Word] = []

# Ключи WORDS_BY_TOPIC:
# TOPIC_ALL                                          -> все слова
# "A1|Приветствия и базовые фразы"                  -> все слова темы
# "A1|Приветствия и базовые фразы|Приветствия"      -> слова конкретной подтемы
WORDS_BY_TOPIC: Dict[str, List[int]] = defaultdict(list)

# Статистика для меню
LEVEL_COUNTS: Dict[str, int] = defaultdict(int)                     # "A1" -> 120
TOPIC_COUNTS: Dict[Tuple[str, str], int] = defaultdict(int)         # ("A1","Тема") -> 40
SUBTOPIC_COUNTS: Dict[Tuple[str, str, str], int] = defaultdict(int) # ("A1","Тема","Подтема") -> 15

# ==========================
# ГРАММАТИКА - ЗАГОТОВКА
# ==========================

GRAMMAR_RULES: List[GrammarRule] = [
    # Сюда можно добавить свои правила грамматики
]

# ==========================
# ФУНКЦИИ РАБОТЫ С ДОСТУПОМ
# ==========================

def load_allowed_users() -> None:
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
    with open(ALLOWED_USERS_FILE, "w", encoding="utf-8") as f:
        for uid in sorted(allowed_users):
            f.write(str(uid) + "\n")
    print(f"Сохранено разрешенных пользователей: {len(allowed_users)}")

# ==========================
# РАБОТА С СОСТОЯНИЕМ ПОЛЬЗОВАТЕЛЕЙ
# ==========================

def load_user_state() -> None:
    try:
        with open(USER_STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        count = 0
        for uid_str, state in raw.items():
            try:
                uid = int(uid_str)
            except ValueError:
                continue
            user_state[uid].update(state)
            count += 1

        print(f"Загружено состояний пользователей: {count}")
    except FileNotFoundError:
        print("Файл user_state.json не найден, начинаем с пустого состояния.")
    except Exception as e:
        print("Ошибка при загрузке состояний пользователей:", e)


def save_user_state() -> None:
    try:
        raw = {str(uid): state for uid, state in user_state.items()}
        with open(USER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"Состояние пользователей сохранено. Всего пользователей: {len(raw)}")
    except Exception as e:
        print("Ошибка при сохранении состояний пользователей:", e)

# ==========================
# ЗАГРУЗКА СЛОВ ИЗ words.json
# ==========================

def load_words(path: str = "words.json") -> None:
    """
    Ожидаемый формат:

    {
      "topics": [
        {
          "topic": "Приветствия и базовые фразы",
          "level": "A1",
          "subtopic": "Приветствия",
          "words": [
            { "de": "...", "tr": "...", "ru": "..." },
            ...
          ]
        },
        ...
      ]
    }
    """

    global WORDS, WORDS_BY_TOPIC, LEVEL_COUNTS, TOPIC_COUNTS, SUBTOPIC_COUNTS

    WORDS = []
    WORDS_BY_TOPIC = defaultdict(list)
    LEVEL_COUNTS = defaultdict(int)
    TOPIC_COUNTS = defaultdict(int)
    SUBTOPIC_COUNTS = defaultdict(int)

    file_path = Path(path)
    if not file_path.exists():
        print(f"Файл {path} не найден. Положи words.json рядом с bot.py")
        return

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    def add_word(
        raw: Dict[str, Any],
        level_raw: str,
        topic_raw: str,
        subtopic_raw: str,
    ) -> None:
        de = raw.get("de")
        tr = raw.get("tr")
        ru = raw.get("ru")

        if not de or not tr or not ru:
            print("Пропускаю запись без нужных полей:", raw)
            return

        level = (level_raw or "").strip() or "A1"
        topic = (topic_raw or "").strip() or "Без темы"
        subtopic = (subtopic_raw or "").strip() or "Общее"

        idx = len(WORDS)
        word: Word = {
            "id": idx,
            "de": de,
            "tr": tr,
            "ru": ru,
            "level": level,
            "topic": topic,
            "subtopic": subtopic,
        }

        WORDS.append(word)

        key_all = TOPIC_ALL
        key_topic = f"{level}|{topic}"
        key_subtopic = f"{level}|{topic}|{subtopic}"

        WORDS_BY_TOPIC[key_all].append(idx)
        WORDS_BY_TOPIC[key_topic].append(idx)
        WORDS_BY_TOPIC[key_subtopic].append(idx)

        LEVEL_COUNTS[level] += 1
        TOPIC_COUNTS[(level, topic)] += 1
        SUBTOPIC_COUNTS[(level, topic, subtopic)] += 1

    if isinstance(data, dict) and "topics" in data:
        for block in data["topics"]:
            level_raw = block.get("level") or ""
            topic_raw = block.get("topic") or ""
            subtopic_raw = block.get("subtopic") or ""
            for raw in block.get("words", []):
                add_word(raw, level_raw, topic_raw, subtopic_raw)

    elif isinstance(data, list) and data and isinstance(data[0], dict):
        for block in data:
            if "words" in block:
                level_raw = block.get("level") or ""
                topic_raw = block.get("topic") or ""
                subtopic_raw = block.get("subtopic") or ""
                for raw in block.get("words", []):
                    add_word(raw, level_raw, topic_raw, subtopic_raw)
            else:
                level_raw = block.get("level") or ""
                topic_raw = block.get("topic") or ""
                subtopic_raw = block.get("subtopic") or ""
                add_word(block, level_raw, topic_raw, subtopic_raw)
    else:
        print("Неизвестный формат words.json")
        return

    print(f"Загружено слов: {len(WORDS)}")
    for level in sorted(LEVEL_COUNTS):
        print(f"Уровень {level}: {LEVEL_COUNTS[level]} слов")
    print(f"Всего тем: {len(TOPIC_COUNTS)}, всего подтем: {len(SUBTOPIC_COUNTS)}")

# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ТЕМ
# ==========================

def get_levels() -> List[str]:
    return sorted(LEVEL_COUNTS.keys())


def get_topics_for_level(level: str) -> List[str]:
    topics = [
        topic
        for (lvl, topic), count in TOPIC_COUNTS.items()
        if lvl == level and count > 0
    ]
    return sorted(set(topics))


def get_subtopics_for_level_topic(level: str, topic: str) -> List[str]:
    subs = [
        subtopic
        for (lvl, top, subtopic), count in SUBTOPIC_COUNTS.items()
        if lvl == level and top == topic and count > 0
    ]
    return sorted(set(subs))


def pretty_topic_name(topic_key: str) -> str:
    if not topic_key or topic_key == TOPIC_ALL:
        return "Все слова"
    parts = topic_key.split("|")
    if len(parts) == 3:
        level, topic, subtopic = parts
        return f"Уровень {level}: {topic} → {subtopic}"
    if len(parts) == 2:
        level, topic = parts
        return f"Уровень {level}: {topic}"
    return topic_key

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
    state = user_state[uid]
    state["correct"] = 0
    state["wrong"] = 0
    ids = get_user_words(uid)
    ids = ids.copy()
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
        if mode == "de_ru":
            text = w["ru"]
        else:
            text = f'{w["de"]} [{w["tr"]}]'
        cb_data = f"ans|{correct_id}|{mode}|{1 if wid == correct_id else 0}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=cb_data)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_new_word(user_id: int, chat_id: int) -> None:
    state = user_state[user_id]
    if state["remaining"] is None:
        reset_progress(user_id)

    if not state["remaining"]:
        await bot.send_message(
            chat_id,
            "В этой подборке пока нет слов или ты уже прошел все слова.\n"
            "Выбери уровень и тему через раздел Темы слов."
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
    w = WORDS[word_id]
    word_pool = get_user_words(uid)

    if mode == "de_ru":
        text = (
            "❌ Неправильно.\n"
            "Попробуй еще раз.\n\n"
            f'🇩🇪 Слово: {w["de"]} [{w["tr"]}]\nВыбери правильный перевод на русский.'
        )
    else:
        text = (
            "❌ Неправильно.\n"
            "Попробуй еще раз.\n\n"
            f'🇷🇺 Слово: {w["ru"]}\nВыбери правильный перевод на немецкий.'
        )

    kb = build_options(word_pool, word_id, mode)
    await bot.send_message(chat_id, text, reply_markup=kb)

# ==========================
# КЛАВИАТУРЫ
# ==========================

def build_themes_keyboard() -> InlineKeyboardMarkup:
    rows = []

    total_words = len(WORDS)
    rows.append(
        [
            InlineKeyboardButton(
                text=f"Все слова ({total_words})",
                callback_data="topic_all",
            )
        ]
    )

    for level in get_levels():
        count = LEVEL_COUNTS.get(level, 0)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Уровень {level} ({count})",
                    callback_data=f"level|{level}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_topics_keyboard_for_level(level: str) -> InlineKeyboardMarkup:
    rows = []
    for topic in get_topics_for_level(level):
        count = TOPIC_COUNTS.get((level, topic), 0)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{topic} ({count})",
                    callback_data=f"topic_select|{level}|{topic}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_subtopics_keyboard(level: str, topic: str) -> InlineKeyboardMarkup:
    rows = []
    for subtopic in get_subtopics_for_level_topic(level, topic):
        count = SUBTOPIC_COUNTS.get((level, topic, subtopic), 0)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{subtopic} ({count})",
                    callback_data=f"subtopic|{level}|{topic}|{subtopic}",
                )
            ]
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
                    text="📚 Темы слов",
                    callback_data="menu_themes",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📘 Грамматика",
                    callback_data="menu_grammar",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Проверка предложений",
                    callback_data="menu_check",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Моя статистика",
                    callback_data="menu_stats",
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
# СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ
# ==========================

def update_topic_stats(uid: int, topic: str, correct: int, wrong: int) -> None:
    total = correct + wrong
    if total <= 0:
        return

    accuracy = correct * 100.0 / total

    state = user_state[uid]
    topic_stats = state.setdefault("topic_stats", {})
    stats = topic_stats.get(topic, {
        "runs": 0,
        "best_accuracy": 0.0,
        "last_accuracy": 0.0,
        "total_correct": 0,
        "total_wrong": 0,
    })

    stats["runs"] += 1
    stats["last_accuracy"] = accuracy
    if accuracy > stats.get("best_accuracy", 0.0):
        stats["best_accuracy"] = accuracy
    stats["total_correct"] += correct
    stats["total_wrong"] += wrong

    topic_stats[topic] = stats
    save_user_state()


def build_user_stats_text(uid: int) -> str:
    state = user_state[uid]

    current_topic = state.get("topic", TOPIC_ALL)
    pretty_name = pretty_topic_name(current_topic)
    correct = state.get("correct", 0)
    wrong = state.get("wrong", 0)
    total = correct + wrong

    if total > 0:
        accuracy = correct * 100 / total
        accuracy_str = f"{accuracy:.1f}%"
        if accuracy >= 90:
            comment = "🔥 Отличный результат. Ты очень хорошо знаешь эту тему."
        elif accuracy >= 75:
            comment = "✅ Хороший уровень. Можно переходить дальше, но периодически повторяй."
        elif accuracy >= 60:
            comment = "⚠️ Неплохо, но стоит еще потренироваться в этой теме."
        else:
            comment = "📌 Рекомендую пройти тему еще раз с самого начала."
    else:
        accuracy_str = "Нет данных"
        comment = (
            "Пока нет ответов в этом круге. "
            "Начни тренировку слов и затем снова открой статистику."
        )

    total_words_in_topic = len(WORDS_BY_TOPIC.get(current_topic, []))

    lines: List[str] = []
    lines.append("📊 Твоя статистика по тренировкам слов:\n")
    lines.append(f"Текущая тема: {pretty_name}")
    lines.append(f"Слов в этой подборке: {total_words_in_topic}")
    lines.append("")
    lines.append(f"✅ Правильных ответов: {correct}")
    lines.append(f"❌ Неправильных ответов: {wrong}")
    lines.append(f"🎯 Точность: {accuracy_str}")
    lines.append("")
    lines.append(comment)
    lines.append("")
    lines.append("Статистика относится к текущему кругу слов в выбранной теме или подтеме.")
    lines.append("Когда круг заканчивается, результаты сохраняются в общую статистику по темам.")
    lines.append("")

    topic_stats = state.get("topic_stats", {})
    if topic_stats:
        lines.append("📚 Результаты по темам, которые ты уже проходил:\n")
        for topic, stats in topic_stats.items():
            runs = stats.get("runs", 0)
            best = stats.get("best_accuracy", 0.0)
            last = stats.get("last_accuracy", 0.0)
            nice = pretty_topic_name(topic)
            lines.append(
                f"• {nice}\n"
                f"  Проходов: {runs}\n"
                f"  Лучшая точность: {best:.1f}%\n"
                f"  Последний результат: {last:.1f}%\n"
            )
    else:
        lines.append("Пока нет завершенных кругов по темам.")

    return "\n".join(lines)

# ==========================
# ПРОВЕРКА ПРЕДЛОЖЕНИЙ
# ==========================

async def check_text_with_ai(text: str) -> str:
    if client is None:
        return (
            "Проверка предложений сейчас недоступна.\n"
            "Обратись к администратору."
        )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        answer = completion.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print("Ошибка при проверке предложения:", e)
        return "Произошла ошибка при проверке. Попробуй еще раз позже."

# ==========================
# ХЕНДЛЕРЫ КОМАНД
# ==========================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔓 Запросить доступ",
                        callback_data="req_access",
                    )
                ]
            ]
        )

        text = (
            "🎓 Willkommen. Добро пожаловать в закрытого бота по немецкому языку.\n\n"
            "Этот бот помогает тебе шаг за шагом улучшать немецкий через слова, темы, грамматику и проверку предложений.\n\n"
            "Доступ к боту ограничен. Нажми кнопку ниже, чтобы отправить запрос администратору."
        )
        await message.answer(text, reply_markup=kb)
        return

    total_words = len(WORDS)
    total_topics = len(TOPIC_COUNTS)
    total_subtopics = len(SUBTOPIC_COUNTS)

    text = (
        "🎓 Willkommen. Добро пожаловать в бота по немецкому языку.\n\n"
        "Этот бот помогает улучшать немецкий язык с помощью тренировок по словам, темам и простых упражнений по грамматике.\n\n"
        f"Сейчас в базе {total_words} слов.\n"
        f"Тем: {total_topics}, подтем: {total_subtopics}.\n\n"
        "Ниже ты видишь главное меню. Выбирай режим, и бот проведет тебя по шагам."
    )

    kb = build_main_menu_keyboard()
    await message.answer(text, reply_markup=kb)

    user_state[uid]["check_mode"] = False
    save_user_state()


@dp.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if uid == ADMIN_ID or uid in allowed_users:
        await message.answer(
            "У тебя уже есть доступ к боту. Пользуйся главным меню ниже."
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
            "После одобрения ты получишь сообщение."
        )
    except Exception:
        await message.answer(
            "Не получилось отправить запрос администратору. Попробуй позже."
        )


@dp.message(Command("next"))
async def cmd_next(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
        return

    state = user_state[uid]
    if state["remaining"] is not None and not state["remaining"]:
        reset_progress(uid)

    await send_new_word(uid, message.chat.id)


@dp.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
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
        await message.answer("Нет доступа.")
        return

    if not GRAMMAR_RULES:
        await message.answer(
            "Раздел грамматики пока не настроен. Добавь свои правила в список GRAMMAR_RULES."
        )
        return

    kb = build_grammar_keyboard()
    await message.answer("Выбери грамматическое правило:", reply_markup=kb)


@dp.message(Command("check"))
async def cmd_check_on(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
        return

    user_state[uid]["check_mode"] = True
    save_user_state()
    await message.answer(
        "✏️ Режим проверки предложений включен.\n\n"
        "Напиши предложение на немецком, и я предложу исправленный вариант и отмечу ошибки."
    )


@dp.message(Command("checkoff"))
async def cmd_check_off(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
        return

    user_state[uid]["check_mode"] = False
    save_user_state()
    await message.answer(
        "Режим проверки предложений выключен. Можно вернуться к тренировке слов или грамматики."
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
        return

    text = build_user_stats_text(uid)
    await message.answer(text)

# ==========================
# ОБРАБОТЧИК ТЕКСТА В РЕЖИМЕ ПРОВЕРКИ
# ==========================

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_plain_text(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        return

    state = user_state[uid]

    if not state.get("check_mode", False):
        return

    text = message.text.strip()
    if not text:
        await message.answer("Напиши, пожалуйста, предложение на немецком.")
        return

    waiting_msg = await message.answer("⌛ Проверяю предложение...")

    result = await check_text_with_ai(text)

    await waiting_msg.edit_text(result)

# ==========================
# CALLBACK ХЕНДЛЕРЫ
# ==========================

@dp.callback_query(F.data == "req_access")
async def cb_req_access(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid == ADMIN_ID or uid in allowed_users:
        await callback.answer("Доступ уже есть.")
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
        f"Пользователь: {callback.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            txt,
            reply_markup=kb,
        )
        await callback.answer("Запрос отправлен администратору.")
        await callback.message.answer(
            "Запрос на доступ отправлен. Ожидай решение администратора."
        )
    except Exception:
        await callback.answer("Ошибка отправки запроса.", show_alert=True)


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

    try:
        text = (
            "✅ Доступ к боту одобрен.\n\n"
            "Теперь ты можешь пользоваться всеми режимами через главное меню.\n\n"
            "Выбирай тренировки слов, темы, грамматику или проверку предложений с помощью кнопок."
        )
        await bot.send_message(user_id, text, reply_markup=build_main_menu_keyboard())
    except Exception:
        pass


@dp.callback_query(F.data == "menu_words")
async def cb_menu_words(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    kb = build_themes_keyboard()
    await callback.message.answer(
        "Сначала выбери уровень и тему, а затем подтему. В скобках показано количество слов.",
        reply_markup=kb,
    )


@dp.callback_query(F.data == "menu_themes")
async def cb_menu_themes(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    kb = build_themes_keyboard()
    await callback.message.answer(
        "Выбери уровень или сразу все слова. Затем выбери тему и подтему.",
        reply_markup=kb,
    )


@dp.callback_query(F.data == "menu_grammar")
async def cb_menu_grammar(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()

    if not GRAMMAR_RULES:
        await callback.message.answer(
            "Раздел грамматики пока не настроен. Добавь свои правила в список GRAMMAR_RULES."
        )
        return

    kb = build_grammar_keyboard()
    await callback.message.answer("Выбери грамматическую тему:", reply_markup=kb)


@dp.callback_query(F.data == "menu_check")
async def cb_menu_check(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()

    user_state[uid]["check_mode"] = True
    save_user_state()

    await callback.message.answer(
        "✏️ Режим проверки предложений включен.\n\n"
        "Напиши предложение на немецком, и я предложу исправленный вариант и отмечу ошибки."
    )


@dp.callback_query(F.data == "menu_stats")
async def cb_menu_stats(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()

    text = build_user_stats_text(uid)
    await callback.message.answer(text)


@dp.callback_query(F.data == "topic_all")
async def cb_topic_all(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
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

    await send_new_word(uid, callback.message.chat.id)


@dp.callback_query(F.data.startswith("level|"))
async def cb_level(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
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


@dp.callback_query(F.data.startswith("topic_select|"))
async def cb_topic_select(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, level, topic = callback.data.split("|", maxsplit=2)

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


@dp.callback_query(F.data.startswith("subtopic|"))
async def cb_subtopic(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, level, topic, subtopic = callback.data.split("|", maxsplit=3)

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

    await send_new_word(uid, callback.message.chat.id)


@dp.callback_query(F.data.startswith("mode|"))
async def cb_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, mode = callback.data.split("|", maxsplit=1)
    user_state[uid]["mode"] = mode
    save_user_state()
    if mode == "de_ru":
        txt = "Режим установлен: 🇩🇪 → 🇷🇺. Буду показывать немецкое слово, а ты выбирай русский перевод."
    else:
        txt = "Режим установлен: 🇷🇺 → 🇩🇪. Буду показывать русское слово, а ты выбирай немецкий вариант с транскрипцией."
    await callback.answer("Режим обновлен.")
    try:
        await callback.message.edit_text(txt)
    except Exception:
        await callback.message.answer(txt)


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
        save_user_state()

        if mode == "de_ru":
            text = (
                "✅ Правильно.\n\n"
                f'{w["de"]} [{w["tr"]}] - {w["ru"]}'
            )
        else:
            text = (
                "✅ Правильно.\n\n"
                f'{w["ru"]} - {w["de"]} [{w["tr"]}]'
            )

        finished_now = not state["remaining"]

        if finished_now:
            current_topic = state.get("topic", TOPIC_ALL)
            correct = state.get("correct", 0)
            wrong = state.get("wrong", 0)
            update_topic_stats(uid, current_topic, correct, wrong)

            text += (
                "\n\nТы прошел все слова в этой подборке.\n"
                f'✅ Правильных ответов: {state["correct"]}\n'
                f'❌ Неправильных ответов: {state["wrong"]}\n\n'
                "Можно выбрать другую подтему в разделе Темы слов или начать новую тренировку."
            )

        try:
            await callback.message.edit_text(text)
        except Exception:
            await callback.message.answer(text)

        if not finished_now:
            await send_new_word(uid, callback.message.chat.id)

    else:
        state["wrong"] += 1
        save_user_state()
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

    user_rule_state = grammar_state[uid].setdefault(
        rule_id, {"correct": 0, "wrong": 0, "q_index": 0}
    )

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
        "Правильный ответ:\n"
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
            f"❌ Неправильных ответов: {total_wrong}\n\n"
            "Можно выбрать другую грамматическую тему."
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
    load_user_state()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
