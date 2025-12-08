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

LETTER_SYSTEM_PROMPT = (
    "Ты опытный преподаватель немецкого языка и экзаменатор уровня A1-B1.\n"
    "Твоя задача - проверять письма на немецком языке и давать подробную обратную связь.\n\n"
    "Всегда отвечай строго в такой структуре на русском языке:\n\n"
    "Исправленный вариант письма:\n"
    "{сюда вставь исправленный вариант письма целиком на немецком}\n\n"
    "Ошибки:\n"
    "1) {первая ошибка: коротко объясни по-русски, приведи неправильный фрагмент и правильный вариант}\n"
    "2) {вторая ошибка и так далее, если есть}\n"
    "Если ошибок нет, напиши: Ошибок не найдено. Письмо грамматически корректно.\n\n"
    "Рекомендации:\n"
    "{2-4 конкретных совета по улучшению письма, например, больше союзов, разнообразить лексику и так далее}\n\n"
    "Примерный уровень письма:\n"
    "{укажи один уровень: A1, A2 или B1 и коротко объясни, почему}\n\n"
    "Оценка по критериям (0-5 баллов):\n"
    "Inhalt: X/5 - {краткий комментарий}\n"
    "Struktur: X/5 - {краткий комментарий}\n"
    "Grammatik: X/5 - {краткий комментарий}\n"
    "Wortschatz: X/5 - {краткий комментарий}\n\n"
    "Всегда соблюдай эту структуру. Не добавляй ничего лишнего вне этих блоков."
)

Word = Dict[str, Any]

# ==========================
# ГРАММАТИКА: КНОПКИ, ПРАВИЛА, ВИКТОРИНЫ
# ==========================

GRAMMAR_FILE = Path("grammar.json")
GRAMMAR_RULES: List[Dict[str, Any]] = []

# user_id -> { "rule_id": str, "questions": [...], "index": int, "correct": int, "wrong": int }
USER_QUIZ_STATE: Dict[int, Dict[str, Any]] = {}

# rule_id -> список вопросов, чтобы не генерировать каждый раз заново
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
    if "—" in topic:
        return topic.split("—", 1)[0].strip()
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
            InlineKeyboardButton(text="Правила уровня А2", callback_data="grammar_level:A2"),
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

# ==========================
# ПИСЬМА: ЗАДАНИЯ
# ==========================

LETTER_TASKS: Dict[str, Dict[str, Dict[str, str]]] = {
    "A1": {
        "einladung": {
            "title": "💌 Приглашение (Einladung)",
            "instruction": (
                "Напиши короткое письмо-приглашение на немецком.\n"
                "3-5 предложений. Укажи:\n"
                "• кого ты приглашаешь\n"
                "• куда\n"
                "• когда\n"
                "• что вы будете делать\n"
                "\n"
                "Пиши в неформальном стиле, как другу."
            ),
        },
        "vorstellen": {
            "title": "😊 Поздороваться и представиться",
            "instruction": (
                "Напиши письмо, в котором ты здороваешься и представляешься.\n"
                "3-5 предложений. Укажи:\n"
                "• как тебя зовут\n"
                "• откуда ты\n"
                "• сколько тебе лет\n"
                "• что ты делаешь (учишься или работаешь)\n"
                "\n"
                "Стиль может быть нейтральный или дружелюбный."
            ),
        },
        "freund_nachricht": {
            "title": "📅 Короткое сообщение другу",
            "instruction": (
                "Напиши короткое письмо другу.\n"
                "3-5 предложений. Например:\n"
                "• рассказать, что ты делаешь сегодня\n"
                "• предложить встретиться\n"
                "• спросить, как дела\n"
            ),
        },
        "frage_lehrer": {
            "title": "❓ Вопрос учителю или однокурснику",
            "instruction": (
                "Напиши короткое письмо учителю или однокурснику.\n"
                "3-5 предложений. Укажи:\n"
                "• приветствие\n"
                "• кто ты\n"
                "• твой вопрос (о домашнем задании, экзамене и так далее)\n"
                "• благодарность\n"
            ),
        },
        "termin_absage": {
            "title": "🔄 Отмена или перенос встречи",
            "instruction": (
                "Напиши письмо, в котором ты отменяешь или переносишь встречу.\n"
                "3-5 предложений. Укажи:\n"
                "• на какой день была встреча\n"
                "• почему ты не можешь\n"
                "• новое предложение по времени или просьбу перенести\n"
                "• извинение\n"
            ),
        },
    },
    "A2": {
        "formal_allgemein": {
            "title": "📬 Формальное письмо",
            "instruction": (
                "Напиши формальное письмо в организацию.\n"
                "5-8 предложений. Используй приветствие типа "
                "\"Sehr geehrte Damen und Herren\".\n"
                "Можешь, например, запросить информацию о курсе, услуге или товаре."
            ),
        },
        "arzt_kasse": {
            "title": "🏥 Письмо врачу или в Krankenkasse",
            "instruction": (
                "Напиши письмо врачу или в медицинскую страховую (Krankenkasse).\n"
                "5-8 предложений. Объясни:\n"
                "• кто ты\n"
                "• какая у тебя проблема или вопрос\n"
                "• с какого времени у тебя проблема\n"
                "• что ты хочешь (Termin, Beratung, Information)\n"
            ),
        },
        "beschwerde": {
            "title": "🛠 Жалоба на услугу или товар",
            "instruction": (
                "Напиши письмо-жалобу.\n"
                "5-8 предложений. Опиши:\n"
                "• что ты купил или заказал\n"
                "• в чем проблема\n"
                "• чего ты ожидаешь (Geld zurück, Reparatur, Austausch)\n"
            ),
        },
        "hausmeister_vermieter": {
            "title": "🔧 Письмо Hausmeister или Vermieter",
            "instruction": (
                "Напиши письмо по поводу квартиры (Hausmeister или Vermieter).\n"
                "5-8 предложений. Объясни:\n"
                "• какая проблема в квартире\n"
                "• с какого времени\n"
                "• что ты просишь сделать\n"
            ),
        },
        "verkehrsbetrieb": {
            "title": "🚌 Письмо в транспортную компанию",
            "instruction": (
                "Напиши письмо в транспортную компанию (например, о проблеме с билетом "
                "или опозданием поезда).\n"
                "5-8 предложений. Опиши ситуацию и чего ты ожидаешь."
            ),
        },
        "termin_verschieben": {
            "title": "⏰ Перенос термина",
            "instruction": (
                "Напиши формальное письмо с просьбой перенести термин.\n"
                "5-8 предложений. Укажи старую дату, причину и желательное новое время."
            ),
        },
        "anfrage_info": {
            "title": "📝 Запрос информации (Anfrage)",
            "instruction": (
                "Напиши письмо-запрос информации.\n"
                "5-8 предложений. Объясни кратко, кто ты, и какие именно "
                "детали тебя интересуют."
            ),
        },
    },
    "B1": {
        "erlebnis": {
            "title": "🧾 Письмо-рассказ (опыт или ситуация)",
            "instruction": (
                "Напиши письмо, где ты рассказываешь о какой-то ситуации или опыте.\n"
                "8-12 предложений. Опиши:\n"
                "• где и когда это было\n"
                "• что произошло\n"
                "• как ты себя чувствовал\n"
                "• чем все закончилось\n"
            ),
        },
        "beschwerde_argumente": {
            "title": "🛒 Жалоба с аргументами",
            "instruction": (
                "Напиши подробную жалобу.\n"
                "8-12 предложений. Используй несколько аргументов, приведи примеры, "
                "вежливо, но четко объясни, чего ты ожидаешь."
            ),
        },
        "firma_bewerbung_light": {
            "title": "🏢 Письмо в фирму или Bewerbung light",
            "instruction": (
                "Напиши письмо в фирму (запрос работы, Praktikum или Information).\n"
                "8-12 предложений. Кратко расскажи о себе и объясни, что ты ищешь."
            ),
        },
        "detail_anfrage": {
            "title": "🧐 Запрос подробной информации",
            "instruction": (
                "Напиши письмо, в котором ты подробно спрашиваешь информацию.\n"
                "8-12 предложений. Задай несколько конкретных вопросов."
            ),
        },
        "bewertung_meinung": {
            "title": "💬 Отзыв или мнение (Bewertung)",
            "instruction": (
                "Напиши письмо-отзыв. Например, о курсе, отеле или товаре.\n"
                "8-12 предложений. Укажи плюсы, минусы и свое мнение."
            ),
        },
        "konflikt_situation": {
            "title": "📍 Сложная ситуация (опоздание, конфликт, ошибка)",
            "instruction": (
                "Напиши письмо-объяснение сложной ситуации.\n"
                "8-12 предложений. Опиши, что случилось, почему так вышло "
                "и что ты предлагаешь сделать."
            ),
        },
    },
}

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
        "answer_mode": "choice",
        "waiting_text_answer": False,
        "current_word_id": None,
        "grammar_stats": {
            "total_correct": 0,
            "total_wrong": 0,
            "per_rule": {}
        },
        "letter_mode": False,
        "letter_task": None,
        "letter_stats": {
            "checked": 0
        },
        # Путь интеграции
        "integration_progress": 0,   # индекс открытой темы
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
SUBTOPIC_ID_BY_KEY: Dict[Tuple[str, str, str], str] = {}
SUBTOPIC_KEY_BY_ID: Dict[str, Tuple[str, str, str]] = {}

