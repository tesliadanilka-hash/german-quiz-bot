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
from aiogram.client.default import DefaultBotProperties

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

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="Markdown")
)
dp = Dispatcher()

# ==========================
# НАСТРОЙКИ OPENAI
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

Word = Dict[str, Any]

# ==========================
# АУДИРОВАНИЕ: СТРУКТУРА, ТЕМЫ A1-B2, ХРАНЕНИЕ
# ==========================

LISTENING_FILE = Path("listenings.json")
LISTENING_AUDIO_DIR = Path("listenings_audio")  # сюда кладешь .ogg/.mp3

# ВАЖНО: Слова отдельным пунктом "Тренировать слова".
# В "Аудирование" мы НЕ кладем одиночные слова, только фразы/диалоги/сцены.

LISTENING_TOPICS: Dict[str, List[Dict[str, str]]] = {
    "A1": [
        {"id": "a1_intro", "title": "Знакомство и приветствия"},
        {"id": "a1_station", "title": "Вокзал и транспорт"},
        {"id": "a1_city", "title": "Город и ориентация"},
        {"id": "a1_shop", "title": "Покупки и цены"},
        {"id": "a1_food", "title": "Еда и кафе"},
        {"id": "a1_home", "title": "Дом и быт"},
        {"id": "a1_time", "title": "Время и расписание"},
        {"id": "a1_health", "title": "Здоровье и аптека"},
        {"id": "a1_jobcenter", "title": "Соцслужбы: Jobcenter и базовые запросы"},
        {"id": "a1_smalltalk", "title": "Короткие разговоры и планы"},
    ],
    "A2": [
        {"id": "a2_daily", "title": "Повседневные ситуации"},
        {"id": "a2_work", "title": "Работа и общение на работе"},
        {"id": "a2_rent", "title": "Аренда жилья и проблемы дома"},
        {"id": "a2_doctor", "title": "Врач и запись на прием"},
        {"id": "a2_services", "title": "Сервисы и услуги (ремонт, доставка)"},
        {"id": "a2_travel", "title": "Поездки и планы на выходные"},
        {"id": "a2_phone", "title": "Звонки, сообщения, почта"},
        {"id": "a2_school", "title": "Курсы и учеба"},
        {"id": "a2_bureau", "title": "Учреждения и документы"},
        {"id": "a2_conflicts", "title": "Проблемы и жалобы (мягко)"},
    ],
    "B1": [
        {"id": "b1_news", "title": "Новости и обсуждение событий"},
        {"id": "b1_work", "title": "Работа: собеседование, договор, задачи"},
        {"id": "b1_health", "title": "Здоровье: симптомы, лечение, рекомендации"},
        {"id": "b1_housing", "title": "Жилье: договор, письма, вопросы к хозяину"},
        {"id": "b1_official", "title": "Официальные разговоры и звонки"},
        {"id": "b1_travel", "title": "Путешествия и ситуации в пути"},
        {"id": "b1_conflict", "title": "Споры, недовольство, аргументы"},
        {"id": "b1_finance", "title": "Финансы: счета, покупки, возвраты"},
        {"id": "b1_education", "title": "Учеба, планы, цели"},
        {"id": "b1_society", "title": "Общество, культура, правила"},
    ],
    "B2": [
        {"id": "b2_debate", "title": "Дискуссии и аргументация"},
        {"id": "b2_work", "title": "Профессиональные встречи и переговоры"},
        {"id": "b2_present", "title": "Презентации и объяснения процессов"},
        {"id": "b2_media", "title": "Медиа: интервью, подкасты, обзоры"},
        {"id": "b2_science", "title": "Наука и технологии (общие темы)"},
        {"id": "b2_law", "title": "Право и бюрократия (без узких деталей)"},
        {"id": "b2_economy", "title": "Экономика и бизнес (база)"},
        {"id": "b2_social", "title": "Социальные темы и мнения"},
        {"id": "b2_emails", "title": "Деловые письма и формальные разговоры"},
        {"id": "b2_long", "title": "Длинные диалоги и истории (1-2 минуты)"},
    ],
}

# Структура элемента listenings.json:
# [
#   {
#     "id": "A1_station_001",
#     "level": "A1",
#     "topic_id": "a1_station",
#     "title": "Am Bahnhof: Toni begruesst dich",
#     "audio_file": "A1_station_001.ogg",
#     "transcript_de": "Hallo! Ich bin Toni. Willkommen am Bahnhof. Wie heißt du?",
#     "questions": [
#        {"question": "Wo sind sie?", "options": ["Am Bahnhof","Im Restaurant","In der Schule","Im Park"], "correct_index": 0},
#        ...
#     ]
#   }
# ]

LISTENINGS: List[Dict[str, Any]] = []
LISTENING_BY_ID: Dict[str, Dict[str, Any]] = {}
LISTENINGS_BY_LEVEL_TOPIC: Dict[Tuple[str, str], List[str]] = defaultdict(list)

# user_id -> state for current listening quiz
LISTENING_QUIZ_STATE: Dict[int, Dict[str, Any]] = {}