# ==========================
# ПУТЬ ИНТЕГРАЦИИ: ТЕМЫ
# ==========================

INTEGRATION_TOPICS: List[Dict[str, str]] = [
    {
        "id": "a1_1_intro",
        "title": "A1.1 Знакомство",
        "goal": "Познакомиться с людьми на интеграционном курсе.",
    },
    {
        "id": "a1_1_greetings",
        "title": "A1.1 Приветствия и вежливость",
        "goal": "Научиться здороваться и прощаться в разных ситуациях.",
    },
    {
        "id": "a1_1_numbers_time",
        "title": "A1.1 Числа и время",
        "goal": "Понимать время и договариваться о встречах.",
    },
    # Потом добавишь сюда остальные темы по плану.
]


def get_integration_progress(uid: int) -> int:
    state = user_state[uid]
    try:
        return int(state.get("integration_progress", 0))
    except Exception:
        return 0


def set_integration_progress(uid: int, index: int) -> None:
    state = user_state[uid]
    state["integration_progress"] = max(0, index)
    user_state[uid] = state
    save_user_state()


def complete_integration_topic(uid: int, topic_id: str) -> None:
    """
    Отмечаем тему как пройденную и открываем следующую.
    """
    current_index = get_integration_progress(uid)
    index = None
    for i, t in enumerate(INTEGRATION_TOPICS):
        if t["id"] == topic_id:
            index = i
            break
    if index is None:
        return
    if index >= current_index:
        set_integration_progress(uid, index + 1)


def build_integration_topics_keyboard(uid: int) -> InlineKeyboardMarkup:
    progress_index = get_integration_progress(uid)

    buttons: List[List[InlineKeyboardButton]] = []
    for index, topic in enumerate(INTEGRATION_TOPICS):
        is_open = index <= progress_index
        status_emoji = "🔓" if is_open else "🔒"
        text = f"{status_emoji} {topic['title']}"
        if is_open:
            cb = f"integration_topic_open:{topic['id']}"
        else:
            cb = "integration_locked"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=cb)]
        )

    buttons.append(
        [InlineKeyboardButton(text="⬅ Главное меню", callback_data="back_main")]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_integration_path(message: Message, uid: int, edit: bool = False) -> None:
    # Если пользователь еще не начинал, пусть будет открыта первая тема
    if "integration_progress" not in user_state[uid]:
        set_integration_progress(uid, 0)

    text = (
        "📍 Путь интеграции\n\n"
        "Каждая тема открывается только после прохождения предыдущей.\n"
        "Каждая тема имеет свою мини цель.\n"
        "Ты проходишь путь так же как в реальной жизни:\n"
        "от знакомства до работы, писем, врачей и официальных дел.\n\n"
        "Выбери доступную тему ниже."
    )
    kb = build_integration_topics_keyboard(uid)

    if edit:
        try:
            await message.edit_text(text, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)
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
# СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЕЙ: ЗАГРУЗКА/СОХРАНЕНИЕ
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
        print(f"Файл {path} не найден. Положи words.json рядом с main.py")
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


def build_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛣 Путь интеграции",
                    callback_data="menu_integration",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧠 Тренировать слова",
                    callback_data="menu_words",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📘 Грамматика",
                    callback_data="grammar_menu",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📬 Учимся писать письма",
                    callback_data="menu_letters",
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
                    text="⚙️ Формат ответа",
                    callback_data="menu_answer_mode",
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


def build_back_to_main_row() -> List[List[InlineKeyboardButton]]:
    return [
        [
            InlineKeyboardButton(
                text="⬅️ Главное меню",
                callback_data="back_main",
            )
        ]
    ]


def build_themes_keyboard() -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []

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
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{topic} ({count})",
                    callback_data=f"topic_select|{topic_id}",
                )
            ]
        )

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
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{subtopic} ({count})",
                    callback_data=f"subtopic|{sub_id}",
                )
            ]
        )

    rows.extend(build_back_to_main_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_mode_keyboard_for_settings(current_mode: str) -> List[List[InlineKeyboardButton]]:
    de_selected = "✅ " if current_mode == "de_ru" else ""
    ru_selected = "✅ " if current_mode == "ru_de" else ""
    return [
        [
            InlineKeyboardButton(
                text=f"{de_selected}🇩🇪 -> 🇷🇺 Немецкое слово",
                callback_data="mode|de_ru",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{ru_selected}🇷🇺 -> 🇩🇪 Русское слово",
                callback_data="mode|ru_de",
            )
        ],
    ]


def build_answer_mode_keyboard(current_answer: str) -> List[List[InlineKeyboardButton]]:
    choice_mark = "✅ " if current_answer == "choice" else ""
    typing_mark = "✅ " if current_answer == "typing" else ""
    return [
        [
            InlineKeyboardButton(
                text=f"{choice_mark}Варианты ответа (4)",
                callback_data="answer_mode|choice",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{typing_mark}Ввод слова вручную",
                callback_data="answer_mode|typing",
            )
        ],
    ]


def build_full_format_keyboard(current_mode: str, current_answer: str) -> InlineKeyboardMarkup:
    rows: List[List[InlineKeyboardButton]] = []
    rows.extend(build_mode_keyboard_for_settings(current_mode))
    rows.extend(build_answer_mode_keyboard(current_answer))
    rows.extend(build_back_to_main_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==========================
# КЛАВИАТУРЫ ДЛЯ ПИСЕМ
# ==========================


def build_letter_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏ A1 - Простые письма",
                    callback_data="letter_level|A1",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✉ A2 - Бытовые и формальные письма",
                    callback_data="letter_level|A2",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📝 B1 - Экзаменационные письма",
                    callback_data="letter_level|B1",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📚 Шаблоны писем",
                    callback_data="letter_templates",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧪 Практика: проверить мое письмо",
                    callback_data="letter_practice",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Мой прогресс по письмам",
                    callback_data="letter_progress",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅ Главное меню",
                    callback_data="back_main",
                )
            ],
        ]
    )