def ensure_default_listenings_file() -> None:
    if LISTENING_FILE.exists():
        return

    LISTENING_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    sample = [
        {
            "id": "A1_station_001",
            "level": "A1",
            "topic_id": "a1_station",
            "title": "Am Bahnhof: Toni begruesst dich",
            "audio_file": "A1_station_001.ogg",
            "transcript_de": "Hallo! Ich bin Toni. Willkommen am Bahnhof. Wie heißt du?",
            "questions": [
                {
                    "question": "Wo sind sie?",
                    "options": ["Am Bahnhof", "Im Restaurant", "In der Schule", "Im Park"],
                    "correct_index": 0
                },
                {
                    "question": "Wie heißt er?",
                    "options": ["Toni", "Ahmet", "Max", "Paul"],
                    "correct_index": 0
                }
            ]
        }
    ]

    with LISTENING_FILE.open("w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=2)

    print("Создан listenings.json с примером. Добавь аудио файл в папку listenings_audio.")


def load_listenings() -> None:
    global LISTENINGS, LISTENING_BY_ID, LISTENINGS_BY_LEVEL_TOPIC

    LISTENINGS = []
    LISTENING_BY_ID = {}
    LISTENINGS_BY_LEVEL_TOPIC = defaultdict(list)

    ensure_default_listenings_file()

    try:
        with LISTENING_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Ошибка чтения listenings.json:", e)
        return

    if not isinstance(data, list):
        print("listenings.json должен быть списком объектов.")
        return

    for item in data:
        if not isinstance(item, dict):
            continue
        lid = str(item.get("id", "")).strip()
        level = str(item.get("level", "")).strip()
        topic_id = str(item.get("topic_id", "")).strip()
        title = str(item.get("title", "")).strip()
        audio_file = str(item.get("audio_file", "")).strip()
        questions = item.get("questions", [])

        if not lid or not level or not topic_id or not title or not audio_file:
            continue
        if not isinstance(questions, list) or not questions:
            continue

        ok_questions = []
        for q in questions:
            if not isinstance(q, dict):
                continue
            qq = str(q.get("question", "")).strip()
            opts = q.get("options", [])
            ci = q.get("correct_index", None)
            if not qq or not isinstance(opts, list) or len(opts) != 4:
                continue
            if not isinstance(ci, int) or ci < 0 or ci > 3:
                continue
            ok_questions.append(
                {"question": qq, "options": [str(x) for x in opts], "correct_index": ci}
            )
        if not ok_questions:
            continue

        clean = dict(item)
        clean["questions"] = ok_questions

        LISTENINGS.append(clean)
        LISTENING_BY_ID[lid] = clean
        LISTENINGS_BY_LEVEL_TOPIC[(level, topic_id)].append(lid)

    print(f"Загружено аудирований: {len(LISTENINGS)}")


def listening_prompt_template() -> str:
    # Это промт для генерации одного блока аудирования (текст+вопросы) под твою базу.
    return (
        "Ты методист DaF (немецкий как иностранный). Сгенерируй ОДИН блок аудирования.\n"
        "Требования:\n"
        "1) Уровень: {LEVEL}\n"
        "2) Тема: {TOPIC_TITLE}\n"
        "3) Длина аудио: {SECONDS} секунд (коротко).\n"
        "4) Язык аудио: ТОЛЬКО немецкий.\n"
        "5) Дай transcript_de без сложных конструкций, строго по уровню.\n"
        "6) Сделай 4 вопроса на понимание смысла. У каждого вопроса ровно 4 варианта ответа.\n"
        "7) Один вариант правильный, correct_index 0-3.\n"
        "8) Варианты должны быть правдоподобными.\n"
        "9) Не используй кавычки-елочки. Не используй длинные тире.\n\n"
        "Формат ответа: только JSON:\n"
        "{\n"
        "  \"title\": \"...\",\n"
        "  \"transcript_de\": \"...\",\n"
        "  \"questions\": [\n"
        "    {\"question\":\"...\",\"options\":[\"...\",\"...\",\"...\",\"...\"],\"correct_index\":0}\n"
        "  ]\n"
        "}\n"
    )


# ==========================
# ГРАММАТИКА - КНОПКИ, ПРАВИЛА, ВИКТОРИНЫ
# ==========================

GRAMMAR_FILE = Path("grammar.json")
GRAMMAR_RULES: List[Dict[str, Any]] = []

USER_QUIZ_STATE: Dict[int, Dict[str, Any]] = {}
QUIZ_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def strip_html_tags(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    for tag in ("<b>", "</b>", "<i>", "</i>", "<u>", "</u>"):
        text = text.replace(tag, "")
    return text


def load_grammar_rules() -> None:
    global GRAMMAR_RULES
    if not GRAMMAR_FILE.exists():
        print("grammar.json не найден.")
        GRAMMAR_RULES = []
        return

    with GRAMMAR_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        GRAMMAR_RULES = data
    elif isinstance(data, dict) and "rules" in data:
        GRAMMAR_RULES = data["rules"]
    elif isinstance(data, dict):
        rules: List[Dict[str, Any]] = []
        for v in data.values():
            if isinstance(v, list):
                rules.extend(v)
        GRAMMAR_RULES = rules
    else:
        GRAMMAR_RULES = []

    print(f"Загружено грамматических правил: {len(GRAMMAR_RULES)}")


def get_sublevel_from_topic(topic: str) -> str:
    if "-" in topic:
        return topic.split("-", 1)[0].strip()
    return topic.strip()


def get_rules_by_level(level: str) -> List[Dict[str, Any]]:
    return [r for r in GRAMMAR_RULES if r.get("level") == level]


def get_sublevels_for_level(level: str) -> List[str]:
    sublevels = set()
    for rule in get_rules_by_level(level):
        topic = rule.get("topic", "")
        sub = get_sublevel_from_topic(topic)
        if sub.startswith(level):
            sublevels.add(sub)
    return sorted(sublevels)


def get_rules_by_sublevel(sublevel: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for r in GRAMMAR_RULES:
        topic = r.get("topic", "")
        if get_sublevel_from_topic(topic) == sublevel:
            result.append(r)
    return result


def get_rule_by_id(rule_id: str) -> Optional[Dict[str, Any]]:
    for r in GRAMMAR_RULES:
        if r.get("id") == rule_id:
            return r
    return None


def kb_grammar_levels() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="Правила уровня A1", callback_data="grammar_level:A1"),
            InlineKeyboardButton(text="Правила уровня A2", callback_data="grammar_level:A2"),
        ],
        [InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_grammar_sublevels(level: str) -> InlineKeyboardMarkup:
    sublevels = get_sublevels_for_level(level)
    rows: List[List[InlineKeyboardButton]] = []
    row: List[InlineKeyboardButton] = []
    for sub in sublevels:
        row.append(
            InlineKeyboardButton(
                text=sub,
                callback_data=f"grammar_sub:{sub}",
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="⬅ Выбор уровня", callback_data="grammar_menu")])
    rows.append([InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_grammar_rules_list(sublevel: str) -> InlineKeyboardMarkup:
    rules = get_rules_by_sublevel(sublevel)
    rows: List[List[InlineKeyboardButton]] = []
    for r in rules:
        rows.append(
            [
                InlineKeyboardButton(
                    text=r.get("title", "Правило"),
                    callback_data=f"grammar_rule:{r['id']}",
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅ Подуровни",
                callback_data=f"grammar_level:{sublevel.split('.')[0]}",
            )
        ]
    )
    rows.append([InlineKeyboardButton(text="⬅ Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_rule_after_explanation(rule_id: str) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(
                text="🧠 Практиковать упражнение по этой теме",
                callback_data=f"grammar_quiz_start:{rule_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ К списку правил",
                callback_data="grammar_back_rules",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ Главное меню",
                callback_data="main_menu",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def kb_quiz_answers(rule_id: str, q_index: int, options: List[str]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i, opt in enumerate(options):
        rows.append(
            [
                InlineKeyboardButton(
                    text=opt,
                    callback_data=f"grammar_quiz_ans:{rule_id}:{q_index}:{i}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_after_quiz(rule_id: str) -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(
                text="🔁 Практиковать еще раз",
                callback_data=f"grammar_quiz_start:{rule_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="📚 К выбору правил",
                callback_data="grammar_menu",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ Главное меню",
                callback_data="main_menu",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def get_quiz_instruction_ru() -> str:
    return (
        "📝 Задание: выбери один правильный вариант ответа, "
        "который грамматически подходит к этому предложению по текущему правилу."
    )


async def generate_quiz_for_rule(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    if client is None:
        print("Нет OPENAI_API_KEY, викторина по грамматике недоступна.")
        return []

    rule_id = str(rule.get("id", ""))
    if not rule_id:
        print("У правила нет id, не могу кэшировать упражнения.")
        return []

    cached = QUIZ_CACHE.get(rule_id)
    if cached:
        return cached

    title = strip_html_tags(rule.get("title", ""))
    explanation = strip_html_tags(rule.get("explanation", ""))

    user_prompt = (
        "Du bist ein professioneller Lehrer fuer Deutsch als Fremdsprache.\n"
        "Erstelle 5 kurze Uebungsaufgaben, die AUSSCHLIESSLICH dieses Grammatikthema pruefen.\n"
        "Benutze KEINE anderen Grammatikstrukturen, die nicht zu diesem Thema gehoeren.\n\n"
        "WICHTIG:\n"
        "- Schreibe ALLES nur auf Deutsch.\n"
        "- Keine Erklaerungen, kein Englisch, keine anderen Sprachen.\n"
        "- Feld \"question\" enthaelt nur den Beispielsatz oder Satz mit Luecke, "
        "ohne Arbeitsanweisungen wie \"Waehle die richtige Antwort\".\n"
        "- Die Arbeitsanweisung wird der Bot auf Russisch erklaeren, du brauchst sie NICHT zu schreiben.\n"
        "- Jede Aufgabe hat GENAU 4 Antwortoptionen.\n"
        "- Es gibt GENAU EINE richtige Antwort (correct_index).\n"
        "- Mische die Aufgabentypen, aber bleibe immer in diesem Grammatikthema.\n\n"
        "Antwortformat: ein einziges JSON-Objekt:\n"
        "{\n"
        "  \"questions\": [\n"
        "    {\n"
        "      \"question\": \"Satz oder Satz mit Luecke auf Deutsch\",\n"
        "      \"options\": [\"Antwort 1\",\"Antwort 2\",\"Antwort 3\",\"Antwort 4\"],\n"
        "      \"correct_index\": 0\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Schreibe WIRKLICH nur JSON, ohne Kommentar, ohne Erklaerung, "
        "ohne Text ausserhalb des JSON. Benutze keine HTML-Tags.\n\n"
        f"Grammatikthema (Titel): {title}\n\n"
        f"Erklaerung des Themas:\n{explanation}\n"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du bist ein strenger JSON-Generator und "
                        "professioneller Lehrer fuer Deutsch als Fremdsprache. "
                        "Antwort immer NUR mit einem gueltigen JSON-Objekt."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            max_tokens=700,
        )
        content = completion.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.strip()
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            if content.lower().startswith("json"):
                content = content[4:].lstrip()

        data = json.loads(content)
    except Exception as e:
        print("Ошибка при генерации викторины:", e)
        return []

    questions = data.get("questions", [])
    clean_questions: List[Dict[str, Any]] = []

    for q in questions:
        if not isinstance(q, dict):
            continue
        opts = q.get("options", [])
        if len(opts) != 4:
            continue
        if not isinstance(q.get("correct_index", 0), int):
            continue

        question_text = strip_html_tags(q.get("question", ""))
        options_clean = [strip_html_tags(o) for o in opts]

        clean_questions.append(
            {
                "question": question_text,
                "options": options_clean,
                "correct_index": int(q["correct_index"]),
            }
        )

    if not clean_questions:
        return []

    random.shuffle(clean_questions)
    clean_questions = clean_questions[:5]

    QUIZ_CACHE[rule_id] = clean_questions
    return clean_questions

# ==========================
# ТЕМЫ ДЛЯ СЛОВ
# ==========================

TOPIC_ALL = "ALL"

user_state: Dict[int, Dict[str, Any]] = defaultdict(
    lambda: {
        "mode": "de_ru",
        "topic": TOPIC_ALL,
        "correct": 0,
        "wrong": 0,
        "remaining": None,
        "check_mode": False,
        "topic_stats": {},
        "answer_mode": "choice",
        "waiting_text_answer": False,
        "current_word_id": None,
        "grammar_stats": {
            "total_correct": 0,
            "total_wrong": 0,
            "per_rule": {}
        },
    }
)

allowed_users: set[int] = set()

WORDS: List[Dict[str, Any]] = []
WORDS_BY_TOPIC: Dict[str, List[int]] = defaultdict(list)
LEVEL_COUNTS: Dict[str, int] = defaultdict(int)
TOPIC_COUNTS: Dict[Tuple[str, str], int] = defaultdict(int)
SUBTOPIC_COUNTS: Dict[Tuple[str, str, str], int] = defaultdict(int)

TOPIC_ID_BY_KEY: Dict[Tuple[str, str], str] = {}
TOPIC_KEY_BY_ID: Dict[str, Tuple[str, str]] = {}
SUBTOPIC_ID_BY_KEY: Dict[Tuple[str, str, str]] = {}
SUBTOPIC_KEY_BY_ID: Dict[str, Tuple[str, str, str]] = {}

# ==========================
# ДОСТУП
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
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ
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
            base = user_state[uid]
            base.update(state)
            user_state[uid] = base
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
# ЗАГРУЗКА СЛОВ
# ==========================

def load_words(path: str = "words.json") -> None:
    global WORDS, WORDS_BY_TOPIC, LEVEL_COUNTS, TOPIC_COUNTS, SUBTOPIC_COUNTS
    global TOPIC_ID_BY_KEY, TOPIC_KEY_BY_ID, SUBTOPIC_ID_BY_KEY, SUBTOPIC_KEY_BY_ID
    global SUBTOPIC_KEY_BY_ID

    WORDS = []
    WORDS_BY_TOPIC = defaultdict(list)
    LEVEL_COUNTS = defaultdict(int)
    TOPIC_COUNTS = defaultdict(int)
    SUBTOPIC_COUNTS = defaultdict(int)
    TOPIC_ID_BY_KEY = {}
    TOPIC_KEY_BY_ID = {}
    SUBTOPIC_ID_BY_KEY = {}
    SUBTOPIC_KEY_BY_ID = {}

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
        word: Dict[str, Any] = {
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

    for i, key in enumerate(sorted(TOPIC_COUNTS.keys())):
        tid = f"t{i}"
        TOPIC_ID_BY_KEY[key] = tid
        TOPIC_KEY_BY_ID[tid] = key

    for i, key in enumerate(sorted(SUBTOPIC_COUNTS.keys())):
        sid = f"s{i}"
        SUBTOPIC_ID_BY_KEY[key] = sid
        SUBTOPIC_KEY_BY_ID[sid] = key

# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ДЛЯ ТЕМ
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
        return f"Уровень {level}: {topic} -> {subtopic}"
    if len(parts) == 2:
        level, topic = parts
        return f"Уровень {level}: {topic}"
    return topic_key

# ==========================
# ФУНКЦИИ ДЛЯ СЛОВ
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
    state["waiting_text_answer"] = False
    state["current_word_id"] = None
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
            text = f'{w["de"]} ({w["tr"]})'
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
            "Выбери уровень и тему через Тренировку слов.",
        )
        return

    word_id = state["remaining"].pop()
    w = WORDS[word_id]
    answer_mode = state.get("answer_mode", "choice")
    mode = state["mode"]
    word_pool = get_user_words(user_id)

    if answer_mode == "choice":
        if mode == "de_ru":
            text = f'🇩🇪 Слово: {w["de"]} ({w["tr"]})\nВыбери правильный перевод на русский.'
        else:
            text = f'🇷🇺 Слово: {w["ru"]}\nВыбери правильный перевод на немецкий.'
        kb = build_options(word_pool, word_id, mode)
        await bot.send_message(chat_id, text, reply_markup=kb)
    else:
        text = (
            f'🇷🇺 Слово: {w["ru"]}\n\n'
            "Напиши это слово по немецки, только само немецкое слово, без транскрипции и без скобок."
        )
        state["current_word_id"] = word_id
        state["waiting_text_answer"] = True
        save_user_state()
        await bot.send_message(chat_id, text)


async def resend_same_word(chat_id: int, word_id: int, mode: str, uid: int) -> None:
    w = WORDS[word_id]
    word_pool = get_user_words(uid)

    if mode == "de_ru":
        text = (
            "❌ Неправильно.\n"
            "Попробуй еще раз.\n\n"
            f'🇩🇪 Слово: {w["de"]} ({w["tr"]})\nВыбери правильный перевод на русский.'
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
# КЛАВИАТУРЫ МЕНЮ
# ==========================

def build_back_to_main_row() -> List[List[InlineKeyboardButton]]:
    return [
        [
            InlineKeyboardButton(
                text="⬅️ Главное меню",
                callback_data="back_main",
            )
        ]
    ]


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Тренировать слова", callback_data="menu_words")],
            [InlineKeyboardButton(text="🎧 Аудирование", callback_data="menu_listening")],
            [InlineKeyboardButton(text="📘 Грамматика", callback_data="grammar_menu")],
            [InlineKeyboardButton(text="✏️ Проверка предложений", callback_data="menu_check")],
            [InlineKeyboardButton(text="⚙️ Формат ответа", callback_data="menu_answer_mode")],
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="menu_stats")],
        ]
    )


def build_themes_keyboard() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

    total_words = len(WORDS)
    rows.append([InlineKeyboardButton(text=f"Все слова ({total_words})", callback_data="topic_all")])

    for level in get_levels():
        count = LEVEL_COUNTS.get(level, 0)
        rows.append([InlineKeyboardButton(text=f"Уровень {level} ({count})", callback_data=f"level|{level}")])

    rows.extend(build_back_to_main_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_topics_keyboard_for_level(level: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for topic in get_topics_for_level(level):
        key = (level, topic)
        topic_id = TOPIC_ID_BY_KEY.get(key)
        if not topic_id:
            continue
        count = TOPIC_COUNTS.get(key, 0)
        rows.append([InlineKeyboardButton(text=f"{topic} ({count})", callback_data=f"topic_select|{topic_id}")])

    rows.extend(build_back_to_main_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_subtopics_keyboard(level: str, topic: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for subtopic in get_subtopics_for_level_topic(level, topic):
        key = (level, topic, subtopic)
        sub_id = SUBTOPIC_ID_BY_KEY.get(key)
        if not sub_id:
            continue
        count = SUBTOPIC_COUNTS.get(key, 0)
        rows.append([InlineKeyboardButton(text=f"{subtopic} ({count})", callback_data=f"subtopic|{sub_id}")])

    rows.extend(build_back_to_main_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_mode_keyboard_for_settings(current_mode: str) -> List[List[InlineKeyboardButton]]:
    de_selected = "✅ " if current_mode == "de_ru" else ""
    ru_selected = "✅ " if current_mode == "ru_de" else ""
    return [
        [InlineKeyboardButton(text=f"{de_selected}🇩🇪 -> 🇷🇺 Немецкое слово", callback_data="mode|de_ru")],
        [InlineKeyboardButton(text=f"{ru_selected}🇷🇺 -> 🇩🇪 Русское слово", callback_data="mode|ru_de")],
    ]


def build_answer_mode_keyboard(current_answer: str) -> List[List[InlineKeyboardButton]]:
    choice_mark = "✅ " if current_answer == "choice" else ""
    typing_mark = "✅ " if current_answer == "typing" else ""
    return [
        [InlineKeyboardButton(text=f"{choice_mark}Варианты ответа (4)", callback_data="answer_mode|choice")],
        [InlineKeyboardButton(text=f"{typing_mark}Ввод слова вручную", callback_data="answer_mode|typing")],
    ]


def build_full_format_keyboard(current_mode: str, current_answer: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    rows.extend(build_mode_keyboard_for_settings(current_mode))
    rows.extend(build_answer_mode_keyboard(current_answer))
    rows.extend(build_back_to_main_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==========================
# АУДИРОВАНИЕ: КНОПКИ И ЛОГИКА
# ==========================

def kb_listening_levels() -> InlineKeyboardMarkup:
    rows = []
    for lvl in ["A1", "A2", "B1", "B2"]:
        rows.append([InlineKeyboardButton(text=f"Уровень {lvl}", callback_data=f"listen_level:{lvl}")])
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_listening_topics(level: str) -> InlineKeyboardMarkup:
    topics = LISTENING_TOPICS.get(level, [])
    rows: List[List[InlineKeyboardButton]] = []
    for t in topics:
        rows.append([InlineKeyboardButton(text=t["title"], callback_data=f"listen_topic:{level}:{t['id']}")])
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="menu_listening")])
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_listening_items(level: str, topic_id: str) -> InlineKeyboardMarkup:
    ids = LISTENINGS_BY_LEVEL_TOPIC.get((level, topic_id), [])
    rows: List[List[InlineKeyboardButton]] = []
    if not ids:
        rows.append([InlineKeyboardButton(text="Пока пусто", callback_data="noop")])
    else:
        for lid in ids[:30]:
            item = LISTENING_BY_ID.get(lid)
            if not item:
                continue
            rows.append([InlineKeyboardButton(text=item.get("title", lid), callback_data=f"listen_item:{lid}")])

    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"listen_level:{level}")])
    rows.append([InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_listening_start(listen_id: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="▶ Слушать", callback_data=f"listen_start:{listen_id}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data=f"listen_back_from_item:{listen_id}")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_listening_answers(listen_id: str, q_index: int, options: List[str]) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    for i, opt in enumerate(options):
        rows.append([InlineKeyboardButton(text=opt, callback_data=f"listen_ans:{listen_id}:{q_index}:{i}")])
    rows.append([InlineKeyboardButton(text="🔁 Слушать еще раз", callback_data=f"listen_repeat:{listen_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_listening_finish(listen_id: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="🔁 Пройти еще раз", callback_data=f"listen_start:{listen_id}")],
        [InlineKeyboardButton(text="⬅ К темам", callback_data="menu_listening")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def find_topic_for_listen(listen_id: str) -> Tuple[str, str]:
    item = LISTENING_BY_ID.get(listen_id)
    if not item:
        return ("A1", "a1_intro")
    return (str(item.get("level", "A1")), str(item.get("topic_id", "a1_intro")))


async def send_listening_audio(chat_id: int, item: Dict[str, Any]) -> bool:
    audio_file = str(item.get("audio_file", "")).strip()
    if not audio_file:
        return False

    path = LISTENING_AUDIO_DIR / audio_file
    if not path.exists():
        await bot.send_message(
            chat_id,
            "Аудио файл не найден.\n"
            f"Нужно положить файл: {path.as_posix()}"
        )
        return False

    try:
        # Для аудирования удобнее voice, но можно и audio.
        await bot.send_voice(chat_id, voice=open(path, "rb"))
        return True
    except Exception as e:
        print("Ошибка отправки аудио:", e)
        return False


async def send_listening_question(chat_id: int, listen_id: str, q_index: int) -> None:
    item = LISTENING_BY_ID.get(listen_id)
    if not item:
        await bot.send_message(chat_id, "Аудирование не найдено.")
        return

    questions = item.get("questions", [])
    if q_index >= len(questions):
        state = LISTENING_QUIZ_STATE.get(chat_id, {})
        score = state.get("score", 0)
        total = len(questions)
        await bot.send_message(
            chat_id,
            f"✅ Готово.\n\nРезультат: {score}/{total}",
            reply_markup=kb_listening_finish(listen_id)
        )
        return

    q = questions[q_index]
    text = (
        f"🎧 Аудирование: *{item.get('title','')}*\n\n"
        f"❓ Вопрос {q_index + 1}/{len(questions)}\n"
        f"{q['question']}"
    )
    await bot.send_message(chat_id, text, reply_markup=kb_listening_answers(listen_id, q_index, q["options"]))


# ==========================
# СТАТИСТИКА
# ==========================

def update_topic_stats(uid: int, topic: str, correct: int, wrong: int) -> None:
    total = correct + wrong
    if total <= 0:
        return

    accuracy = correct * 100.0 / total

    state = user_state[uid]
    topic_stats = state.setdefault("topic_stats", {})
    stats = topic_stats.get(
        topic,
        {
            "runs": 0,
            "best_accuracy": 0.0,
            "last_accuracy": 0.0,
            "total_correct": 0,
            "total_wrong": 0,
        },
    )

    stats["runs"] += 1
    stats["last_accuracy"] = accuracy
    if accuracy > stats.get("best_accuracy", 0.0):
        stats["best_accuracy"] = accuracy
    stats["total_correct"] += correct
    stats["total_wrong"] += wrong

    topic_stats[topic] = stats
    save_user_state()


def update_grammar_stats(uid: int, rule_id: str, correct_delta: int = 0, wrong_delta: int = 0, finished_quiz: bool = False) -> None:
    state = user_state[uid]

    gstats = state.get("grammar_stats")
    if not isinstance(gstats, dict):
        gstats = {"total_correct": 0, "total_wrong": 0, "per_rule": {}}

    per_rule = gstats.get("per_rule")
    if not isinstance(per_rule, dict):
        per_rule = {}

    rule_stats = per_rule.get(rule_id, {
        "correct": 0,
        "wrong": 0,
        "runs": 0,
    })

    if correct_delta > 0:
        rule_stats["correct"] += correct_delta
        gstats["total_correct"] = gstats.get("total_correct", 0) + correct_delta

    if wrong_delta > 0:
        rule_stats["wrong"] += wrong_delta
        gstats["total_wrong"] = gstats.get("total_wrong", 0) + wrong_delta

    if finished_quiz:
        rule_stats["runs"] += 1

    per_rule[rule_id] = rule_stats
    gstats["per_rule"] = per_rule
    state["grammar_stats"] = gstats
    user_state[uid] = state
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
# КОМАНДЫ
# ==========================

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔓 Запросить доступ", callback_data="req_access")]
            ]
        )

        text = (
            "🎓 Willkommen. Добро пожаловать в закрытого бота по немецкому языку.\n\n"
            "Этот бот помогает улучшать немецкий язык через слова, грамматику, аудирование и проверку предложений.\n\n"
            "Доступ ограничен. Нажми кнопку ниже, чтобы отправить запрос администратору."
        )
        await message.answer(text, reply_markup=kb)
        return

    total_words = len(WORDS)
    total_topics = len(TOPIC_COUNTS)
    total_subtopics = len(SUBTOPIC_COUNTS)

    text = (
        "🎓 Willkommen. Добро пожаловать в бота по немецкому языку.\n\n"
        "Здесь ты можешь:\n"
        "• Тренировать слова по уровням, темам и подтемам\n"
        "• Разбирать грамматику\n"
        "• Тренировать аудирование\n"
        "• Проверять свои предложения\n"
        "• Смотреть статистику по темам\n\n"
        f"Сейчас в базе {total_words} слов.\n"
        f"Тем: {total_topics}, подтем: {total_subtopics}.\n"
        f"Аудирований: {len(LISTENINGS)}.\n\n"
        "Используй главное меню ниже, чтобы выбрать режим."
    )

    kb = build_main_menu_keyboard()
    await message.answer(text, reply_markup=kb)

    user_state[uid]["check_mode"] = False
    save_user_state()


@dp.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if uid == ADMIN_ID or uid in allowed_users:
        await message.answer("У тебя уже есть доступ к боту. Пользуйся главным меню ниже.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разрешить доступ", callback_data=f"allow|{uid}")]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {message.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await bot.send_message(ADMIN_ID, txt, reply_markup=kb)
        await message.answer("Запрос на доступ отправлен администратору.\nПосле одобрения ты получишь сообщение.")
    except Exception:
        await message.answer("Не получилось отправить запрос администратору. Попробуй позже.")


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

    current_mode = user_state[uid].get("mode", "de_ru")
    current_answer = user_state[uid].get("answer_mode", "choice")
    kb = build_full_format_keyboard(current_mode, current_answer)
    await message.answer("Здесь ты можешь настроить направление перевода и формат ответа.", reply_markup=kb)


@dp.message(Command("grammar"))
async def cmd_grammar(message: Message) -> None:
    uid = message.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
        return

    load_grammar_rules()
    if not GRAMMAR_RULES:
        await message.answer("Файл grammar.json не найден или в нем нет правил.")
        return

    await message.answer("Выбери уровень грамматики:", reply_markup=kb_grammar_levels())


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
    await message.answer("Режим проверки предложений выключен. Можно вернуться к тренировке слов или грамматики.")


@dp.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа.")
        return

    text = build_user_stats_text(uid)
    await message.answer(text)

# ==========================
# ОБРАБОТЧИК ТЕКСТА
# ==========================

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_plain_text(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        return

    text = message.text.strip()
    if not text:
        return

    state = user_state[uid]

    if state.get("check_mode", False):
        waiting_msg = await message.answer("⌛ Проверяю предложение...")
        result = await check_text_with_ai(text)
        await waiting_msg.edit_text(result)
        return

    if state.get("answer_mode") == "typing" and state.get("waiting_text_answer"):
        word_id = state.get("current_word_id")
        if word_id is None or word_id < 0 or word_id >= len(WORDS):
            state["waiting_text_answer"] = False
            state["current_word_id"] = None
            save_user_state()
            await message.answer("Что то пошло не так. Попробуй запросить новое слово.")
            return

        w = WORDS[word_id]
        user_answer = text.lower().strip()
        correct_answer = w["de"].lower().strip()

        if user_answer == correct_answer:
            state["correct"] += 1
            state["waiting_text_answer"] = False
            state["current_word_id"] = None
            save_user_state()

            reply = "✅ Правильно.\n\n" f'{w["de"]} ({w["tr"]}) - {w["ru"]}'
            await message.answer(reply)
        else:
            state["wrong"] += 1
            state["waiting_text_answer"] = False
            state["current_word_id"] = None
            save_user_state()

            reply = (
                "❌ Неправильно.\n\n"
                "Правильный ответ:\n"
                f'{w["de"]} ({w["tr"]}) - {w["ru"]}\n\n'
                "Пиши только немецкое слово, без транскрипции."
            )
            await message.answer(reply)

        await send_new_word(uid, message.chat.id)
        return

# ==========================
# CALLBACK: ДОСТУП
# ==========================

@dp.callback_query(F.data == "req_access")
async def cb_req_access(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid == ADMIN_ID or uid in allowed_users:
        await callback.answer("Доступ уже есть.")
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Разрешить доступ", callback_data=f"allow|{uid}")]
        ]
    )

    txt = (
        "🆕 Новый запрос на доступ.\n"
        f"Пользователь: {callback.from_user.full_name}\n"
        f"ID: {uid}"
    )

    try:
        await bot.send_message(ADMIN_ID, txt, reply_markup=kb)
        await callback.answer("Запрос отправлен администратору.")
        await callback.message.answer("Запрос на доступ отправлен. Ожидай решение администратора.")
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
    await callback.message.edit_text(f"✅ Доступ пользователю {user_id} разрешен.")

    try:
        text = (
            "✅ Доступ к боту одобрен.\n\n"
            "Теперь ты можешь пользоваться всеми режимами через главное меню.\n\n"
            "Выбирай слова, аудирование, грамматику, проверку предложений, формат ответа или статистику."
        )
        await bot.send_message(user_id, text, reply_markup=build_main_menu_keyboard())
    except Exception:
        pass


@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    kb = build_main_menu_keyboard()
    text = "Главное меню. Выбери режим:"
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


@dp.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery) -> None:
    await cb_back_main(callback)

# ==========================
# CALLBACK: АУДИРОВАНИЕ
# ==========================

@dp.callback_query(F.data == "menu_listening")
async def cb_menu_listening(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    text = (
        "🎧 Аудирование\n\n"
        "Сначала ты слушаешь аудио, потом отвечаешь на вопросы.\n"
        "Выбери уровень:"
    )
    await callback.message.answer(text, reply_markup=kb_listening_levels())


@dp.callback_query(F.data.startswith("listen_level:"))
async def cb_listen_level(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    level = callback.data.split(":", 1)[1].strip()
    await callback.answer()
    text = f"🎧 Аудирование\n\nУровень: {level}\n\nВыбери тему:"
    await callback.message.answer(text, reply_markup=kb_listening_topics(level))


@dp.callback_query(F.data.startswith("listen_topic:"))
async def cb_listen_topic(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, level, topic_id = callback.data.split(":", 2)
    await callback.answer()

    topic_title = topic_id
    for t in LISTENING_TOPICS.get(level, []):
        if t["id"] == topic_id:
            topic_title = t["title"]

    text = (
        "🎧 Аудирование\n\n"
        f"Уровень: {level}\n"
        f"Тема: {topic_title}\n\n"
        "Выбери аудио:"
    )
    await callback.message.answer(text, reply_markup=kb_listening_items(level, topic_id))


@dp.callback_query(F.data.startswith("listen_item:"))
async def cb_listen_item(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    listen_id = callback.data.split(":", 1)[1].strip()
    item = LISTENING_BY_ID.get(listen_id)
    if not item:
        await callback.answer("Аудирование не найдено.", show_alert=True)
        return

    await callback.answer()

    text = (
        "🎧 Аудирование\n\n"
        f"*{item.get('title','')}*\n\n"
        "Нажми ▶ Слушать, потом ответь на вопросы."
    )
    await callback.message.answer(text, reply_markup=kb_listening_start(listen_id))


@dp.callback_query(F.data.startswith("listen_back_from_item:"))
async def cb_listen_back_from_item(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    listen_id = callback.data.split(":", 1)[1].strip()
    level, topic_id = find_topic_for_listen(listen_id)
    await callback.answer()
    await callback.message.answer("Выбери аудио:", reply_markup=kb_listening_items(level, topic_id))


@dp.callback_query(F.data.startswith("listen_start:"))
async def cb_listen_start(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    listen_id = callback.data.split(":", 1)[1].strip()
    item = LISTENING_BY_ID.get(listen_id)
    if not item:
        await callback.answer("Аудирование не найдено.", show_alert=True)
        return

    await callback.answer()

    LISTENING_QUIZ_STATE[uid] = {
        "listen_id": listen_id,
        "index": 0,
        "score": 0,
        "audio_sent": False
    }

    ok = await send_listening_audio(callback.message.chat.id, item)
    if not ok:
        await callback.message.answer("Не удалось отправить аудио. Проверь файл.")
        return

    LISTENING_QUIZ_STATE[uid]["audio_sent"] = True
    await callback.message.answer("❓ Теперь ответь на вопросы.")
    await send_listening_question(callback.message.chat.id, listen_id, 0)


@dp.callback_query(F.data.startswith("listen_repeat:"))
async def cb_listen_repeat(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    listen_id = callback.data.split(":", 1)[1].strip()
    item = LISTENING_BY_ID.get(listen_id)
    if not item:
        await callback.answer("Аудирование не найдено.", show_alert=True)
        return

    await callback.answer()

    state = LISTENING_QUIZ_STATE.get(uid)
    if not state or state.get("listen_id") != listen_id:
        LISTENING_QUIZ_STATE[uid] = {"listen_id": listen_id, "index": 0, "score": 0, "audio_sent": False}
    else:
        state["audio_sent"] = False

    ok = await send_listening_audio(callback.message.chat.id, item)
    if ok:
        LISTENING_QUIZ_STATE[uid]["audio_sent"] = True
        await callback.message.answer("❓ Продолжаем вопросы.")


@dp.callback_query(F.data.startswith("listen_ans:"))
async def cb_listen_answer(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return

    _, listen_id, q_index_str, opt_index_str = parts
    q_index = int(q_index_str)
    opt_index = int(opt_index_str)

    state = LISTENING_QUIZ_STATE.get(uid)
    if not state or state.get("listen_id") != listen_id:
        await callback.answer("Состояние потеряно. Запусти аудирование заново.", show_alert=True)
        return

    if not state.get("audio_sent", False):
        await callback.answer("Сначала нажми ▶ Слушать.", show_alert=True)
        return

    if q_index != int(state.get("index", 0)):
        await callback.answer()
        return

    item = LISTENING_BY_ID.get(listen_id)
    if not item:
        await callback.answer("Аудирование не найдено.", show_alert=True)
        return

    questions = item.get("questions", [])
    if q_index >= len(questions):
        await callback.answer()
        return

    correct_index = int(questions[q_index].get("correct_index", 0))
    if opt_index == correct_index:
        state["score"] = int(state.get("score", 0)) + 1
        await callback.answer("Правильно ✅")
    else:
        await callback.answer("Неправильно ❌")

    state["index"] = q_index + 1

    if state["index"] >= len(questions):
        total = len(questions)
        score = int(state.get("score", 0))
        await callback.message.answer(
            f"✅ Готово.\n\nРезультат: {score}/{total}",
            reply_markup=kb_listening_finish(listen_id)
        )
        return

    await send_listening_question(callback.message.chat.id, listen_id, state["index"])

# ==========================
# CALLBACK: СЛОВА
# ==========================

@dp.callback_query(F.data == "menu_words")
async def cb_menu_words(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    kb = build_themes_keyboard()
    await callback.message.answer(
        "Выбери уровень, затем тему и подтему. В скобках показано количество слов.",
        reply_markup=kb,
    )


@dp.callback_query(F.data == "menu_answer_mode")
async def cb_menu_answer_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.answer()
    current_mode = user_state[uid].get("mode", "de_ru")
    current_answer = user_state[uid].get("answer_mode", "choice")
    kb = build_full_format_keyboard(current_mode, current_answer)
    text = (
        "⚙️ Формат ответа.\n\n"
        "1) Направление перевода:\n"
        "   • 🇩🇪 -> 🇷🇺 Немецкое слово -> выбираешь перевод на русский\n"
        "   • 🇷🇺 -> 🇩🇪 Русское слово -> выбираешь или вводишь вариант на немецком\n\n"
        "2) Формат ответа:\n"
        "   • Варианты ответа (4) - как тест\n"
        "   • Ввод слова вручную - ты пишешь немецкое слово сам"
    )
    await callback.message.answer(text, reply_markup=kb)


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

    _, topic_id = callback.data.split("|", maxsplit=1)

    if topic_id not in TOPIC_KEY_BY_ID:
        await callback.answer("Тема не найдена.", show_alert=True)
        return

    level, topic = TOPIC_KEY_BY_ID[topic_id]

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

    _, sub_id = callback.data.split("|", maxsplit=1)

    if sub_id not in SUBTOPIC_KEY_BY_ID:
        await callback.answer("Подтема не найдена.", show_alert=True)
        return

    level, topic, subtopic = SUBTOPIC_KEY_BY_ID[sub_id]

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
    if mode not in ("de_ru", "ru_de"):
        await callback.answer("Неизвестное направление.", show_alert=True)
        return

    user_state[uid]["mode"] = mode
    save_user_state()

    await callback.answer("Направление перевода обновлено.")

    current_mode = user_state[uid].get("mode", "de_ru")
    current_answer = user_state[uid].get("answer_mode", "choice")
    kb = build_full_format_keyboard(current_mode, current_answer)

    if mode == "de_ru":
        txt = "Теперь я буду показывать немецкое слово, а ты отвечаешь по русски."
    else:
        txt = "Теперь я буду показывать русское слово, а ты отвечаешь по немецки."

    try:
        await callback.message.edit_text(txt, reply_markup=kb)
    except Exception:
        await callback.message.answer(txt, reply_markup=kb)


@dp.callback_query(F.data.startswith("answer_mode|"))
async def cb_answer_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, mode = callback.data.split("|", maxsplit=1)
    if mode not in ("choice", "typing"):
        await callback.answer("Неизвестный формат ответа.", show_alert=True)
        return

    state = user_state[uid]
    state["answer_mode"] = mode
    state["waiting_text_answer"] = False
    state["current_word_id"] = None
    save_user_state()

    await callback.answer("Формат ответа обновлен.")

    current_mode = state.get("mode", "de_ru")
    current_answer = state.get("answer_mode", "choice")
    kb = build_full_format_keyboard(current_mode, current_answer)

    if mode == "choice":
        text = "Теперь формат ответа: варианты.\n\nПо каждому слову будет 4 варианта ответа на кнопках."
    else:
        text = "Теперь формат ответа: ввод слова вручную.\n\nЯ показываю русское слово, а ты пишешь его по немецки."

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)


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
            text = "✅ Правильно.\n\n" f'{w["de"]} ({w["tr"]}) - {w["ru"]}'
        else:
            text = "✅ Правильно.\n\n" f'{w["ru"]} - {w["de"]} ({w["tr"]})'

        finished_now = not state["remaining"]
        if finished_now:
            current_topic = state.get("topic", TOPIC_ALL)
            correct = state.get("correct", 0)
            wrong = state.get("wrong", 0)
            update_topic_stats(uid, current_topic, correct, wrong)

            text += (
                "\n\nТы прошел все слова в этой подборке.\n"
                f"✅ Правильных ответов: {state['correct']}\n"
                f"❌ Неправильных ответов: {state['wrong']}\n\n"
                "Можно выбрать другую подтему в Тренировке слов или начать новую тренировку."
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

# ==========================
# CALLBACK: ГРАММАТИКА
# ==========================

@dp.callback_query(F.data == "grammar_menu")
async def cb_grammar_menu(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    load_grammar_rules()
    if not GRAMMAR_RULES:
        await callback.answer("Правила не найдены.", show_alert=True)
        return

    await callback.message.edit_text("Выбери уровень грамматики:", reply_markup=kb_grammar_levels())
    await callback.answer()


@dp.callback_query(F.data.startswith("grammar_level:"))
async def cb_grammar_level(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, level = callback.data.split(":", 1)
    sublevels = get_sublevels_for_level(level)
    if not sublevels:
        await callback.answer("Для этого уровня пока нет правил.", show_alert=True)
        return
    await callback.message.edit_text(f"Выбери подуровень для {level}:", reply_markup=kb_grammar_sublevels(level))
    await callback.answer()


@dp.callback_query(F.data.startswith("grammar_sub:"))
async def cb_grammar_sub(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, sub = callback.data.split(":", 1)
    rules = get_rules_by_sublevel(sub)
    if not rules:
        await callback.answer("В этом подуровне пока нет правил.", show_alert=True)
        return
    await callback.message.edit_text(f"Правила для {sub}:", reply_markup=kb_grammar_rules_list(sub))
    await callback.answer()


@dp.callback_query(F.data.startswith("grammar_rule:"))
async def cb_grammar_rule(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id = callback.data.split(":", 1)
    rule = get_rule_by_id(rule_id)
    if not rule:
        await callback.answer("Правило не найдено.", show_alert=True)
        return

    title_clean = strip_html_tags(rule.get("title", "Правило"))
    expl_clean = strip_html_tags(rule.get("explanation", ""))

    text = f"*{title_clean}*\n\n{expl_clean}"
    await callback.message.edit_text(text, reply_markup=kb_rule_after_explanation(rule_id))
    await callback.answer()


@dp.callback_query(F.data == "grammar_back_rules")
async def cb_grammar_back_rules(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    await callback.message.edit_text("Выбери уровень грамматики:", reply_markup=kb_grammar_levels())
    await callback.answer()


@dp.callback_query(F.data.startswith("grammar_quiz_start:"))
async def cb_quiz_start(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id = callback.data.split(":", 1)
    rule = get_rule_by_id(rule_id)
    if not rule:
        await callback.answer("Правило не найдено.", show_alert=True)
        return

    await callback.answer()

    wait_msg = await callback.message.answer("⌛ Генерирую упражнения по этой теме, подожди немного...")

    questions = await generate_quiz_for_rule(rule)
    if not questions:
        await wait_msg.edit_text("Не удалось создать упражнения для этой темы. Попробуй еще раз позже.")
        return

    USER_QUIZ_STATE[uid] = {
        "rule_id": rule_id,
        "questions": questions,
        "index": 0,
        "correct": 0,
        "wrong": 0,
    }

    await wait_msg.edit_text("Упражнения готовы. Начинаем первый вопрос.", parse_mode=None)
    await send_current_quiz_question(callback.message, uid, new_message=True)


async def send_current_quiz_question(message: Message, user_id: int, new_message: bool = False):
    state = USER_QUIZ_STATE.get(user_id)
    if not state:
        return

    idx = state["index"]
    questions = state["questions"]
    if idx >= len(questions):
        await send_quiz_result(message, user_id)
        return

    q = questions[idx]
    instr_ru = get_quiz_instruction_ru()

    text = (
        "📘 Грамматика: упражнение\n\n"
        f"Вопрос {idx + 1} из {len(questions)}\n\n"
        f"{instr_ru}\n\n"
        f"🇩🇪 {q['question']}"
    )

    kb = kb_quiz_answers(state["rule_id"], idx, q["options"])

    if new_message:
        await message.answer(text, reply_markup=kb, parse_mode=None)
    else:
        try:
            await message.edit_text(text, reply_markup=kb, parse_mode=None)
        except Exception:
            await message.answer(text, reply_markup=kb, parse_mode=None)


@dp.callback_query(F.data.startswith("grammar_quiz_ans:"))
async def cb_quiz_answer(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, rule_id, q_index_str, opt_index_str = callback.data.split(":", 3)
    state = USER_QUIZ_STATE.get(uid)

    if not state or state["rule_id"] != rule_id:
        await callback.answer("Состояние викторины потеряно. Начни заново.", show_alert=True)
        return

    q_index = int(q_index_str)
    opt_index = int(opt_index_str)

    questions = state["questions"]
    if q_index != state["index"]:
        await callback.answer()
        return

    current = questions[q_index]
    correct = int(current.get("correct_index", 0))
    total_questions = len(questions)
    number = q_index + 1

    if opt_index == correct:
        state["correct"] += 1
        update_grammar_stats(uid, rule_id, correct_delta=1)

        state["index"] += 1
        await callback.answer("Правильно ✅")

        if state["index"] >= len(questions):
            await send_quiz_result(callback.message, uid)
            return

        next_q = questions[state["index"]]
        instr_ru = get_quiz_instruction_ru()

        text = (
            "✅ Ответ правильный!\n\n"
            "📘 Грамматика: следующее упражнение\n\n"
            f"Вопрос {state['index'] + 1} из {total_questions}\n\n"
            f"{instr_ru}\n\n"
            f"🇩🇪 {next_q['question']}"
        )

        kb = kb_quiz_answers(rule_id, state["index"], next_q["options"])

        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode=None)

    else:
        state["wrong"] += 1
        update_grammar_stats(uid, rule_id, wrong_delta=1)

        await callback.answer("Неправильно. Попробуй еще раз.", show_alert=False)

        wrong_text = current["options"][opt_index]
        instr_ru = get_quiz_instruction_ru()

        text = (
            "❌ Это неверный ответ.\n\n"
            "📘 Грамматика: упражнение\n\n"
            f"Вопрос {number} из {total_questions}\n\n"
            f"{instr_ru}\n\n"
            f"🇩🇪 {current['question']}\n\n"
            f"Выбранный вариант: {wrong_text}\n"
            "Попробуй еще раз."
        )

        kb = kb_quiz_answers(rule_id, q_index, current["options"])

        try:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode=None)
        except Exception:
            await callback.message.answer(text, reply_markup=kb, parse_mode=None)


async def send_quiz_result(message: Message, user_id: int):
    state = USER_QUIZ_STATE.get(user_id)
    if not state:
        return
    total = len(state["questions"])
    correct = state["correct"]
    wrong = state["wrong"]
    percent = round(correct / total * 100)

    if percent == 100:
        comment = "Отлично! Ты владеешь этой темой на очень высоком уровне."
    elif percent >= 80:
        comment = "Очень хорошо! Есть пара мелочей, которые можно повторить."
    elif percent >= 50:
        comment = "Неплохо, но стоит еще потренироваться."
    else:
        comment = "Пока уровень слабый, лучше повторить правило и пройти упражнения еще раз."

    rule_id = state["rule_id"]

    update_grammar_stats(user_id, rule_id, finished_quiz=True)

    text = (
        "📊 Результат по грамматике\n\n"
        f"Правильных ответов: {correct} из {total} ({percent} %)\n"
        f"Неправильных попыток: {wrong}\n\n"
        f"{comment}"
    )

    await message.edit_text(text, reply_markup=kb_after_quiz(rule_id), parse_mode=None)

# ==========================
# ЗАПУСК
# ==========================

async def main() -> None:
    load_allowed_users()
    load_words("words.json")
    load_user_state()
    if GRAMMAR_FILE.exists():
        load_grammar_rules()
    load_listenings()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