def build_letter_tasks_keyboard(level: str) -> InlineKeyboardMarkup:
    tasks = LETTER_TASKS.get(level, {})
    rows: List[List[InlineKeyboardButton]] = []

    for task_key, task_data in tasks.items():
        title = task_data.get("title", task_key)
        rows.append(
            [
                InlineKeyboardButton(
                    text=title,
                    callback_data=f"letter_task|{level}|{task_key}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅ Назад к письмам",
                callback_data="menu_letters",
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)

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
# ПРОВЕРКА ПРЕДЛОЖЕНИЙ И ПИСЕМ
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


async def check_letter_with_ai(text: str) -> str:
    if client is None:
        return (
            "Проверка писем сейчас недоступна.\n"
            "Обратись к администратору."
        )

    prompt_user = (
        "Ниже текст письма на немецком языке. Это письмо ученика уровня от A1 до B1.\n"
        "Проверь письмо по инструкции.\n\n"
        "Текст письма:\n"
        f"{text}"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": LETTER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_user},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        answer = completion.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print("Ошибка при проверке письма:", e)
        return "Произошла ошибка при проверке письма. Попробуй еще раз позже."
# ==========================
# КОМАНДЫ
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
            "Этот бот помогает улучшать немецкий язык через слова, темы, грамматику, письма и проверку предложений.\n\n"
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
        "• Учиться писать письма (A1-A2-B1)\n"
        "• Проверять свои предложения\n"
        "• Проходить Путь интеграции от A1 до B1\n"
        "• Смотреть статистику по темам\n\n"
        f"Сейчас в базе {total_words} слов.\n"
        f"Тем: {total_topics}, подтем: {total_subtopics}.\n\n"
        "Используй главное меню ниже, чтобы выбрать режим."
    )

    kb = build_main_menu_keyboard()
    await message.answer(text, reply_markup=kb)

    state = user_state[uid]
    state["check_mode"] = False
    state["letter_mode"] = False
    user_state[uid] = state
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
                    callback_data=f"allow|{uid}",
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

    current_mode = user_state[uid].get("mode", "de_ru")
    current_answer = user_state[uid].get("answer_mode", "choice")
    kb = build_full_format_keyboard(current_mode, current_answer)
    await message.answer(
        "Здесь ты можешь настроить направление перевода и формат ответа.",
        reply_markup=kb,
    )


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

    state = user_state[uid]
    state["check_mode"] = True
    state["letter_mode"] = False
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

    # 1) РЕЖИМ ПИСЕМ
    if state.get("letter_mode", False):
        waiting_msg = await message.answer("⌛ Проверяю письмо...")
        result = await check_letter_with_ai(text)

        stats = state.get("letter_stats", {"checked": 0})
        stats["checked"] = stats.get("checked", 0) + 1
        state["letter_stats"] = stats
        user_state[uid] = state
        save_user_state()

        await waiting_msg.edit_text(result)
        return

    # 2) РЕЖИМ ПРОВЕРКИ ПРЕДЛОЖЕНИЙ
    if state.get("check_mode", False):
        waiting_msg = await message.answer("⌛ Проверяю предложение...")
        result = await check_text_with_ai(text)
        await waiting_msg.edit_text(result)
        return

    # 3) РЕЖИМ ВВОДА НЕМЕЦКОГО СЛОВА ВРУЧНУЮ
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

            reply = (
                "✅ Правильно.\n\n"
                f'{w["de"]} ({w["tr"]}) - {w["ru"]}'
            )
            await message.answer(reply)
        else:
            state["wrong"] += 1
            state["waiting_text_answer"] = False
            state["current_word_id"] = None
            save_user_state()

            reply = (
                "❌ Неправильно.\n\n"
                f"Правильный ответ:\n"
                f'{w["de"]} ({w["tr"]}) - {w["ru"]}\n\n'
                "Пиши только немецкое слово, без транскрипции."
            )
            await message.answer(reply)

        await send_new_word(uid, message.chat.id)
        return
# ==========================
# CALLBACK — ГЛАВНОЕ МЕНЮ
# ==========================


@dp.callback_query(F.data == "back_main")
async def cb_back_main(cb: CallbackQuery) -> None:
    await cb.message.answer("Главное меню:", reply_markup=build_main_menu_keyboard())
    await cb.answer()


@dp.callback_query(F.data == "menu_integration")
async def cb_menu_integration(cb: CallbackQuery) -> None:
    await send_integration_path(cb.message.chat.id)
    await cb.answer()


@dp.callback_query(F.data == "menu_words")
async def cb_menu_words(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "Выбери уровень или тему слов:", reply_markup=build_themes_keyboard()
    )
    await cb.answer()


@dp.callback_query(F.data == "menu_letters")
async def cb_menu_letters(cb: CallbackQuery) -> None:
    await cb.message.answer(
        "Учимся писать письма — выбери уровень:",
        reply_markup=build_letter_main_keyboard(),
    )
    await cb.answer()


@dp.callback_query(F.data == "menu_check")
async def cb_menu_check(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    state = user_state[uid]
    state["check_mode"] = True
    state["letter_mode"] = False
    save_user_state()

    await cb.message.answer(
        "✏ Режим проверки предложений включён.\n"
        "Напиши любое предложение на немецком, я проверю.",
    )
    await cb.answer()


@dp.callback_query(F.data == "menu_answer_mode")
async def cb_menu_answer_mode(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    state = user_state[uid]

    mode = state.get("mode", "de_ru")
    answer_mode = state.get("answer_mode", "choice")

    kb = build_full_format_keyboard(mode, answer_mode)
    await cb.message.answer(
        "Настройки формата тренировки:",
        reply_markup=kb,
    )
    await cb.answer()


@dp.callback_query(F.data == "menu_stats")
async def cb_menu_stats(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    text = build_user_stats_text(uid)
    await cb.message.answer(text)
    await cb.answer()


# ==========================
# CALLBACK — ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ
# ==========================


@dp.callback_query(F.data.startswith("allow|"))
async def cb_allow_user(cb: CallbackQuery) -> None:
    if cb.from_user.id != ADMIN_ID:
        await cb.answer("Нет прав.", show_alert=True)
        return

    try:
        uid = int(cb.data.split("|")[1])
    except Exception:
        await cb.answer("Ошибка ID.")
        return

    allowed_users.add(uid)
    save_allowed_users()

    await bot.send_message(uid, "🎉 Твой доступ к боту одобрен. Добро пожаловать!")
    await cb.message.answer(f"Готово. Пользователь {uid} добавлен.")
    await cb.answer()


@dp.callback_query(F.data == "req_access")
async def cb_request_access(cb: CallbackQuery) -> None:
    uid = cb.from_user.id

    txt = (
        "🆕 Запрос на доступ:\n"
        f"Имя: {cb.from_user.full_name}\n"
        f"ID: {uid}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Разрешить доступ",
                    callback_data=f"allow|{uid}",
                )
            ]
        ]
    )

    await bot.send_message(ADMIN_ID, txt, reply_markup=kb)
    await cb.message.answer("Запрос отправлен. Жди одобрения администратора.")
    await cb.answer()


# ==========================
# CALLBACK — ВЫБОР ТЕМ И ПОДТЕМ
# ==========================


@dp.callback_query(F.data == "topic_all")
async def cb_topic_all(cb: CallbackQuery) -> None:
    uid = cb.from_user.id

    st = user_state[uid]
    st["topic"] = TOPIC_ALL
    st["remaining"] = None
    st["correct"] = 0
    st["wrong"] = 0
    save_user_state()

    await cb.message.answer(
        "Выбраны *все слова*.\nЧтобы начать тренировку — напиши /next",
        parse_mode="Markdown",
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("level|"))
async def cb_select_level(cb: CallbackQuery) -> None:
    _, level = cb.data.split("|")

    await cb.message.answer(
        f"Уровень {level}. Теперь выбери тему:",
        reply_markup=build_topics_keyboard_for_level(level),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("topic_select|"))
async def cb_select_topic(cb: CallbackQuery) -> None:
    _, topic_id = cb.data.split("|")
    key = TOPIC_KEY_BY_ID.get(topic_id)

    if not key:
        await cb.answer("Ошибка темы.", show_alert=True)
        return

    level, topic = key

    await cb.message.answer(
        f"Тема: {topic}\nВыбери подтему:",
        reply_markup=build_subtopics_keyboard(level, topic),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("subtopic|"))
async def cb_select_subtopic(cb: CallbackQuery) -> None:
    _, sid = cb.data.split("|")
    key = SUBTOPIC_KEY_BY_ID.get(sid)

    if not key:
        await cb.answer("Ошибка подтемы.", show_alert=True)
        return

    level, topic, subtopic = key
    topic_key = f"{level}|{topic}|{subtopic}"

    uid = cb.from_user.id
    st = user_state[uid]

    st["topic"] = topic_key
    st["remaining"] = None
    st["correct"] = 0
    st["wrong"] = 0
    save_user_state()

    await cb.message.answer(
        f"Подтема выбрана: {subtopic}\nЧтобы начать — введи /next"
    )
    await cb.answer()


# ==========================
# CALLBACK — ИНТЕРАКТИВНЫЕ РЕЖИМЫ (mode, answer mode)
# ==========================


@dp.callback_query(F.data.startswith("mode|"))
async def cb_change_mode(cb: CallbackQuery) -> None:
    _, mode = cb.data.split("|")
    uid = cb.from_user.id

    state = user_state[uid]
    state["mode"] = mode
    save_user_state()

    kb = build_full_format_keyboard(mode, state.get("answer_mode", "choice"))

    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer(f"Режим обновлён: {mode}")


@dp.callback_query(F.data.startswith("answer_mode|"))
async def cb_change_answer_mode(cb: CallbackQuery) -> None:
    _, am = cb.data.split("|")
    uid = cb.from_user.id

    state = user_state[uid]
    state["answer_mode"] = am
    save_user_state()

    kb = build_full_format_keyboard(state.get("mode", "de_ru"), am)

    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer("Формат ответа обновлён.")


# ==========================
# CALLBACK — ПИСЬМА
# ==========================


@dp.callback_query(F.data.startswith("letter_level|"))
async def cb_letter_level(cb: CallbackQuery) -> None:
    _, level = cb.data.split("|")

    kb = build_letter_tasks_keyboard(level)
    await cb.message.answer(
        f"Ты выбрал уровень {level}. Теперь выбери тип письма:",
        reply_markup=kb,
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("letter_task|"))
async def cb_letter_task(cb: CallbackQuery) -> None:
    _, level, task_key = cb.data.split("|")

    task = LETTER_TASKS.get(level, {}).get(task_key)
    if not task:
        await cb.answer("Ошибка письма.", show_alert=True)
        return

    title = task.get("title", task_key)
    points = task.get("points", [])

    text = f"📬 Письмо: {title}\n\nТвоё задание:\n"
    for p in points:
        text += f"• {p}\n"

    text += "\nНапиши письмо ниже, я проверю его."

    uid = cb.from_user.id
    state = user_state[uid]
    state["letter_mode"] = True
    save_user_state()

    await cb.message.answer(text)
    await cb.answer()


@dp.callback_query(F.data == "letter_templates")
async def cb_letter_templates(cb: CallbackQuery) -> None:
    text = (
        "📚 Шаблоны писем пока в разработке.\n"
        "Скоро появятся готовые структуры для A1-A2-B1."
    )
    await cb.message.answer(text)
    await cb.answer()


@dp.callback_query(F.data == "letter_practice")
async def cb_letter_practice(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    st = user_state[uid]
    st["letter_mode"] = True
    save_user_state()

    await cb.message.answer(
        "Напиши любое письмо на немецком, я исправлю и объясню ошибки."
    )
    await cb.answer()


@dp.callback_query(F.data == "letter_progress")
async def cb_letter_progress(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    st = user_state[uid]
    ls = st.get("letter_stats", {})

    checked = ls.get("checked", 0)

    text = (
        "📊 Прогресс по письмам:\n\n"
        f"Писем проверено: {checked}"
    )

    await cb.message.answer(text)
    await cb.answer()


# ==========================
# CALLBACK — ТРЕНИРОВКА СЛОВ (ответы)
# ==========================


@dp.callback_query(F.data.startswith("ans|"))
async def cb_answer_word(cb: CallbackQuery) -> None:
    uid = cb.from_user.id
    chat_id = cb.message.chat.id

    _, correct_id, mode, is_correct = cb.data.split("|")
    correct_id = int(correct_id)
    is_correct = int(is_correct)

    st = user_state[uid]

    if is_correct:
        st["correct"] += 1
        save_user_state()

        w = WORDS[correct_id]
        text = (
            "✅ Правильно!\n\n"
            f'{w["de"]} ({w["tr"]}) - {w["ru"]}'
        )
        await cb.message.answer(text)
        await send_new_word(uid, chat_id)
    else:
        st["wrong"] += 1
        save_user_state()

        await resend_same_word(chat_id, correct_id, mode, uid)

    await cb.answer()


# ==========================
# УРОК 1 A1.1 — ANKOMMEN (TONI)
# ==========================

from aiogram import Router as LessonRouter

lesson1_router = LessonRouter()

# Память в рантайме. Потом можно заменить на БД.
USER_L1_NAME: Dict[int, str] = {}
USER_L1_WAIT_NAME: Dict[int, bool] = {}


# ------------- ВСПОМОГАТЕЛЬНЫЕ КНОПКИ УРОКА 1 -------------

def kb_l1_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶ Начать урок", callback_data="l1_start")]
        ]
    )


def kb_l1_hallo_silent() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👋 Hallo", callback_data="l1_b2_hallo")],
            [InlineKeyboardButton(text="🤫 Ничего не говорить", callback_data="l1_b2_silent")],
        ]
    )


def kb_l1_hallo_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👋 Hallo", callback_data="l1_b2_force_hallo")]
        ]
    )


def kb_l1_continue_block4() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶ Продолжить", callback_data="l1_block5")]
        ]
    )


def kb_l1_block6_next() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✔ Я понял", callback_data="l1_block7")]
        ]
    )


def kb_l1_block7_next() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶ Дальше", callback_data="l1_block8")]
        ]
    )


def kb_l1_vocab_next() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Хочу мини тест", callback_data="l1_test_q1")]
        ]
    )


def kb_l1_finish_next() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➡ Перейти к уроку 2", callback_data="l1_go_lesson2")]
        ]
    )


# ------------- БЛОК 5: ВОПРОС "Я Alex" -------------

def kb_l1_block5_answers(user_name: str) -> InlineKeyboardMarkup:
    # Варианты: Ich bin Name, Du bist Name, Ich bin Toni
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Ich bin {user_name}.", callback_data="l1_b5_opt1")],
            [InlineKeyboardButton(text=f"Du bist {user_name}.", callback_data="l1_b5_opt2")],
            [InlineKeyboardButton(text="Ich bin Toni.", callback_data="l1_b5_opt3")],
        ]
    )


async def send_l1_block5_question(message_or_cb):
    """
    Показываем вопрос Блока 5: "Выбери фразу, которая значит 'Я Alex'."
    message_or_cb - это либо Message, либо CallbackQuery.
    """
    if isinstance(message_or_cb, CallbackQuery):
        user_id = message_or_cb.from_user.id
        send = message_or_cb.message.answer
    else:
        user_id = message_or_cb.from_user.id
        send = message_or_cb.answer

    user_name = USER_L1_NAME.get(user_id, "Alex")

    text = (
        "Давай потренируемся.\n\n"
        f"Выбери фразу, которая значит \"Я {user_name}\"."
    )

    await send(
        text=text,
        reply_markup=kb_l1_block5_answers(user_name)
    )


# ------------- БЛОК 6: МИНИ ДИАЛОГ -------------

def kb_l1_block6_answers(user_name: str) -> InlineKeyboardMarkup:
    # Варианты: Ich bin Name, Du bist Toni, Hallo Name
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Ich bin {user_name}.", callback_data="l1_b6_opt1")],
            [InlineKeyboardButton(text="Du bist Toni.", callback_data="l1_b6_opt2")],
            [InlineKeyboardButton(text=f"Hallo {user_name}.", callback_data="l1_b6_opt3")],
        ]
    )


async def send_l1_block6_question(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = USER_L1_NAME.get(user_id, "Alex")

    text_toni = "Toni:\n\n\"Gut. Jetzt du.\""
    await callback.message.answer(text_toni)

    text = "Выбери, что ты скажешь Toni."
    await callback.message.answer(
        text=text,
        reply_markup=kb_l1_block6_answers(user_name)
    )


# ------------- БЛОК 7: УПРАЖНЕНИЯ Ich / Du -------------

def kb_l1_block7_q1() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ich bin Toni.", callback_data="l1_b7_q1_opt1")],
            [InlineKeyboardButton(text="Du bist Toni.", callback_data="l1_b7_q1_opt2")],
        ]
    )


def kb_l1_block7_q2() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ich bin Toni.", callback_data="l1_b7_q2_opt1")],
            [InlineKeyboardButton(text="Du bist Toni.", callback_data="l1_b7_q2_opt2")],
        ]
    )


# ------------- БЛОК 9: МИНИ ТЕСТ -------------

def kb_l1_test_q1() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Как тебя зовут", callback_data="l1_q1_opt1")],
            [InlineKeyboardButton(text="Как у тебя дела", callback_data="l1_q1_opt2")],
            [InlineKeyboardButton(text="Откуда ты", callback_data="l1_q1_opt3")],
        ]
    )


def kb_l1_test_q2(user_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Ich bin {user_name}.", callback_data="l1_q2_opt1")],
            [InlineKeyboardButton(text=f"Du bist {user_name}.", callback_data="l1_q2_opt2")],
            [InlineKeyboardButton(text="Ich du Alex.", callback_data="l1_q2_opt3")],
        ]
    )


def kb_l1_test_q3() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ich bin Toni.", callback_data="l1_q3_opt1")],
            [InlineKeyboardButton(text="Du bist Toni.", callback_data="l1_q3_opt2")],
            [InlineKeyboardButton(text="Du bin Toni.", callback_data="l1_q3_opt3")],
        ]
    )


# ------------- ХЕНДЛЕРЫ УРОКА 1 -------------


@lesson1_router.message(F.text == "/lesson1")
@lesson1_router.message(F.text == "/a1_1_l1")
async def start_lesson1(message: Message):
    """
    Блок 1. Запуск урока.
    """
    user_id = message.from_user.id
    USER_L1_WAIT_NAME[user_id] = False

    text = (
        "🇩🇪 A1.1 Урок 1\n"
        "Ankommen - Первое знакомство\n\n"
        "Сегодня ты:\n"
        "• Познакомишься с персонажем Toni\n"
        "• Научишься говорить, как тебя зовут\n"
        "• Увидишь в действии фразы \"Ich bin...\" и \"Du bist...\"\n\n"
        "Нажми кнопку, чтобы начать."
    )

    await message.answer(text, reply_markup=kb_l1_start())


@lesson1_router.callback_query(F.data == "l1_start")
async def lesson1_block2(callback: CallbackQuery):
    """
    Блок 2. Сцена вокзал и первое Hallo.
    """
    text = (
        "🚉 Ты стоишь на вокзале в маленьком немецком городе.\n"
        "У тебя чемодан и немного волнения внутри.\n\n"
        "К тебе подходит человек и улыбается."
    )

    await callback.message.answer(text)

    toni_text = 'Toni:\n\n"Hallo! Ich bin Toni."'
    await callback.message.answer(toni_text, reply_markup=kb_l1_hallo_silent())
    await callback.answer()


@lesson1_router.callback_query(F.data == "l1_b2_hallo")
@lesson1_router.callback_query(F.data == "l1_b2_force_hallo")
async def lesson1_block3(callback: CallbackQuery):
    """
    Переход к блоку 3 после "Hallo".
    """
    user_id = callback.from_user.id
    USER_L1_WAIT_NAME[user_id] = True

    toni_text = (
        "Toni:\n\n"
        "\"Schön. Ich bin Toni.\"\n\n"
        "\"Wie heißt du?\""
    )
    hint = (
        "ℹ \"Wie heißt du?\" на русском:\n"
        "\"Как тебя зовут?\"\n\n"
        "Просто напиши свое имя латиницей."
    )

    await callback.message.answer(toni_text)
    await callback.message.answer(hint)
    await callback.answer()


@lesson1_router.callback_query(F.data == "l1_b2_silent")
async def lesson1_block2_silent(callback: CallbackQuery):
    """
    Ветка если игрок выбрал "Ничего не говорить".
    """
    text = (
        "Toni:\n\n"
        "\"Alles gut. Viele sind ein bisschen schüchtern am Anfang.\"\n"
        "(Все хорошо. Многие немного стесняются в начале.)\n\n"
        "\"Versuch es mal. Sag einfach: Hallo.\"\n"
        "(Попробуй еще раз. Скажи просто: \"Hallo\".)"
    )

    await callback.message.answer(text, reply_markup=kb_l1_hallo_only())
    await callback.answer()


@lesson1_router.message()
async def lesson1_catch_name(message: Message):
    """
    Ловим имя, если мы ждем его в уроке 1.
    """
    user_id = message.from_user.id
    if not USER_L1_WAIT_NAME.get(user_id):
        return

    user_name_raw = message.text.strip()
    if not user_name_raw:
        await message.answer("Попробуй еще раз, просто напиши свое имя.")
        return

    USER_L1_NAME[user_id] = user_name_raw
    USER_L1_WAIT_NAME[user_id] = False

    name = user_name_raw

    toni_reply = f'Toni:\n\n"Aha! Du bist {name}. Schön, {name}."'
    await message.answer(toni_reply)

    explain = (
        "✅ Супер. У тебя уже есть два немецких предложения.\n\n"
        "Ich bin Toni. - Я Тони.\n"
        f"Du bist {name}. - Ты {name}.\n\n"
        "Слова:\n"
        "• Ich - я\n"
        "• Du - ты\n"
        "• bin - есть (для \"ich\")\n"
        "• bist - есть (для \"du\")"
    )

    await message.answer(explain, reply_markup=kb_l1_continue_block4())


@lesson1_router.callback_query(F.data == "l1_block5")
async def lesson1_block5(callback: CallbackQuery):
    """
    Блок 5. Повтор фраз кнопками. Вопрос "Я Alex".
    """
    await send_l1_block5_question(callback)
    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_b5_opt"))
async def lesson1_block5_answer(callback: CallbackQuery):
    """
    Обработка ответа блока 5.
    """
    user_id = callback.from_user.id
    user_name = USER_L1_NAME.get(user_id, "Alex")

    data = callback.data

    if data == "l1_b5_opt1":
        # Правильный ответ: Ich bin Name
        text = (
            "✅ Правильно.\n"
            f"Ich bin {user_name}. - \"Я {user_name}.\""
        )
        await callback.message.answer(text)
        # Переход к блоку 6
        await send_l1_block6_question(callback)
    else:
        text = (
            "❌ Почти.\n\n"
            f"\"Ich bin {user_name}.\" - это \"Я {user_name}.\".\n"
            f"\"Du bist {user_name}.\" - это \"Ты {user_name}.\".\n\n"
            "Попробуем еще раз."
        )
        await callback.message.answer(text)
        await send_l1_block5_question(callback)

    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_b6_opt"))
async def lesson1_block6_answer(callback: CallbackQuery):
    """
    Блок 6. Выбор фразы "Ich bin Name".
    """
    user_id = callback.from_user.id
    user_name = USER_L1_NAME.get(user_id, "Alex")
    data = callback.data

    if data == "l1_b6_opt1":
        # Правильный ответ
        toni = f'Toni:\n\n"Super, {user_name}."\n"Ich bin Toni. Du bist {user_name}."'
        await callback.message.answer(toni)

        explain = (
            "Видишь разницу:\n\n"
            f"• Ich bin {user_name}. - Я {user_name}.\n"
            f"• Du bist {user_name}. - Ты {user_name}.\n\n"
            "Ты уже понимаешь целых два предложения на немецком."
        )
        await callback.message.answer(explain, reply_markup=kb_l1_block6_next())
    else:
        text = (
            "Сначала лучше представиться самому.\n\n"
            f"Выбери: \"Ich bin {user_name}.\""
        )
        await callback.message.answer(text)
        await send_l1_block6_question(callback)

    await callback.answer()


@lesson1_router.callback_query(F.data == "l1_block7")
async def lesson1_block7(callback: CallbackQuery):
    """
    Блок 7. Упражнение на Ich / Du.
    """
    q1 = (
        "Давай быстро проверим, чувствуешь ли ты разницу между Ich и Du.\n\n"
        "Задание 1:\n\n"
        "Как будет \"Я Toni\"?"
    )
    await callback.message.answer(q1, reply_markup=kb_l1_block7_q1())
    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_b7_q1_opt"))
async def lesson1_block7_q1_answer(callback: CallbackQuery):
    """
    Ответ на вопрос 1 блока 7.
    """
    if callback.data == "l1_b7_q1_opt1":
        # Ich bin Toni. - правильный
        await callback.message.answer("✅ Отлично, это правильно.\n\nIch bin Toni.")
        # Переход ко второму вопросу
        q2 = (
            "Задание 2:\n\n"
            "Как будет \"Ты Toni\"?"
        )
        await callback.message.answer(q2, reply_markup=kb_l1_block7_q2())
    else:
        await callback.message.answer(
            "❌ Не совсем.\n\n"
            "\"Ich bin Toni.\" - это \"Я Toni\".\n"
            "\"Du bist Toni.\" - это \"Ты Toni\".\n\n"
            "Попробуем еще раз."
        )
        q1 = "Как будет \"Я Toni\"?"
        await callback.message.answer(q1, reply_markup=kb_l1_block7_q1())

    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_b7_q2_opt"))
async def lesson1_block7_q2_answer(callback: CallbackQuery):
    """
    Ответ на вопрос 2 блока 7.
    """
    if callback.data == "l1_b7_q2_opt2":
        # Du bist Toni. - правильный
        await callback.message.answer("✅ Отлично, ты чувствуешь разницу.\n\nDu bist Toni.")
        summary = (
            "🔁 Мини итог:\n\n"
            "Ich bin [Name]. - Я [имя].\n"
            "Du bist [Name]. - Ты [имя].\n\n"
            "Это основа для всего общения."
        )
        await callback.message.answer(summary, reply_markup=kb_l1_block7_next())
    else:
        await callback.message.answer(
            "❌ Не совсем.\n\n"
            "\"Du bist Toni.\" - это \"Ты Toni\".\n\n"
            "Попробуем еще раз."
        )
        q2 = "Как будет \"Ты Toni\"?"
        await callback.message.answer(q2, reply_markup=kb_l1_block7_q2())

    await callback.answer()


@lesson1_router.callback_query(F.data == "l1_block8")
async def lesson1_block8_vocab(callback: CallbackQuery):
    """
    Блок 8. Мини словарь урока.
    """
    text = (
        "📚 Словарь урока 1\n\n"
        "• Hallo - привет\n"
        "• ich - я\n"
        "• du - ты\n"
        "• bin - есть (с \"ich\")\n"
        "• bist - есть (с \"du\")\n"
        "• ich bin ... - я ...\n"
        "• du bist ... - ты ...\n"
        "• der Name - имя\n"
        "• Deutschland - Германия\n"
        "• willkommen - добро пожаловать\n"
        "• neu - новый\n\n"
        "Не обязательно запомнить все сразу. Главное сейчас - Hallo, Ich bin ..., Wie heißt du?"
    )

    await callback.message.answer(text, reply_markup=kb_l1_vocab_next())
    await callback.answer()


# ------------- МИНИ ТЕСТ УРОКА 1 -------------


@lesson1_router.callback_query(F.data == "l1_test_q1")
async def lesson1_test_q1(callback: CallbackQuery):
    text = (
        "Вопрос 1\n\n"
        "Что значит \"Wie heißt du?\" на русском?"
    )
    await callback.message.answer(text, reply_markup=kb_l1_test_q1())
    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_q1_opt"))
async def lesson1_test_q1_answer(callback: CallbackQuery):
    data = callback.data
    if data == "l1_q1_opt1":
        await callback.message.answer("✅ Правильно. \"Wie heißt du?\" - \"Как тебя зовут\".")
        # Переходим к вопросу 2
        user_id = callback.from_user.id
        user_name = USER_L1_NAME.get(user_id, "Alex")
        text = (
            "Вопрос 2\n\n"
            f"Выбери правильное предложение \"Я {user_name}\"."
        )
        await callback.message.answer(text, reply_markup=kb_l1_test_q2(user_name))
    else:
        await callback.message.answer(
            "❌ Не совсем.\n\n"
            "\"Wie heißt du?\" значит \"Как тебя зовут\".\n"
            "Попробуем еще раз."
        )
        text = "Что значит \"Wie heißt du?\" на русском?"
        await callback.message.answer(text, reply_markup=kb_l1_test_q1())

    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_q2_opt"))
async def lesson1_test_q2_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_name = USER_L1_NAME.get(user_id, "Alex")
    data = callback.data

    if data == "l1_q2_opt1":
        await callback.message.answer(f"✅ Отлично. \"Ich bin {user_name}.\" - \"Я {user_name}.\".")
        # Переходим к вопросу 3
        text = (
            "Вопрос 3\n\n"
            "Представь, ты говоришь с Toni.\n"
            "Как сказать \"Ты Toni\"?"
        )
        await callback.message.answer(text, reply_markup=kb_l1_test_q3())
    else:
        await callback.message.answer(
            "❌ Не совсем.\n\n"
            "Нужна форма \"Ich bin ...\" для \"Я ...\".\n"
            "Попробуем еще раз."
        )
        text = "Выбери правильное предложение:"
        await callback.message.answer(text, reply_markup=kb_l1_test_q2(user_name))

    await callback.answer()


@lesson1_router.callback_query(F.data.startswith("l1_q3_opt"))
async def lesson1_test_q3_answer(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    user_name = USER_L1_NAME.get(user_id, "Alex")

    if data == "l1_q3_opt2":
        # Du bist Toni - правильно
        finish = (
            "🎉 Отлично, урок 1 пройден.\n\n"
            "Теперь ты умеешь:\n"
            "• Поздороваться: Hallo\n"
            f"• Представиться: Ich bin {user_name}.\n"
            "• Понимать и отвечать на \"Wie heißt du?\"\n"
            "• Различать Ich bin и Du bist\n\n"
            "Ты сделал первый шаг в своем виртуальном дне в Германии."
        )
        await callback.message.answer(finish, reply_markup=kb_l1_finish_next())
    else:
        await callback.message.answer(
            "❌ Не совсем.\n\n"
            "\"Du bist Toni.\" - это \"Ты Toni\".\n"
            "Попробуем еще раз."
        )
        text = (
            "Представь, ты говоришь с Toni.\n"
            "Как сказать \"Ты Toni\"?"
        )
        await callback.message.answer(text, reply_markup=kb_l1_test_q3())

    await callback.answer()


@lesson1_router.callback_query(F.data == "l1_go_lesson2")
async def lesson1_go_lesson2(callback: CallbackQuery):
    """
    Заглушка перехода к уроку 2.
    Потом заменишь на реальный запуск второго урока.
    """
    await callback.message.answer("Урок 2 скоро. Пока можешь повторить: /lesson1")
    await callback.answer()
# ==========================
# ПОДКЛЮЧЕНИЕ УРОКА 1 И ЗАПУСК БОТА
# ==========================

# Подключаем router урока 1 к основному диспетчеру
dp.include_router(lesson1_router)


async def main() -> None:
    load_allowed_users()
    load_words("words.json")
    load_user_state()
    if GRAMMAR_FILE.exists():
        load_grammar_rules()

    print("Бот запущен. Ожидаю сообщения пользователей...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
