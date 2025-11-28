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

    Поддерживаются два варианта структуры:

    1) Плоский список:
       [
         {
           "de": "Hallo",
           "tr": "[ха-ло]",
           "ru": "привет",
           "topic": "Приветствия и базовые фразы"
         },
         [
  {
    "de": "Hallo",
    "tr": "ˈhalo",
    "ru": "привет"
  },
  {
    "de": "Guten Tag",
    "tr": "ˌɡuːtn̩ ˈtaːk",
    "ru": "добрый день"
  },
  {
    "de": "Guten Morgen",
    "tr": "ˌɡuːtn̩ ˈmɔʁɡn̩",
    "ru": "доброе утро"
  },
  {
    "de": "Guten Abend",
    "tr": "ˌɡuːtn̩ ˈaːbn̩t",
    "ru": "добрый вечер"
  },
  {
    "de": "Gute Nacht",
    "tr": "ˌɡuːtə ˈnaxt",
    "ru": "спокойной ночи"
  },
  {
    "de": "Tschüss",
    "tr": "tʃʏs",
    "ru": "пока"
  },
  {
    "de": "Auf Wiedersehen",
    "tr": "aʊ̯f ˈviːdɐzeːən",
    "ru": "до свидания"
  },
  {
    "de": "Bis später",
    "tr": "bɪs ˈʃpɛːtɐ",
    "ru": "до позже"
  },
  {
    "de": "Bis morgen",
    "tr": "bɪs ˈmɔʁɡn̩",
    "ru": "до завтра"
  },
  {
    "de": "Willkommen",
    "tr": "vɪlˈkɔmən",
    "ru": "добро пожаловать"
  },
  {
    "de": "Danke",
    "tr": "ˈdaŋkə",
    "ru": "спасибо"
  },
  {
    "de": "Vielen Dank",
    "tr": "ˈfiːlən daŋk",
    "ru": "большое спасибо"
  },
  {
    "de": "Bitte",
    "tr": "ˈbɪtə",
    "ru": "пожалуйста"
  },
  {
    "de": "Entschuldigung",
    "tr": "ɛntˈʃʊldɪɡʊŋ",
    "ru": "извините"
  },
  {
    "de": "Es tut mir leid",
    "tr": "ɛs tuːt miːɐ̯ laɪ̯t",
    "ru": "мне жаль"
  },
  {
    "de": "Ja",
    "tr": "jaː",
    "ru": "да"
  },
  {
    "de": "Nein",
    "tr": "naɪ̯n",
    "ru": "нет"
  },
  {
    "de": "Vielleicht",
    "tr": "fiˈlaɪ̯çt",
    "ru": "возможно"
  },
  {
    "de": "Genau",
    "tr": "ɡəˈnaʊ̯",
    "ru": "верно"
  },
  {
    "de": "Wirklich",
    "tr": "ˈvɪʁklɪç",
    "ru": "действительно"
  },
  {
    "de": "Natürlich",
    "tr": "naˈtyːɐ̯lɪç",
    "ru": "конечно"
  },
  {
    "de": "Klar",
    "tr": "klaːɐ̯",
    "ru": "понятно"
  },
  {
    "de": "Ich verstehe",
    "tr": "ɪç fɛɐ̯ˈʃteːə",
    "ru": "я понимаю"
  },
  {
    "de": "Ich weiß",
    "tr": "ɪç vaɪ̯s",
    "ru": "я знаю"
  },
  {
    "de": "Ich weiß nicht",
    "tr": "ɪç vaɪ̯s nɪçt",
    "ru": "я не знаю"
  },
  {
    "de": "Wie geht’s?",
    "tr": "viː ɡeːts",
    "ru": "как дела?"
  },
  {
    "de": "Gut",
    "tr": "ɡuːt",
    "ru": "хорошо"
  },
  {
    "de": "Sehr gut",
    "tr": "zeːɐ̯ ɡuːt",
    "ru": "очень хорошо"
  },
  {
    "de": "Nicht so gut",
    "tr": "nɪçt zoː ɡuːt",
    "ru": "не очень"
  },
  {
    "de": "Schlecht",
    "tr": "ʃlɛçt",
    "ru": "плохо"
  },
  {
    "de": "Und dir?",
    "tr": "ʊnt diːɐ̯",
    "ru": "а у тебя?"
  },
  {
    "de": "Und Ihnen?",
    "tr": "ʊnt ˈiːnən",
    "ru": "а у вас?"
  },
  {
    "de": "Wie bitte?",
    "tr": "ˈviː ˌbɪtə",
    "ru": "что, простите?"
  },
  {
    "de": "Noch einmal, bitte",
    "tr": "nɔx ˈaɪ̯nmal ˈbɪtə",
    "ru": "ещё раз, пожалуйста"
  },
  {
    "de": "Kein Problem",
    "tr": "kaɪ̯n pʁoˈbleːm",
    "ru": "нет проблем"
  },
  {
    "de": "Alles gut",
    "tr": "ˈaləs ɡuːt",
    "ru": "всё хорошо"
  },
  {
    "de": "Viel Glück",
    "tr": "fiːl ɡlʏk",
    "ru": "удачи"
  },
  {
    "de": "Gute Besserung",
    "tr": "ˌɡuːtə ˈbɛsəʁʊŋ",
    "ru": "выздоравливай"
  },
  {
    "de": "Frohe Weihnachten",
    "tr": "ˌfʁoːə ˈvaɪ̯naxtn̩",
    "ru": "с Рождеством"
  },
  {
    "de": "Guten Rutsch",
    "tr": "ˌɡuːtn̩ ʁʊtʃ",
    "ru": "с наступающим"
  },
  {
    "de": "Herzlichen Glückwunsch",
    "tr": "ˈhɛʁtslɪçən ˈɡlʏkvʊnʃ",
    "ru": "поздравляю"
  },
  {
    "de": "Viel Spaß",
    "tr": "fiːl ʃpaːs",
    "ru": "веселись"
  },
  {
    "de": "Pass auf!",
    "tr": "pas aʊ̯f",
    "ru": "осторожно"
  },
  {
    "de": "Hilfe!",
    "tr": "ˈhɪlfə",
    "ru": "помощь"
  },
  {
    "de": "Achtung!",
    "tr": "axton",
    "ru": "внимание"
  },
  {
    "de": "Ich",
    "tr": "ɪç",
    "ru": "я"
  },
  {
    "de": "Du",
    "tr": "duː",
    "ru": "ты"
  },
  {
    "de": "Er",
    "tr": "eːɐ̯",
    "ru": "он"
  },
  {
    "de": "Sie",
    "tr": "ziː",
    "ru": "она"
  },
  {
    "de": "Es",
    "tr": "ɛs",
    "ru": "оно"
  },
  {
    "de": "Wir",
    "tr": "viːɐ̯",
    "ru": "мы"
  },
  {
    "de": "Ihr",
    "tr": "iːɐ̯",
    "ru": "вы"
  },
  {
    "de": "Sie (plural)",
    "tr": "ziː",
    "ru": "они"
  },
  {
    "de": "Sie (formal)",
    "tr": "ziː",
    "ru": "Вы"
  },
  {
    "de": "Name",
    "tr": "ˈnaːmə",
    "ru": "имя"
  },
  {
    "de": "Vorname",
    "tr": "ˈfoːɐ̯ˌnaːmə",
    "ru": "имя (личное)"
  },
  {
    "de": "Nachname",
    "tr": "ˈnaːxˌnaːmə",
    "ru": "фамилия"
  },
  {
    "de": "Alter",
    "tr": "ˈaltɐ",
    "ru": "возраст"
  },
  {
    "de": "Adresse",
    "tr": "aˈdʁɛsə",
    "ru": "адрес"
  },
  {
    "de": "Straße",
    "tr": "ˈʃtʁaːsə",
    "ru": "улица"
  },
  {
    "de": "Hausnummer",
    "tr": "ˈhaʊ̯sˌnʊmɐ",
    "ru": "номер дома"
  },
  {
    "de": "Wohnort",
    "tr": "ˈvoːnˌʔɔʁt",
    "ru": "место проживания"
  },
  {
    "de": "Stadt",
    "tr": "ʃtat",
    "ru": "город"
  },
  {
    "de": "Land",
    "tr": "lant",
    "ru": "страна"
  },
  {
    "de": "Geburtsdatum",
    "tr": "ɡəˈbʊʁtsˌdaːtʊm",
    "ru": "дата рождения"
  },
  {
    "de": "Geburtsort",
    "tr": "ɡəˈbʊʁtsˌʔɔʁt",
    "ru": "место рождения"
  },
  {
    "de": "Telefon",
    "tr": "ˈteːləfoːn",
    "ru": "телефон"
  },
  {
    "de": "Nummer",
    "tr": "ˈnʊmɐ",
    "ru": "номер"
  },
  {
    "de": "Beruf",
    "tr": "bəˈʁuːf",
    "ru": "профессия"
  },
  {
    "de": "Arbeit",
    "tr": "ˈaʁbaɪ̯t",
    "ru": "работа"
  },
  {
    "de": "Firma",
    "tr": "ˈfɪʁma",
    "ru": "фирма"
  },
  {
    "de": "Student",
    "tr": "ʃtuˈdɛnt",
    "ru": "студент"
  },
  {
    "de": "Schüler",
    "tr": "ˈʃyːlɐ",
    "ru": "школьник"
  },
  {
    "de": "Lehrer",
    "tr": "ˈleːʁɐ",
    "ru": "учитель"
  },
  {
    "de": "Kollege",
    "tr": "kɔˈleːɡə",
    "ru": "коллега"
  },
  {
    "de": "Freund",
    "tr": "fʁɔɪ̯nt",
    "ru": "друг"
  },
  {
    "de": "Freundin",
    "tr": "ˈfʁɔɪ̯ndɪn",
    "ru": "подруга"
  },
  {
    "de": "Familie",
    "tr": "faˈmiːli̯ə",
    "ru": "семья"
  },
  {
    "de": "Vater",
    "tr": "ˈfaːtɐ",
    "ru": "отец"
  },
  {
    "de": "Mutter",
    "tr": "ˈmʊtɐ",
    "ru": "мать"
  },
  {
    "de": "Bruder",
    "tr": "ˈbʁuːdɐ",
    "ru": "брат"
  },
  {
    "de": "Schwester",
    "tr": "ˈʃvɛstɐ",
    "ru": "сестра"
  },
  {
    "de": "Ehemann",
    "tr": "ˈeːəˌman",
    "ru": "муж"
  },
  {
    "de": "Ehefrau",
    "tr": "ˈeːəˌfʁaʊ̯",
    "ru": "жена"
  },
  {
    "de": "Kind",
    "tr": "kɪnt",
    "ru": "ребенок"
  },
  {
    "de": "Sohn",
    "tr": "zoːn",
    "ru": "сын"
  },
  {
    "de": "Tochter",
    "tr": "ˈtɔxtɐ",
    "ru": "дочь"
  },
  {
    "de": "Hobby",
    "tr": "ˈhɔbi",
    "ru": "хобби"
  },
  {
    "de": "Interesse",
    "tr": "ɪntəˈʁɛsə",
    "ru": "интерес"
  },
  {
    "de": "Sprache",
    "tr": "ˈʃpʁaːxə",
    "ru": "язык"
  },
  {
    "de": "Deutsch",
    "tr": "dɔɪ̯tʃ",
    "ru": "немецкий"
  },
  {
    "de": "Englisch",
    "tr": "ˈɛŋlɪʃ",
    "ru": "английский"
  },
  {
    "de": "wohne",
    "tr": "ˈvoːnə",
    "ru": "живу"
  },
  {
    "de": "Person",
    "tr": "pɛʁˈzoːn",
    "ru": "человек"
  },
  {
    "de": "Mann",
    "tr": "man",
    "ru": "мужчина"
  },
  {
    "de": "Frau",
    "tr": "fʁaʊ̯",
    "ru": "женщина"
  },
  {
    "de": "Junge",
    "tr": "ˈjʊŋə",
    "ru": "мальчик"
  },
  {
    "de": "Mädchen",
    "tr": "ˈmɛːtçən",
    "ru": "девочка"
  },
  {
    "de": "Leute",
    "tr": "ˈlɔɪ̯tə",
    "ru": "люди"
  },
  {
    "de": "Körper",
    "tr": "ˈkœʁpɐ",
    "ru": "тело"
  },
  {
    "de": "Kopf",
    "tr": "kɔpf",
    "ru": "голова"
  },
  {
    "de": "Gesicht",
    "tr": "ɡəˈzɪçt",
    "ru": "лицо"
  },
  {
    "de": "Auge",
    "tr": "ˈaʊ̯ɡə",
    "ru": "глаз"
  },
  {
    "de": "Ohren",
    "tr": "ˈoːʁən",
    "ru": "уши"
  },
  {
    "de": "Nase",
    "tr": "ˈnaːzə",
    "ru": "нос"
  },
  {
    "de": "Mund",
    "tr": "mʊnt",
    "ru": "рот"
  },
  {
    "de": "Haare",
    "tr": "ˈhaːʁə",
    "ru": "волосы"
  },
  {
    "de": "Hals",
    "tr": "hals",
    "ru": "шея"
  },
  {
    "de": "Schulter",
    "tr": "ˈʃʊltɐ",
    "ru": "плечо"
  },
  {
    "de": "Arm",
    "tr": "aʁm",
    "ru": "рука"
  },
  {
    "de": "Hand",
    "tr": "hant",
    "ru": "кисть руки"
  },
  {
    "de": "Finger",
    "tr": "ˈfɪŋɐ",
    "ru": "палец"
  },
  {
    "de": "Brust",
    "tr": "bʁʊst",
    "ru": "грудь"
  },
  {
    "de": "Bauch",
    "tr": "baʊ̯x",
    "ru": "живот"
  },
  {
    "de": "Rücken",
    "tr": "ˈʁʏkn̩",
    "ru": "спина"
  },
  {
    "de": "Bein",
    "tr": "baɪ̯n",
    "ru": "нога"
  },
  {
    "de": "Fuß",
    "tr": "fuːs",
    "ru": "ступня"
  },
  {
    "de": "Größe",
    "tr": "ˈɡʁøːsə",
    "ru": "рост"
  },
  {
    "de": "Gewicht",
    "tr": "ɡəˈvɪçt",
    "ru": "вес"
  },
  {
    "de": "groß",
    "tr": "ɡʁoːs",
    "ru": "высокий"
  },
  {
    "de": "klein",
    "tr": "klaɪ̯n",
    "ru": "низкий"
  },
  {
    "de": "dick",
    "tr": "dɪk",
    "ru": "полный"
  },
  {
    "de": "dünn",
    "tr": "dʏn",
    "ru": "худой"
  },
  {
    "de": "alt",
    "tr": "alt",
    "ru": "старый"
  },
  {
    "de": "jung",
    "tr": "jʊŋ",
    "ru": "молодой"
  },
  {
    "de": "schön",
    "tr": "ʃøːn",
    "ru": "красивый"
  },
  {
    "de": "hässlich",
    "tr": "ˈhɛslɪç",
    "ru": "некрасивый"
  },
  {
    "de": "stark",
    "tr": "ʃtaʁk",
    "ru": "сильный"
  },
  {
    "de": "schwach",
    "tr": "ʃvax",
    "ru": "слабый"
  },
  {
    "de": "müde",
    "tr": "ˈmyːdə",
    "ru": "усталый"
  },
  {
    "de": "krank",
    "tr": "kʁaŋk",
    "ru": "больной"
  },
  {
    "de": "gesund",
    "tr": "ɡəˈzʊnt",
    "ru": "здоровый"
  },
  {
    "de": "glücklich",
    "tr": "ˈɡlʏklɪç",
    "ru": "счастливый"
  },
  {
    "de": "traurig",
    "tr": "ˈtʁaʊ̯ʁɪç",
    "ru": "грустный"
  },
  {
    "de": "freundlich",
    "tr": "ˈfʁɔɪ̯ntlɪç",
    "ru": "дружелюбный"
  },
  {
    "de": "nett",
    "tr": "nɛt",
    "ru": "милый"
  },
  {
    "de": "ernst",
    "tr": "ɛʁnst",
    "ru": "серьёзный"
  },
  {
    "de": "laut",
    "tr": "laʊ̯t",
    "ru": "громкий"
  },
  {
    "de": "leise",
    "tr": "ˈlaɪ̯zə",
    "ru": "тихий"
  },
  {
    "de": "langsam",
    "tr": "ˈlaŋzaːm",
    "ru": "медленный"
  },
  {
    "de": "schnell",
    "tr": "ʃnɛl",
    "ru": "быстрый"
  },
  {
    "de": "neu",
    "tr": "nɔɪ̯",
    "ru": "новый"
  },
  {
    "de": "alt (Sache)",
    "tr": "alt",
    "ru": "старый (предмет)"
  },
  {
    "de": "heiß",
    "tr": "haɪ̯s",
    "ru": "горячий"
  },
  {
    "de": "kalt",
    "tr": "kalt",
    "ru": "холодный"
  },
  {
    "de": "die Familie",
    "tr": "diː faˈmiːli̯ə",
    "ru": "семья"
  },
  {
    "de": "der Vater",
    "tr": "ˈfaːtɐ",
    "ru": "отец"
  },
  {
    "de": "die Mutter",
    "tr": "ˈmʊtɐ",
    "ru": "мать"
  },
  {
    "de": "die Eltern",
    "tr": "ˈɛltɐn",
    "ru": "родители"
  },
  {
    "de": "der Sohn",
    "tr": "zoːn",
    "ru": "сын"
  },
  {
    "de": "die Tochter",
    "tr": "ˈtɔxtɐ",
    "ru": "дочь"
  },
  {
    "de": "der Bruder",
    "tr": "ˈbʁuːdɐ",
    "ru": "брат"
  },
  {
    "de": "die Schwester",
    "tr": "ˈʃvɛstɐ",
    "ru": "сестра"
  },
  {
    "de": "der Onkel",
    "tr": "ˈɔŋkl̩",
    "ru": "дядя"
  },
  {
    "de": "die Tante",
    "tr": "ˈtantə",
    "ru": "тётя"
  },
  {
    "de": "der Cousin",
    "tr": "kuˈzɛ̃ː",
    "ru": "кузен"
  },
  {
    "de": "die Cousine",
    "tr": "kuˈziːnə",
    "ru": "кузина"
  },
  {
    "de": "die Großeltern",
    "tr": "ˈɡʁoːsˌʔɛltɐn",
    "ru": "бабушка и дедушка"
  },
  {
    "de": "die Großmutter",
    "tr": "ˈɡʁoːsˌmʊtɐ",
    "ru": "бабушка"
  },
  {
    "de": "der Großvater",
    "tr": "ˈɡʁoːsˌfaːtɐ",
    "ru": "дедушка"
  },
  {
    "de": "das Kind",
    "tr": "kɪnt",
    "ru": "ребёнок"
  },
  {
    "de": "die Kinder",
    "tr": "ˈkɪndɐ",
    "ru": "дети"
  },
  {
    "de": "die Geschwister",
    "tr": "ɡəˈʃvɪstɐ",
    "ru": "братья и сёстры"
  },
  {
    "de": "der Neffe",
    "tr": "ˈnɛfə",
    "ru": "племянник"
  },
  {
    "de": "die Nichte",
    "tr": "ˈnɪçtə",
    "ru": "племянница"
  },
  {
    "de": "die Schwiegereltern",
    "tr": "ˈʃviːɡɐˌʔɛltɐn",
    "ru": "свёкры"
  },
  {
    "de": "die Schwiegermutter",
    "tr": "ˈʃviːɡɐˌmʊtɐ",
    "ru": "свекровь / тёща"
  },
  {
    "de": "der Schwiegervater",
    "tr": "ˈʃviːɡɐˌfaːtɐ",
    "ru": "свёкор / тесть"
  },
  {
    "de": "verheiratet",
    "tr": "fɛɐ̯ˈhaɪ̯ʁatət",
    "ru": "женат / замужем"
  },
  {
    "de": "ledig",
    "tr": "ˈleːdɪç",
    "ru": "холост / не замужем"
  },
  {
    "de": "geschieden",
    "tr": "ɡəˈʃiːdn̩",
    "ru": "разведён"
  },
  {
    "de": "verlobt",
    "tr": "fɛɐ̯ˈloːpt",
    "ru": "помолвлен"
  },
  {
    "de": "die Beziehung",
    "tr": "bəˈt͡siːʊŋ",
    "ru": "отношения"
  },
  {
    "de": "der Partner",
    "tr": "ˈpaʁtnɐ",
    "ru": "партнёр"
  },
  {
    "de": "die Partnerin",
    "tr": "ˈpaʁtnəʁɪn",
    "ru": "партнёрша"
  },
  {
    "de": "die Ehe",
    "tr": "ˈeːə",
    "ru": "брак"
  },
  {
    "de": "der Ehemann",
    "tr": "ˈeːəˌman",
    "ru": "муж"
  },
  {
    "de": "die Ehefrau",
    "tr": "ˈeːəˌfʁaʊ̯",
    "ru": "жена"
  },
  {
    "de": "die Hochzeit",
    "tr": "ˈhɔxˌt͡saɪ̯t",
    "ru": "свадьба"
  },
  {
    "de": "die Scheidung",
    "tr": "ˈʃaɪ̯dʊŋ",
    "ru": "развод"
  },
  {
    "de": "die Liebe",
    "tr": "ˈliːbə",
    "ru": "любовь"
  },
  {
    "de": "der Streit",
    "tr": "ʃtʁaɪ̯t",
    "ru": "ссора"
  },
  {
    "de": "die Unterstützung",
    "tr": "ʊntɐˈʃtʏt͡sʊŋ",
    "ru": "поддержка"
  },
  {
    "de": "die Tradition",
    "tr": "tʁadiˈt͡si̯oːn",
    "ru": "традиция"
  },
  {
    "de": "die Generation",
    "tr": "ɡenəʁaˈt͡si̯oːn",
    "ru": "поколение"
  },
  {
    "de": "zusammen",
    "tr": "t͡suˈzamən",
    "ru": "вместе"
  },
  {
    "de": "allein",
    "tr": "aˈlaɪ̯n",
    "ru": "один"
  },
  {
    "de": "verwandt",
    "tr": "fɛɐ̯ˈvant",
    "ru": "родственник"
  },
  {
    "de": "sich kümmern",
    "tr": "zɪç ˈkʏmɐʁn",
    "ru": "заботиться"
  },
  {
    "de": "sich treffen",
    "tr": "zɪç ˈtʁɛfn̩",
    "ru": "встречаться"
  },
  {
    "de": "besuchen",
    "tr": "bəˈzuːxn̩",
    "ru": "навещать"
  },
  {
    "de": "wohnen",
    "tr": "ˈvoːnən",
    "ru": "жить"
  },
  {
    "de": "leben",
    "tr": "ˈleːbn̩",
    "ru": "жить (существовать)"
  },
  {
    "de": "das Haus",
    "tr": "das haʊ̯s",
    "ru": "дом"
  },
  {
    "de": "die Wohnung",
    "tr": "ˈvoːnʊŋ",
    "ru": "квартира"
  },
  {
    "de": "das Zimmer",
    "tr": "ˈt͡sɪmɐ",
    "ru": "комната"
  },
  {
    "de": "das Wohnzimmer",
    "tr": "ˈvoːnˌt͡sɪmɐ",
    "ru": "гостиная"
  },
  {
    "de": "das Schlafzimmer",
    "tr": "ˈʃlaːfˌt͡sɪmɐ",
    "ru": "спальня"
  },
  {
    "de": "die Küche",
    "tr": "ˈkʏçə",
    "ru": "кухня"
  },
  {
    "de": "das Badezimmer",
    "tr": "ˈbaːdəˌt͡sɪmɐ",
    "ru": "ванная"
  },
  {
    "de": "die Toilette",
    "tr": "to̯aˈlɛtə",
    "ru": "туалет"
  },
  {
    "de": "der Flur",
    "tr": "fluːɐ̯",
    "ru": "коридор"
  },
  {
    "de": "der Balkon",
    "tr": "balˈkoːn",
    "ru": "балкон"
  },
  {
    "de": "der Garten",
    "tr": "ˈɡaʁtn̩",
    "ru": "сад"
  },
  {
    "de": "die Garage",
    "tr": "ɡaˈʁaːʒə",
    "ru": "гараж"
  },
  {
    "de": "das Fenster",
    "tr": "ˈfɛnstɐ",
    "ru": "окно"
  },
  {
    "de": "die Tür",
    "tr": "tyːɐ̯",
    "ru": "дверь"
  },
  {
    "de": "die Wand",
    "tr": "vant",
    "ru": "стена"
  },
  {
    "de": "der Boden",
    "tr": "ˈboːdn̩",
    "ru": "пол"
  },
  {
    "de": "die Decke",
    "tr": "ˈdɛkə",
    "ru": "потолок"
  },
  {
    "de": "das Bett",
    "tr": "bɛt",
    "ru": "кровать"
  },
  {
    "de": "der Tisch",
    "tr": "tɪʃ",
    "ru": "стол"
  },
  {
    "de": "der Stuhl",
    "tr": "ʃtuːl",
    "ru": "стул"
  },
  {
    "de": "das Sofa",
    "tr": "ˈzoːfa",
    "ru": "диван"
  },
  {
    "de": "der Schrank",
    "tr": "ʃʁaŋk",
    "ru": "шкаф"
  },
  {
    "de": "das Regal",
    "tr": "ʁeˈɡaːl",
    "ru": "полка"
  },
  {
    "de": "der Teppich",
    "tr": "ˈtɛpɪç",
    "ru": "ковёр"
  },
  {
    "de": "die Lampe",
    "tr": "ˈlampə",
    "ru": "лампа"
  },
  {
    "de": "die Heizung",
    "tr": "ˈhaɪ̯t͡sʊŋ",
    "ru": "отопление"
  },
  {
    "de": "der Kühlschrank",
    "tr": "ˈkyːlʃʁaŋk",
    "ru": "холодильник"
  },
  {
    "de": "der Herd",
    "tr": "heːɐ̯t",
    "ru": "плита"
  },
  {
    "de": "die Spüle",
    "tr": "ˈʃpyːlə",
    "ru": "раковина"
  },
  {
    "de": "die Dusche",
    "tr": "ˈduːʃə",
    "ru": "душ"
  },
  {
    "de": "die Badewanne",
    "tr": "ˈbaːdəˌvanə",
    "ru": "ванна"
  },
  {
    "de": "die Waschmaschine",
    "tr": "ˈvaʃmaˌʃiːnə",
    "ru": "стиральная машина"
  },
  {
    "de": "der Staubsauger",
    "tr": "ˈʃtaʊ̯pˌzaʊ̯ɡɐ",
    "ru": "пылесос"
  },
  {
    "de": "der Schlüssel",
    "tr": "ˈʃlʏsl̩",
    "ru": "ключ"
  },
  {
    "de": "die Miete",
    "tr": "ˈmiːtə",
    "ru": "аренда"
  },
  {
    "de": "der Vermieter",
    "tr": "fɛɐ̯ˈmiːtɐ",
    "ru": "арендодатель"
  },
  {
    "de": "der Mieter",
    "tr": "ˈmiːtɐ",
    "ru": "арендатор"
  },
  {
    "de": "die Nachbarn",
    "tr": "ˈnaxbaʁn̩",
    "ru": "соседи"
  },
  {
    "de": "das Gebäude",
    "tr": "ɡəˈbɔʏ̯də",
    "ru": "здание"
  },
  {
    "de": "der Eingang",
    "tr": "ˈaɪ̯nˌɡaŋ",
    "ru": "вход"
  },
  {
    "de": "der Ausgang",
    "tr": "ˈaʊ̯sˌɡaŋ",
    "ru": "выход"
  },
  {
    "de": "der Aufzug",
    "tr": "ˈaʊ̯fˌt͡suːk",
    "ru": "лифт"
  },
  {
    "de": "die Treppe",
    "tr": "ˈtʁɛpə",
    "ru": "лестница"
  },
  {
    "de": "die Klingel",
    "tr": "ˈklɪŋl̩",
    "ru": "звонок"
  },
  {
    "de": "der Mietvertrag",
    "tr": "ˈmiːtˌfɛɐ̯ˌtʁaːk",
    "ru": "договор аренды"
  },
  {
    "de": "die Anzeige",
    "tr": "ˈant͡saɪ̯ɡə",
    "ru": "объявление"
  },
  {
    "de": "das Möbel",
    "tr": "ˈmøːbl̩",
    "ru": "мебель"
  },
  {
    "de": "einziehen",
    "tr": "ˈaɪ̯nˌt͡siːən",
    "ru": "въезжать"
  },
  {
    "de": "ausziehen",
    "tr": "ˈaʊ̯sˌt͡siːən",
    "ru": "съезжать"
  },
  {
    "de": "das Essen",
    "tr": "das ˈɛsn̩",
    "ru": "еда"
  },
  {
    "de": "das Getränk",
    "tr": "ɡəˈtʁɛŋk",
    "ru": "напиток"
  },
  {
    "de": "das Wasser",
    "tr": "ˈvasɐ",
    "ru": "вода"
  },
  {
    "de": "der Saft",
    "tr": "zaft",
    "ru": "сок"
  },
  {
    "de": "die Milch",
    "tr": "mɪlç",
    "ru": "молоко"
  },
  {
    "de": "der Kaffee",
    "tr": "ˈkafeː",
    "ru": "кофе"
  },
  {
    "de": "der Tee",
    "tr": "teː",
    "ru": "чай"
  },
  {
    "de": "die Suppe",
    "tr": "ˈzʊpə",
    "ru": "суп"
  },
  {
    "de": "das Brot",
    "tr": "broːt",
    "ru": "хлеб"
  },
  {
    "de": "die Brötchen",
    "tr": "ˈbʁøːtçən",
    "ru": "булочки"
  },
  {
    "de": "die Butter",
    "tr": "ˈbʊtɐ",
    "ru": "масло"
  },
  {
    "de": "der Käse",
    "tr": "ˈkɛːzə",
    "ru": "сыр"
  },
  {
    "de": "das Fleisch",
    "tr": "flaɪ̯ʃ",
    "ru": "мясо"
  },
  {
    "de": "das Hähnchen",
    "tr": "ˈhɛːnçən",
    "ru": "курица"
  },
  {
    "de": "der Fisch",
    "tr": "fɪʃ",
    "ru": "рыба"
  },
  {
    "de": "die Wurst",
    "tr": "vʊʁst",
    "ru": "колбаса"
  },
  {
    "de": "das Ei",
    "tr": "aɪ̯",
    "ru": "яйцо"
  },
  {
    "de": "der Reis",
    "tr": "ʁaɪ̯s",
    "ru": "рис"
  },
  {
    "de": "die Nudeln",
    "tr": "ˈnuːdl̩n",
    "ru": "макароны"
  },
  {
    "de": "das Gemüse",
    "tr": "ɡəˈmyːzə",
    "ru": "овощи"
  },
  {
    "de": "das Obst",
    "tr": "oːpst",
    "ru": "фрукты"
  },
  {
    "de": "der Apfel",
    "tr": "ˈapfl̩",
    "ru": "яблоко"
  },
  {
    "de": "die Banane",
    "tr": "baˈnaːnə",
    "ru": "банан"
  },
  {
    "de": "die Orange",
    "tr": "oˈʁãːʒə",
    "ru": "апельсин"
  },
  {
    "de": "die Trauben",
    "tr": "ˈtʁaʊ̯bn̩",
    "ru": "виноград"
  },
  {
    "de": "die Kartoffel",
    "tr": "kaʁˈtɔfl̩",
    "ru": "картофель"
  },
  {
    "de": "die Tomate",
    "tr": "toˈmaːtə",
    "ru": "помидор"
  },
  {
    "de": "die Gurke",
    "tr": "ˈɡʊʁkə",
    "ru": "огурец"
  },
  {
    "de": "die Zwiebel",
    "tr": "ˈt͡sviːbl̩",
    "ru": "лук"
  },
  {
    "de": "die Karotte",
    "tr": "kaˈʁɔtə",
    "ru": "морковь"
  },
  {
    "de": "der Salat",
    "tr": "zaˈlaːt",
    "ru": "салат"
  },
  {
    "de": "die Pizza",
    "tr": "ˈpɪt͡sa",
    "ru": "пицца"
  },
  {
    "de": "der Hamburger",
    "tr": "ˈhambʊʁɡɐ",
    "ru": "гамбургер"
  },
  {
    "de": "die Pommes",
    "tr": "ˈpɔmə",
    "ru": "картофель фри"
  },
  {
    "de": "der Zucker",
    "tr": "ˈt͡sʊkɐ",
    "ru": "сахар"
  },
  {
    "de": "das Salz",
    "tr": "zalt͡s",
    "ru": "соль"
  },
  {
    "de": "der Pfeffer",
    "tr": "ˈpfɛfɐ",
    "ru": "перец"
  },
  {
    "de": "das Öl",
    "tr": "øːl",
    "ru": "масло (растительное)"
  },
  {
    "de": "der Honig",
    "tr": "ˈhoːnɪç",
    "ru": "мёд"
  },
  {
    "de": "die Schokolade",
    "tr": "ʃokoˈlaːdə",
    "ru": "шоколад"
  },
  {
    "de": "der Kuchen",
    "tr": "ˈkuːxn̩",
    "ru": "пирог, торт"
  },
  {
    "de": "das Eis",
    "tr": "aɪ̯s",
    "ru": "мороженое"
  },
  {
    "de": "frisch",
    "tr": "fʁɪʃ",
    "ru": "свежий"
  },
  {
    "de": "kalt",
    "tr": "kalt",
    "ru": "холодный"
  },
  {
    "de": "heiß",
    "tr": "haɪ̯s",
    "ru": "горячий"
  },
  {
    "de": "süß",
    "tr": "zyːs",
    "ru": "сладкий"
  },
  {
    "de": "salzig",
    "tr": "ˈzaltsɪç",
    "ru": "солёный"
  },
  {
    "de": "bitter",
    "tr": "ˈbɪtɐ",
    "ru": "горький"
  },
  {
    "de": "scharf",
    "tr": "ʃaʁf",
    "ru": "острый"
  },
  {
    "de": "lecker",
    "tr": "ˈlɛkɐ",
    "ru": "вкусный"
  },
  {
    "de": "die Zeit",
    "tr": "t͡saɪ̯t",
    "ru": "время"
  },
  {
    "de": "die Uhr",
    "tr": "uːɐ̯",
    "ru": "часы"
  },
  {
    "de": "die Uhrzeit",
    "tr": "ˈuːɐ̯ˌt͡saɪ̯t",
    "ru": "время (на часах)"
  },
  {
    "de": "die Stunde",
    "tr": "ˈʃtʊndə",
    "ru": "час"
  },
  {
    "de": "die Minute",
    "tr": "miˈnuːtə",
    "ru": "минута"
  },
  {
    "de": "die Sekunde",
    "tr": "zeˈkʊndə",
    "ru": "секунда"
  },
  {
    "de": "der Morgen",
    "tr": "ˈmɔʁɡn̩",
    "ru": "утро"
  },
  {
    "de": "der Vormittag",
    "tr": "ˈfoːɐ̯mɪtaːk",
    "ru": "до полудня"
  },
  {
    "de": "der Mittag",
    "tr": "ˈmɪtaːk",
    "ru": "полдень"
  },
  {
    "de": "der Nachmittag",
    "tr": "ˈnaːxmɪtaːk",
    "ru": "после обеда"
  },
  {
    "de": "der Abend",
    "tr": "ˈaːbn̩t",
    "ru": "вечер"
  },
  {
    "de": "die Nacht",
    "tr": "naxt",
    "ru": "ночь"
  },
  {
    "de": "Montag",
    "tr": "ˈmoːntaːk",
    "ru": "понедельник"
  },
  {
    "de": "Dienstag",
    "tr": "ˈdiːnstaːk",
    "ru": "вторник"
  },
  {
    "de": "Mittwoch",
    "tr": "ˈmɪtvɔx",
    "ru": "среда"
  },
  {
    "de": "Donnerstag",
    "tr": "ˈdɔnɐstaːk",
    "ru": "четверг"
  },
  {
    "de": "Freitag",
    "tr": "ˈfʁaɪ̯taːk",
    "ru": "пятница"
  },
  {
    "de": "Samstag",
    "tr": "ˈzamstaːk",
    "ru": "суббота"
  },
  {
    "de": "Sonntag",
    "tr": "ˈzɔnˌtaːk",
    "ru": "воскресенье"
  },
  {
    "de": "heute",
    "tr": "ˈhɔɪ̯tə",
    "ru": "сегодня"
  },
  {
    "de": "gestern",
    "tr": "ˈɡɛstɐn",
    "ru": "вчера"
  },
  {
    "de": "morgen",
    "tr": "ˈmɔʁɡn̩",
    "ru": "завтра"
  },
  {
    "de": "jetzt",
    "tr": "jɛt͡st",
    "ru": "сейчас"
  },
  {
    "de": "später",
    "tr": "ˈʃpɛːtɐ",
    "ru": "позже"
  },
  {
    "de": "früh",
    "tr": "fʁyː",
    "ru": "рано"
  },
  {
    "de": "zu spät",
    "tr": "t͡suː ʃpɛːt",
    "ru": "слишком поздно"
  },
  {
    "de": "pünktlich",
    "tr": "ˈpʏŋktlɪç",
    "ru": "пунктуальный"
  },
  {
    "de": "der Kalender",
    "tr": "kaˈlɛndɐ",
    "ru": "календарь"
  },
  {
    "de": "der Termin",
    "tr": "tɛʁˈmiːn",
    "ru": "встреча, запись"
  },
  {
    "de": "die Woche",
    "tr": "ˈvɔxə",
    "ru": "неделя"
  },
  {
    "de": "das Wochenende",
    "tr": "ˈvɔxənˌʔɛndə",
    "ru": "выходные"
  },
  {
    "de": "der Monat",
    "tr": "ˈmoːnaːt",
    "ru": "месяц"
  },
  {
    "de": "das Jahr",
    "tr": "jaːɐ̯",
    "ru": "год"
  },
  {
    "de": "die Jahreszeit",
    "tr": "ˈjaːʁəst͡saɪ̯t",
    "ru": "время года"
  },
  {
    "de": "immer",
    "tr": "ˈɪmɐ",
    "ru": "всегда"
  },
  {
    "de": "nie",
    "tr": "niː",
    "ru": "никогда"
  },
  {
    "de": "manchmal",
    "tr": "ˈmançmaːl",
    "ru": "иногда"
  },
  {
    "de": "oft",
    "tr": "ɔft",
    "ru": "часто"
  },
  {
    "de": "selten",
    "tr": "ˈzɛltn̩",
    "ru": "редко"
  },
  {
    "de": "morgens",
    "tr": "ˈmɔʁɡn̩s",
    "ru": "по утрам"
  },
  {
    "de": "mittags",
    "tr": "ˈmɪtaːks",
    "ru": "в полдень"
  },
  {
    "de": "abends",
    "tr": "ˈaːbn̩ts",
    "ru": "по вечерам"
  },
  {
    "de": "nachts",
    "tr": "naxts",
    "ru": "по ночам"
  },
  {
    "de": "bald",
    "tr": "balt",
    "ru": "скоро"
  },
  {
    "de": "vorher",
    "tr": "ˈfoːɐ̯heːɐ̯",
    "ru": "до этого"
  },
  {
    "de": "nachher",
    "tr": "ˈnaːxheːɐ̯",
    "ru": "после этого"
  },
  {
    "de": "rechtzeitig",
    "tr": "ˈʁɛçtˌt͡saɪ̯tɪç",
    "ru": "своевременно"
  },
  {
    "de": "der Wecker",
    "tr": "ˈvɛkɐ",
    "ru": "будильник"
  },
  {
    "de": "der Zeitplan",
    "tr": "ˈt͡saɪ̯tˌplaːn",
    "ru": "расписание"
  },
  {
    "de": "die Pause",
    "tr": "ˈpaʊ̯zə",
    "ru": "перерыв"
  },
  {
    "de": "die Stadt",
    "tr": "ʃtat",
    "ru": "город"
  },
  {
    "de": "das Dorf",
    "tr": "dɔʁf",
    "ru": "деревня"
  },
  {
    "de": "das Zentrum",
    "tr": "ˈt͡sɛntʁʊm",
    "ru": "центр"
  },
  {
    "de": "der Stadtrand",
    "tr": "ˈʃtatˌʁant",
    "ru": "окраина"
  },
  {
    "de": "die Straße",
    "tr": "ˈʃtʁaːsə",
    "ru": "улица"
  },
  {
    "de": "der Platz",
    "tr": "plat͡s",
    "ru": "площадь"
  },
  {
    "de": "die Kreuzung",
    "tr": "ˈkʁɔʏ̯t͡sʊŋ",
    "ru": "перекресток"
  },
  {
    "de": "die Ampel",
    "tr": "ˈampəl",
    "ru": "светофор"
  },
  {
    "de": "der Bahnhof",
    "tr": "ˈbaːnhoːf",
    "ru": "вокзал"
  },
  {
    "de": "die Haltestelle",
    "tr": "ˈhaltəˌʃtɛlə",
    "ru": "остановка"
  },
  {
    "de": "die Station",
    "tr": "ʃtaˈt͡si̯oːn",
    "ru": "станция"
  },
  {
    "de": "der Bus",
    "tr": "bʊs",
    "ru": "автобус"
  },
  {
    "de": "die U-Bahn",
    "tr": "ˈuːˌbaːn",
    "ru": "метро"
  },
  {
    "de": "die S-Bahn",
    "tr": "ˈɛsˌbaːn",
    "ru": "городская электричка"
  },
  {
    "de": "das Taxi",
    "tr": "ˈtaksi",
    "ru": "такси"
  },
  {
    "de": "das Auto",
    "tr": "ˈaʊ̯to",
    "ru": "машина"
  },
  {
    "de": "der Zug",
    "tr": "t͡suːk",
    "ru": "поезд"
  },
  {
    "de": "das Fahrrad",
    "tr": "ˈfaːʁaːt",
    "ru": "велосипед"
  },
  {
    "de": "der Fahrer",
    "tr": "ˈfaːʁɐ",
    "ru": "водитель"
  },
  {
    "de": "fahren",
    "tr": "ˈfaːʁən",
    "ru": "ехать"
  },
  {
    "de": "gehen",
    "tr": "ˈɡeːən",
    "ru": "идти"
  },
  {
    "de": "zu Fuß",
    "tr": "t͡suː fuːs",
    "ru": "пешком"
  },
  {
    "de": "links",
    "tr": "lɪŋks",
    "ru": "налево"
  },
  {
    "de": "rechts",
    "tr": "ʁɛçts",
    "ru": "направо"
  },
  {
    "de": "geradeaus",
    "tr": "ɡəˈʁaːdəˌaʊ̯s",
    "ru": "прямо"
  },
  {
    "de": "abbiegen",
    "tr": "ˈapˌbiːɡn̩",
    "ru": "поворачивать"
  },
  {
    "de": "der Weg",
    "tr": "veːk",
    "ru": "путь"
  },
  {
    "de": "weit",
    "tr": "vaɪ̯t",
    "ru": "далеко"
  },
  {
    "de": "nah",
    "tr": "naː",
    "ru": "близко"
  },
  {
    "de": "die Apotheke",
    "tr": "apoˈteːkə",
    "ru": "аптека"
  },
  {
    "de": "der Supermarkt",
    "tr": "ˈzuːpɐˌmaʁkt",
    "ru": "супермаркет"
  },
  {
    "de": "das Geschäft",
    "tr": "ɡəˈʃɛft",
    "ru": "магазин"
  },
  {
    "de": "die Bank",
    "tr": "baŋk",
    "ru": "банк"
  },
  {
    "de": "die Post",
    "tr": "pɔst",
    "ru": "почта"
  },
  {
    "de": "das Rathaus",
    "tr": "ˈʁaːtˌhaʊ̯s",
    "ru": "ратуша"
  },
  {
    "de": "die Polizei",
    "tr": "poliˈt͡saɪ̯",
    "ru": "полиция"
  },
  {
    "de": "das Krankenhaus",
    "tr": "ˈkʁaŋkn̩ˌhaʊ̯s",
    "ru": "больница"
  },
  {
    "de": "die Schule",
    "tr": "ˈʃuːlə",
    "ru": "школа"
  },
  {
    "de": "die Bibliothek",
    "tr": "biblioˈteːk",
    "ru": "библиотека"
  },
  {
    "de": "der Park",
    "tr": "paʁk",
    "ru": "парк"
  },
  {
    "de": "der Spielplatz",
    "tr": "ˈʃpiːlˌplat͡s",
    "ru": "детская площадка"
  },
  {
    "de": "das Restaurant",
    "tr": "ʁɛstoˈʁãː",
    "ru": "ресторан"
  },
  {
    "de": "die Bäckerei",
    "tr": "bɛkəˈʁaɪ̯",
    "ru": "пекарня"
  },
  {
    "de": "die Tankstelle",
    "tr": "ˈtaŋkˌʃtɛlə",
    "ru": "заправка"
  },
  {
    "de": "suchen",
    "tr": "ˈzuːxn̩",
    "ru": "искать"
  },
  {
    "de": "finden",
    "tr": "ˈfɪndn̩",
    "ru": "находить"
  },
  {
    "de": "verlieren",
    "tr": "fɛɐ̯ˈliːʁən",
    "ru": "терять"
  },
  {
    "de": "besuchen",
    "tr": "bəˈzuːxn̩",
    "ru": "посещать"
  },
  {
    "de": "besichtigen",
    "tr": "bəˈzɪçtɪɡən",
    "ru": "осматривать"
  },
  {
    "de": "die Richtung",
    "tr": "ˈʁɪçtʊŋ",
    "ru": "направление"
  },
  {
    "de": "die Schule",
    "tr": "ˈʃuːlə",
    "ru": "школа"
  },
  {
    "de": "die Klasse",
    "tr": "ˈklasə",
    "ru": "класс"
  },
  {
    "de": "das Klassenzimmer",
    "tr": "ˈklasn̩ˌt͡sɪmɐ",
    "ru": "классная комната"
  },
  {
    "de": "der Lehrer",
    "tr": "ˈleːʁɐ",
    "ru": "учитель"
  },
  {
    "de": "die Lehrerin",
    "tr": "ˈleːʁəʁɪn",
    "ru": "учительница"
  },
  {
    "de": "der Schüler",
    "tr": "ˈʃyːlɐ",
    "ru": "школьник"
  },
  {
    "de": "die Schülerin",
    "tr": "ˈʃyːləʁɪn",
    "ru": "школьница"
  },
  {
    "de": "das Fach",
    "tr": "fax",
    "ru": "предмет"
  },
  {
    "de": "der Unterricht",
    "tr": "ˈʊntɐʁɪçt",
    "ru": "урок"
  },
  {
    "de": "lernen",
    "tr": "ˈlɛʁnən",
    "ru": "учить"
  },
  {
    "de": "studieren",
    "tr": "ʃtuˈdiːʁən",
    "ru": "изучать"
  },
  {
    "de": "lesen",
    "tr": "ˈleːzn̩",
    "ru": "читать"
  },
  {
    "de": "schreiben",
    "tr": "ˈʃʁaɪ̯bn̩",
    "ru": "писать"
  },
  {
    "de": "rechnen",
    "tr": "ˈʁɛçnən",
    "ru": "считать"
  },
  {
    "de": "die Aufgabe",
    "tr": "ˈaʊ̯fˌɡaːbə",
    "ru": "задание"
  },
  {
    "de": "die Hausaufgabe",
    "tr": "ˈhaʊ̯sʔaʊ̯fˌɡaːbə",
    "ru": "домашнее задание"
  },
  {
    "de": "die Prüfung",
    "tr": "ˈpʁyːfʊŋ",
    "ru": "экзамен"
  },
  {
    "de": "der Test",
    "tr": "tɛst",
    "ru": "тест"
  },
  {
    "de": "die Note",
    "tr": "ˈnoːtə",
    "ru": "оценка"
  },
  {
    "de": "die Frage",
    "tr": "ˈfʁaːɡə",
    "ru": "вопрос"
  },
  {
    "de": "die Antwort",
    "tr": "ˈantvɔʁt",
    "ru": "ответ"
  },
  {
    "de": "verstehen",
    "tr": "fɛɐ̯ˈʃteːən",
    "ru": "понимать"
  },
  {
    "de": "wiederholen",
    "tr": "viːdɐˈhoːlən",
    "ru": "повторять"
  },
  {
    "de": "die Pause",
    "tr": "ˈpaʊ̯zə",
    "ru": "перемена"
  },
  {
    "de": "der Schulhof",
    "tr": "ˈʃuːlhoːf",
    "ru": "школьный двор"
  },
  {
    "de": "das Buch",
    "tr": "buːx",
    "ru": "книга"
  },
  {
    "de": "das Heft",
    "tr": "hɛft",
    "ru": "тетрадь"
  },
  {
    "de": "der Bleistift",
    "tr": "ˈblaɪ̯ˌʃtɪft",
    "ru": "карандаш"
  },
  {
    "de": "der Kugelschreiber",
    "tr": "ˈkuːɡl̩ˌʃʁaɪ̯bɐ",
    "ru": "ручка"
  },
  {
    "de": "das Papier",
    "tr": "paˈpiːɐ̯",
    "ru": "бумага"
  },
  {
    "de": "die Tafel",
    "tr": "ˈtaːfl̩",
    "ru": "доска"
  },
  {
    "de": "der Radiergummi",
    "tr": "ʁaˈdiːɐ̯ˌɡʊmi",
    "ru": "ластик"
  },
  {
    "de": "das Lineal",
    "tr": "lɪniˈaːl",
    "ru": "линейка"
  },
  {
    "de": "der Rucksack",
    "tr": "ˈʁʊkˌzak",
    "ru": "рюкзак"
  },
  {
    "de": "die Schultasche",
    "tr": "ˈʃuːlˌtaʃə",
    "ru": "школьная сумка"
  },
  {
    "de": "der Computer",
    "tr": "kɔmˈpjuːtɐ",
    "ru": "компьютер"
  },
  {
    "de": "das Internet",
    "tr": "ˈɪntɐnɛt",
    "ru": "интернет"
  },
  {
    "de": "die Bibliothek",
    "tr": "biblioˈteːk",
    "ru": "библиотека"
  },
  {
    "de": "die Universität",
    "tr": "univeʁziˈtɛːt",
    "ru": "университет"
  },
  {
    "de": "der Student",
    "tr": "ʃtuˈdɛnt",
    "ru": "студент"
  },
  {
    "de": "die Studentin",
    "tr": "ʃtuˈdɛntɪn",
    "ru": "студентка"
  },
  {
    "de": "prüfen",
    "tr": "ˈpʁyːfən",
    "ru": "проверять"
  },
  {
    "de": "erklären",
    "tr": "ɛɐ̯ˈklɛːʁən",
    "ru": "объяснять"
  },
  {
    "de": "aufpassen",
    "tr": "ˈaʊ̯fˌpasn̩",
    "ru": "быть внимательным"
  },
  {
    "de": "beginnen",
    "tr": "bəˈɡɪnən",
    "ru": "начинать"
  },
  {
    "de": "enden",
    "tr": "ˈɛndn̩",
    "ru": "заканчивать"
  },
  {
    "de": "prüfungsfrei",
    "tr": "ˈpʁyːfʊŋsˌfʁaɪ̯",
    "ru": "без экзаменов"
  },
  {
    "de": "der Stundenplan",
    "tr": "ˈʃtʊndn̩ˌplaːn",
    "ru": "расписание"
  },
  {
    "de": "die Bildung",
    "tr": "ˈbɪldʊŋ",
    "ru": "образование"
  },
  {
    "de": "kaufen",
    "tr": "ˈkaʊ̯fn̩",
    "ru": "покупать"
  },
  {
    "de": "verkaufen",
    "tr": "fɛɐ̯ˈkaʊ̯fn̩",
    "ru": "продавать"
  },
  {
    "de": "der Laden",
    "tr": "ˈlaːdn̩",
    "ru": "магазин"
  },
  {
    "de": "das Geschäft",
    "tr": "ɡəˈʃɛft",
    "ru": "магазин"
  },
  {
    "de": "der Supermarkt",
    "tr": "ˈzuːpɐˌmaʁkt",
    "ru": "супермаркет"
  },
  {
    "de": "das Einkaufszentrum",
    "tr": "ˈaɪ̯nkaʊ̯fsˌt͡sɛntʁʊm",
    "ru": "торговый центр"
  },
  {
    "de": "die Bäckerei",
    "tr": "bɛkəˈʁaɪ̯",
    "ru": "пекарня"
  },
  {
    "de": "die Metzgerei",
    "tr": "mɛt͡sɡəˈʁaɪ̯",
    "ru": "мясная лавка"
  },
  {
    "de": "die Apotheke",
    "tr": "apoˈteːkə",
    "ru": "аптека"
  },
  {
    "de": "die Kasse",
    "tr": "ˈkasə",
    "ru": "касса"
  },
  {
    "de": "die Schlange",
    "tr": "ˈʃlaŋə",
    "ru": "очередь"
  },
  {
    "de": "der Einkauf",
    "tr": "ˈaɪ̯nˌkaʊ̯f",
    "ru": "покупка"
  },
  {
    "de": "einkaufen",
    "tr": "ˈaɪ̯nˌkaʊ̯fn̩",
    "ru": "делать покупки"
  },
  {
    "de": "das Angebot",
    "tr": "ˈanɡəˌboːt",
    "ru": "предложение, акция"
  },
  {
    "de": "der Preis",
    "tr": "pʁaɪ̯s",
    "ru": "цена"
  },
  {
    "de": "billig",
    "tr": "ˈbɪlɪç",
    "ru": "дешевый"
  },
  {
    "de": "teuer",
    "tr": "ˈtɔɪ̯ɐ",
    "ru": "дорогой"
  },
  {
    "de": "die Rechnung",
    "tr": "ˈʁɛçnʊŋ",
    "ru": "счет"
  },
  {
    "de": "bezahlen",
    "tr": "bəˈt͡saːlən",
    "ru": "платить"
  },
  {
    "de": "bar bezahlen",
    "tr": "baːɐ̯ bəˈt͡saːlən",
    "ru": "платить наличными"
  },
  {
    "de": "mit Karte zahlen",
    "tr": "mɪt ˈkaʁtə ˈt͡saːlən",
    "ru": "платить картой"
  },
  {
    "de": "die Kreditkarte",
    "tr": "kʁeˈdiːtˌkaʁtə",
    "ru": "кредитная карта"
  },
  {
    "de": "der Verkäufer",
    "tr": "fɛɐ̯ˈkɔɪ̯fɐ",
    "ru": "продавец"
  },
  {
    "de": "die Verkäuferin",
    "tr": "fɛɐ̯ˈkɔɪ̯fʁɪn",
    "ru": "продавщица"
  },
  {
    "de": "die Tüte",
    "tr": "ˈtyːtə",
    "ru": "пакет"
  },
  {
    "de": "die Tasche",
    "tr": "ˈtaʃə",
    "ru": "сумка"
  },
  {
    "de": "probieren",
    "tr": "pʁoˈbiːʁən",
    "ru": "пробовать"
  },
  {
    "de": "anprobieren",
    "tr": "ˈanpʁoˌbiːʁən",
    "ru": "примерять"
  },
  {
    "de": "passen",
    "tr": "ˈpasn̩",
    "ru": "подходить"
  },
  {
    "de": "zurückgeben",
    "tr": "t͡suˈʁʏkˌɡeːbn̩",
    "ru": "возвращать"
  },
  {
    "de": "suchen",
    "tr": "ˈzuːxn̩",
    "ru": "искать"
  },
  {
    "de": "finden",
    "tr": "ˈfɪndn̩",
    "ru": "находить"
  },
  {
    "de": "brauchen",
    "tr": "ˈbʁaʊ̯xn̩",
    "ru": "нуждаться"
  },
  {
    "de": "die Größe",
    "tr": "ˈɡʁøːsə",
    "ru": "размер"
  },
  {
    "de": "die Farbe",
    "tr": "ˈfaʁbə",
    "ru": "цвет"
  },
  {
    "de": "die Ware",
    "tr": "ˈvaːʁə",
    "ru": "товар"
  },
  {
    "de": "die Qualität",
    "tr": "kvaliˈtɛːt",
    "ru": "качество"
  },
  {
    "de": "die Quittung",
    "tr": "ˈkvɪtʊŋ",
    "ru": "чек"
  },
  {
    "de": "reduziert",
    "tr": "ʁeduˈt͡siːɐ̯t",
    "ru": "со скидкой"
  },
  {
    "de": "im Angebot sein",
    "tr": "ɪm ˈanɡəˌboːt zaɪ̯n",
    "ru": "быть по акции"
  },
  {
    "de": "öffnen",
    "tr": "ˈœfnən",
    "ru": "открывать"
  },
  {
    "de": "schließen",
    "tr": "ˈʃliːsən",
    "ru": "закрывать"
  },
  {
    "de": "geöffnet",
    "tr": "ɡəˈœfnət",
    "ru": "открыто"
  },
  {
    "de": "geschlossen",
    "tr": "ɡəˈʃlɔsn̩",
    "ru": "закрыто"
  },
  {
    "de": "die Öffnungszeiten",
    "tr": "ˈœfnʊŋsˌt͡saɪ̯tn̩",
    "ru": "часы работы"
  },
  {
    "de": "das Sonderangebot",
    "tr": "ˈzɔndɐˌanɡəˌboːt",
    "ru": "специальное предложение"
  },
  {
    "de": "der Prospekt",
    "tr": "pʁoˈspɛkt",
    "ru": "рекламная листовка"
  },
  {
    "de": "der Kunde",
    "tr": "ˈkʊndə",
    "ru": "клиент"
  },
  {
    "de": "die Kundin",
    "tr": "ˈkʊndɪn",
    "ru": "клиентка"
  },
  {
    "de": "gesund",
    "tr": "ɡəˈzʊnt",
    "ru": "здоровый"
  },
  {
    "de": "die Gesundheit",
    "tr": "ɡəˈzʊndhaɪ̯t",
    "ru": "здоровье"
  },
  {
    "de": "krank",
    "tr": "kʁaŋk",
    "ru": "больной"
  },
  {
    "de": "die Krankheit",
    "tr": "ˈkʁaŋkhaɪ̯t",
    "ru": "болезнь"
  },
  {
    "de": "das Fieber",
    "tr": "ˈfiːbɐ",
    "ru": "жар"
  },
  {
    "de": "die Erkältung",
    "tr": "ɛɐ̯ˈkɛltʊŋ",
    "ru": "простуда"
  },
  {
    "de": "der Husten",
    "tr": "ˈhuːstn̩",
    "ru": "кашель"
  },
  {
    "de": "der Schnupfen",
    "tr": "ˈʃnʊpfn̩",
    "ru": "насморк"
  },
  {
    "de": "die Kopfschmerzen",
    "tr": "ˈkɔp͡fʃmɛʁt͡sn̩",
    "ru": "головная боль"
  },
  {
    "de": "die Bauchschmerzen",
    "tr": "ˈbaʊ̯xʃmɛʁt͡sn̩",
    "ru": "боль в животе"
  },
  {
    "de": "die Tablette",
    "tr": "taˈblɛtə",
    "ru": "таблетка"
  },
  {
    "de": "die Medizin",
    "tr": "mediˈt͡siːn",
    "ru": "лекарство"
  },
  {
    "de": "das Rezept",
    "tr": "ʁeˈt͡sɛpt",
    "ru": "рецепт"
  },
  {
    "de": "der Arzt",
    "tr": "aʁt͡st",
    "ru": "врач"
  },
  {
    "de": "die Ärztin",
    "tr": "ˈɛːʁt͡stin",
    "ru": "врач (женщина)"
  },
  {
    "de": "die Apotheke",
    "tr": "apoˈteːkə",
    "ru": "аптека"
  },
  {
    "de": "der Termin",
    "tr": "tɛʁˈmiːn",
    "ru": "запись к врачу"
  },
  {
    "de": "die Untersuchung",
    "tr": "ʊntɐˈzuːxʊŋ",
    "ru": "обследование"
  },
  {
    "de": "die Verletzung",
    "tr": "fɛɐ̯ˈlɛt͡sʊŋ",
    "ru": "травма"
  },
  {
    "de": "die Wunde",
    "tr": "ˈvʊndə",
    "ru": "рана"
  },
  {
    "de": "das Blut",
    "tr": "bluːt",
    "ru": "кровь"
  },
  {
    "de": "der Notfall",
    "tr": "ˈnoːtˌfal",
    "ru": "чрезвычайный случай"
  },
  {
    "de": "die Hilfe",
    "tr": "ˈhɪlfə",
    "ru": "помощь"
  },
  {
    "de": "helfen",
    "tr": "ˈhɛlfn̩",
    "ru": "помогать"
  },
  {
    "de": "retten",
    "tr": "ˈʁɛtn̩",
    "ru": "спасать"
  },
  {
    "de": "weh tun",
    "tr": "veː tuːn",
    "ru": "болеть (о части тела)"
  },
  {
    "de": "sich verletzen",
    "tr": "zɪç fɛɐ̯ˈlɛt͡sn̩",
    "ru": "пораниться"
  },
  {
    "de": "müde",
    "tr": "ˈmyːdə",
    "ru": "усталый"
  },
  {
    "de": "schwach",
    "tr": "ʃvax",
    "ru": "слабый"
  },
  {
    "de": "fit",
    "tr": "fɪt",
    "ru": "в форме"
  },
  {
    "de": "sich ausruhen",
    "tr": "zɪç ˈaʊ̯sˌʁuːən",
    "ru": "отдыхать"
  },
  {
    "de": "schlafen",
    "tr": "ˈʃlaːfn̩",
    "ru": "спать"
  },
  {
    "de": "gut schlafen",
    "tr": "ɡuːt ˈʃlaːfn̩",
    "ru": "хорошо спать"
  },
  {
    "de": "schlecht schlafen",
    "tr": "ʃlɛçt ˈʃlaːfn̩",
    "ru": "плохо спать"
  },
  {
    "de": "sich fühlen",
    "tr": "zɪç ˈfyːlən",
    "ru": "чувствовать себя"
  },
  {
    "de": "hungrig",
    "tr": "ˈhʊŋʁɪç",
    "ru": "голодный"
  },
  {
    "de": "durstig",
    "tr": "ˈdʊʁstɪç",
    "ru": "испытывающий жажду"
  },
  {
    "de": "trinken",
    "tr": "ˈtʁɪŋkn̩",
    "ru": "пить"
  },
  {
    "de": "viel Wasser trinken",
    "tr": "fiːl ˈvasɐ ˈtʁɪŋkn̩",
    "ru": "пить много воды"
  },
  {
    "de": "gesund essen",
    "tr": "ɡəˈzʊnt ˈɛsn̩",
    "ru": "питаться правильно"
  },
  {
    "de": "die Diät",
    "tr": "diˈʔɛːt",
    "ru": "диета"
  },
  {
    "de": "Sport machen",
    "tr": "ʃpɔʁt ˈmaxn̩",
    "ru": "заниматься спортом"
  },
  {
    "de": "die Übung",
    "tr": "ˈyːbʊŋ",
    "ru": "упражнение"
  },
  {
    "de": "der Schmerz",
    "tr": "ʃmɛʁt͡s",
    "ru": "боль"
  },
  {
    "de": "schlimm",
    "tr": "ʃlɪm",
    "ru": "тяжелый, плохой"
  },
  {
    "de": "leicht",
    "tr": "laɪ̯çt",
    "ru": "легкий"
  },
  {
    "de": "die Praxis",
    "tr": "ˈpʁaksɪs",
    "ru": "поликлиника, кабинет"
  },
  {
    "de": "das Krankenhaus",
    "tr": "ˈkʁaŋkn̩ˌhaʊ̯s",
    "ru": "больница"
  },
  {
    "de": "der Patient",
    "tr": "paˈt͡si̯ɛnt",
    "ru": "пациент"
  },
  {
    "de": "die Patientin",
    "tr": "paˈt͡si̯ɛntɪn",
    "ru": "пациентка"
  },
  {
    "de": "der Beruf",
    "tr": "bəˈʁuːf",
    "ru": "профессия"
  },
  {
    "de": "arbeiten",
    "tr": "ˈaʁbaɪ̯tn̩",
    "ru": "работать"
  },
  {
    "de": "die Arbeit",
    "tr": "ˈaʁbaɪ̯t",
    "ru": "работа"
  },
  {
    "de": "der Chef",
    "tr": "ʃɛf",
    "ru": "шеф"
  },
  {
    "de": "die Chefin",
    "tr": "ˈʃɛfɪn",
    "ru": "шефиnя"
  },
  {
    "de": "die Firma",
    "tr": "ˈfɪʁma",
    "ru": "компания"
  },
  {
    "de": "das Büro",
    "tr": "byˈʁoː",
    "ru": "офис"
  },
  {
    "de": "die Fabrik",
    "tr": "faˈbʁɪk",
    "ru": "завод"
  },
  {
    "de": "der Kollege",
    "tr": "koˈleːɡə",
    "ru": "коллега"
  },
  {
    "de": "die Kollegin",
    "tr": "koˈleːɡɪn",
    "ru": "коллега (женщина)"
  },
  {
    "de": "der Kunde",
    "tr": "ˈkʊndə",
    "ru": "клиент"
  },
  {
    "de": "die Kundin",
    "tr": "ˈkʊndɪn",
    "ru": "клиентка"
  },
  {
    "de": "der Verkäufer",
    "tr": "fɛɐ̯ˈkɔɪ̯fɐ",
    "ru": "продавец"
  },
  {
    "de": "der Lehrer",
    "tr": "ˈleːʁɐ",
    "ru": "учитель"
  },
  {
    "de": "der Fahrer",
    "tr": "ˈfaːʁɐ",
    "ru": "водитель"
  },
  {
    "de": "der Arzt",
    "tr": "aʁt͡st",
    "ru": "врач"
  },
  {
    "de": "der Koch",
    "tr": "kɔx",
    "ru": "повар"
  },
  {
    "de": "der Kellner",
    "tr": "ˈkɛl.nɐ",
    "ru": "официант"
  },
  {
    "de": "die Kellnerin",
    "tr": "ˈkɛl.nəʁɪn",
    "ru": "официантка"
  },
  {
    "de": "der Mechaniker",
    "tr": "meˈçaːnɪkɐ",
    "ru": "механик"
  },
  {
    "de": "der Ingenieur",
    "tr": "ɪnʒeˈnøːɐ̯",
    "ru": "инженер"
  },
  {
    "de": "die Stelle",
    "tr": "ˈʃtɛlə",
    "ru": "место работы"
  },
  {
    "de": "die Bewerbung",
    "tr": "bəˈvɛʁbʊŋ",
    "ru": "заявление на работу"
  },
  {
    "de": "der Vertrag",
    "tr": "fɛɐ̯ˈtʁaːk",
    "ru": "контракт"
  },
  {
    "de": "kündigen",
    "tr": "ˈkʏndɪɡən",
    "ru": "увольняться"
  },
  {
    "de": "der Lohn",
    "tr": "loːn",
    "ru": "зарплата"
  },
  {
    "de": "das Gehalt",
    "tr": "ɡəˈhalt",
    "ru": "оклад"
  },
  {
    "de": "verdienen",
    "tr": "fɛɐ̯ˈdiːnən",
    "ru": "зарабатывать"
  },
  {
    "de": "das Team",
    "tr": "tiːm",
    "ru": "команда"
  },
  {
    "de": "der Kollege",
    "tr": "koˈleːɡə",
    "ru": "коллега"
  },
  {
    "de": "zusammenarbeiten",
    "tr": "t͡suˈzamənˌaʁbaɪ̯tn̩",
    "ru": "работать вместе"
  },
  {
    "de": "die Pause",
    "tr": "ˈpaʊ̯zə",
    "ru": "перерыв"
  },
  {
    "de": "die Arbeitszeit",
    "tr": "ˈaʁbaɪ̯t͡sˌt͡saɪ̯t",
    "ru": "рабочее время"
  },
  {
    "de": "Vollzeit",
    "tr": "ˈfɔlt͡saɪ̯t",
    "ru": "полный рабочий день"
  },
  {
    "de": "Teilzeit",
    "tr": "ˈtaɪ̯lt͡saɪ̯t",
    "ru": "неполная занятость"
  },
  {
    "de": "das Praktikum",
    "tr": "ˈpʁaktikʊm",
    "ru": "практика"
  },
  {
    "de": "der Berufserfahrung",
    "tr": "bəˈʁuːfsʔɛɐ̯ˌfaːʁʊŋ",
    "ru": "профессиональный опыт"
  },
  {
    "de": "der Service",
    "tr": "ˈzœʁvɪs",
    "ru": "сервис"
  },
  {
    "de": "anrufen",
    "tr": "ˈanˌʁuːfn̩",
    "ru": "звонить"
  },
  {
    "de": "das Meeting",
    "tr": "ˈmiːtɪŋ",
    "ru": "встреча, митинг"
  },
  {
    "de": "der Termin",
    "tr": "tɛʁˈmiːn",
    "ru": "встреча"
  },
  {
    "de": "pünktlich sein",
    "tr": "ˈpʏŋktlɪç zaɪ̯n",
    "ru": "быть пунктуальным"
  },
  {
    "de": "die Verantwortung",
    "tr": "fɛɐ̯ˈantvɔʁtʊŋ",
    "ru": "ответственность"
  },
  {
    "de": "die Aufgabe",
    "tr": "ˈaʊ̯fˌɡaːbə",
    "ru": "задача"
  },
  {
    "de": "anstrengend",
    "tr": "ˈanʃtʁɛŋənt",
    "ru": "напряженный"
  },
  {
    "de": "einfach",
    "tr": "ˈaɪ̯nfax",
    "ru": "легкий"
  },
  {
    "de": "schwer",
    "tr": "ʃveːɐ̯",
    "ru": "трудный"
  },
  {
    "de": "der Kollege",
    "tr": "koˈleːɡə",
    "ru": "коллега"
  },
  {
    "de": "die Karriere",
    "tr": "kaˈʁiːʁə",
    "ru": "карьера"
  },
  {
    "de": "der Arbeitsplatz",
    "tr": "ˈaʁbaɪ̯t͡sˌplat͡s",
    "ru": "рабочее место"
  },
  {
    "de": "arbeitslos",
    "tr": "ˈaʁbaɪ̯t͡sˌloːs",
    "ru": "безработный"
  },
  {
    "de": "das Hobby",
    "tr": "ˈhɔbi",
    "ru": "хобби"
  },
  {
    "de": "die Freizeit",
    "tr": "ˈfʁaɪ̯t͡saɪ̯t",
    "ru": "свободное время"
  },
  {
    "de": "spielen",
    "tr": "ˈʃpiːlən",
    "ru": "играть"
  },
  {
    "de": "Fußball spielen",
    "tr": "ˈfuːsbal ˈʃpiːlən",
    "ru": "играть в футбол"
  },
  {
    "de": "Tennis spielen",
    "tr": "ˈtɛnɪs ˈʃpiːlən",
    "ru": "играть в теннис"
  },
  {
    "de": "schwimmen",
    "tr": "ˈʃvɪmən",
    "ru": "плавать"
  },
  {
    "de": "laufen",
    "tr": "ˈlaʊ̯fn̩",
    "ru": "бегать"
  },
  {
    "de": "wandern",
    "tr": "ˈvandɐn",
    "ru": "ходить в поход"
  },
  {
    "de": "Rad fahren",
    "tr": "ʁaːt ˈfaːʁən",
    "ru": "ездить на велосипеде"
  },
  {
    "de": "trainieren",
    "tr": "tʁaˈniːʁən",
    "ru": "тренироваться"
  },
  {
    "de": "ins Fitnessstudio gehen",
    "tr": "ɪns ˈfɪtnɛsˌʃtuːdio ˈɡeːən",
    "ru": "ходить в зал"
  },
  {
    "de": "lesen",
    "tr": "ˈleːzn̩",
    "ru": "читать"
  },
  {
    "de": "ein Buch lesen",
    "tr": "aɪ̯n buːx ˈleːzn̩",
    "ru": "читать книгу"
  },
  {
    "de": "schreiben",
    "tr": "ˈʃʁaɪ̯bn̩",
    "ru": "писать"
  },
  {
    "de": "zeichnen",
    "tr": "ˈt͡saɪ̯çnən",
    "ru": "рисовать (карандашом)"
  },
  {
    "de": "malen",
    "tr": "ˈmaːlən",
    "ru": "рисовать (красками)"
  },
  {
    "de": "fotografieren",
    "tr": "fotoɡʁaˈfiːʁən",
    "ru": "фотографировать"
  },
  {
    "de": "tanzen",
    "tr": "ˈtant͡sn̩",
    "ru": "танцевать"
  },
  {
    "de": "singen",
    "tr": "ˈzɪŋən",
    "ru": "петь"
  },
  {
    "de": "Musik hören",
    "tr": "muˈziːk ˈhøːʁən",
    "ru": "слушать музыку"
  },
  {
    "de": "fernsehen",
    "tr": "ˈfɛʁnˌzeːən",
    "ru": "смотреть телевизор"
  },
  {
    "de": "eine Serie schauen",
    "tr": "ˈeːnə ˈzeːʁi̯ə ˈʃaʊ̯ən",
    "ru": "смотреть сериал"
  },
  {
    "de": "ins Kino gehen",
    "tr": "ɪns ˈkiːno ˈɡeːən",
    "ru": "ходить в кино"
  },
  {
    "de": "ins Theater gehen",
    "tr": "ɪns teˈaːtɐ ˈɡeːən",
    "ru": "ходить в театр"
  },
  {
    "de": "kochen",
    "tr": "ˈkɔxn̩",
    "ru": "готовить"
  },
  {
    "de": "backen",
    "tr": "ˈbakn̩",
    "ru": "печь"
  },
  {
    "de": "Computerspiele spielen",
    "tr": "kɔmˈpjuːtɐˌʃpiːlə ˈʃpiːlən",
    "ru": "играть в компьютерные игры"
  },
  {
    "de": "Videospiele spielen",
    "tr": "ˈviːde.oˌʃpiːlə ˈʃpiːlən",
    "ru": "играть в видеоигры"
  },
  {
    "de": "reisen",
    "tr": "ˈʁaɪ̯zn̩",
    "ru": "путешествовать"
  },
  {
    "de": "Freunde treffen",
    "tr": "ˈfʁɔɪ̯ndə ˈtʁɛfn̩",
    "ru": "встречаться с друзьями"
  },
  {
    "de": "ausgehen",
    "tr": "ˈaʊ̯sˌɡeːən",
    "ru": "выходить в свет"
  },
  {
    "de": "spazieren gehen",
    "tr": "ʃpaˈt͡siːʁən ˈɡeːən",
    "ru": "гулять"
  },
  {
    "de": "Entspannung",
    "tr": "ɛntˈʃpanʊŋ",
    "ru": "расслабление"
  },
  {
    "de": "sich entspannen",
    "tr": "zɪç ɛntˈʃpanən",
    "ru": "расслабляться"
  },
  {
    "de": "die Freizeit genießen",
    "tr": "ˈfʁaɪ̯t͡saɪ̯t ɡəˈniːsən",
    "ru": "наслаждаться свободным временем"
  },
  {
    "de": "Gitarre spielen",
    "tr": "ɡiˈtaʁə ˈʃpiːlən",
    "ru": "играть на гитаре"
  },
  {
    "de": "ein Instrument spielen",
    "tr": "aɪ̯n ɪnstruˈmɛnt ˈʃpiːlən",
    "ru": "играть на инструменте"
  },
  {
    "de": "sammeln",
    "tr": "ˈzaməln̩",
    "ru": "коллекционировать"
  },
  {
    "de": "Brettspiele",
    "tr": "ˈbʁɛtˌʃpiːlə",
    "ru": "настольные игры"
  },
  {
    "de": "die Karte",
    "tr": "ˈkaʁtə",
    "ru": "карта, карточка"
  },
  {
    "de": "der Ausflug",
    "tr": "ˈaʊ̯sˌfluːk",
    "ru": "поездка, вылазка"
  },
  {
    "de": "joggen",
    "tr": "ˈd͡ʒɔɡn̩",
    "ru": "бегать трусцой"
  },
  {
    "de": "Yoga machen",
    "tr": "ˈjoːɡa ˈmaxn̩",
    "ru": "заниматься йогой"
  },
  {
    "de": "entspannende Musik",
    "tr": "ɛntˈʃpanəndə muˈziːk",
    "ru": "расслабляющая музыка"
  },
  {
    "de": "sich ausruhen",
    "tr": "zɪç ˈaʊ̯sˌʁuːən",
    "ru": "отдыхать"
  },
  {
    "de": "faulenzen",
    "tr": "ˈfaʊ̯lɛnt͡sən",
    "ru": "лениться, бездельничать"
  },
  {
    "de": "Zeit mit der Familie",
    "tr": "t͡saɪ̯t mɪt deːɐ̯ faˈmiːli̯ə",
    "ru": "время с семьей"
  },
  {
    "de": "Zeit mit Freunden",
    "tr": "t͡saɪ̯t mɪt ˈfʁɔɪ̯ndn̩",
    "ru": "время с друзьями"
  },
  {
    "de": "das Interesse",
    "tr": "ɪntəˈʁɛsə",
    "ru": "интерес"
  },
  {
    "de": "sich interessieren für",
    "tr": "zɪç ɪntəʁɛˈsiːʁən fyːɐ̯",
    "ru": "интересоваться чем-то"
  },
  {
    "de": "das Wetter",
    "tr": "ˈvɛtɐ",
    "ru": "погода"
  },
  {
    "de": "die Sonne",
    "tr": "ˈzɔnə",
    "ru": "солнце"
  },
  {
    "de": "sonnig",
    "tr": "ˈzɔnɪç",
    "ru": "солнечно"
  },
  {
    "de": "der Regen",
    "tr": "ˈʁeːɡn̩",
    "ru": "дождь"
  },
  {
    "de": "regnen",
    "tr": "ˈʁeːɡnən",
    "ru": "идет дождь"
  },
  {
    "de": "der Schnee",
    "tr": "ʃneː",
    "ru": "снег"
  },
  {
    "de": "schneien",
    "tr": "ˈʃnaɪ̯ən",
    "ru": "идет снег"
  },
  {
    "de": "bewölkt",
    "tr": "bəˈvœlkt",
    "ru": "пасмурно"
  },
  {
    "de": "der Wind",
    "tr": "vɪnt",
    "ru": "ветер"
  },
  {
    "de": "windig",
    "tr": "ˈvɪndɪç",
    "ru": "ветрено"
  },
  {
    "de": "der Sturm",
    "tr": "ʃtʊʁm",
    "ru": "буря"
  },
  {
    "de": "warm",
    "tr": "vaʁm",
    "ru": "теплый"
  },
  {
    "de": "kalt",
    "tr": "kalt",
    "ru": "холодный"
  },
  {
    "de": "heiß",
    "tr": "haɪ̯s",
    "ru": "жаркий"
  },
  {
    "de": "die Temperatur",
    "tr": "tɛmpɛʁaˈtuːɐ̯",
    "ru": "температура"
  },
  {
    "de": "das Klima",
    "tr": "ˈkliːma",
    "ru": "климат"
  },
  {
    "de": "die Jahreszeit",
    "tr": "ˈjaːʁəst͡saɪ̯t",
    "ru": "время года"
  },
  {
    "de": "der Frühling",
    "tr": "ˈfʁyːlɪŋ",
    "ru": "весна"
  },
  {
    "de": "der Sommer",
    "tr": "ˈzɔmɐ",
    "ru": "лето"
  },
  {
    "de": "der Herbst",
    "tr": "hɛʁpst",
    "ru": "осень"
  },
  {
    "de": "der Winter",
    "tr": "ˈvɪntɐ",
    "ru": "зима"
  },
  {
    "de": "die Natur",
    "tr": "naˈtuːɐ̯",
    "ru": "природа"
  },
  {
    "de": "der Baum",
    "tr": "baʊ̯m",
    "ru": "дерево"
  },
  {
    "de": "die Blume",
    "tr": "ˈbluːmə",
    "ru": "цветок"
  },
  {
    "de": "die Pflanze",
    "tr": "ˈpflant͡sə",
    "ru": "растение"
  },
  {
    "de": "das Gras",
    "tr": "ɡʁaːs",
    "ru": "трава"
  },
  {
    "de": "der Wald",
    "tr": "valt",
    "ru": "лес"
  },
  {
    "de": "der See",
    "tr": "zeː",
    "ru": "озеро"
  },
  {
    "de": "der Fluss",
    "tr": "flʊs",
    "ru": "река"
  },
  {
    "de": "das Meer",
    "tr": "meːɐ̯",
    "ru": "море"
  },
  {
    "de": "der Strand",
    "tr": "ʃtʁant",
    "ru": "пляж"
  },
  {
    "de": "der Berg",
    "tr": "bɛʁk",
    "ru": "гора"
  },
  {
    "de": "das Tal",
    "tr": "taːl",
    "ru": "долина"
  },
  {
    "de": "der Himmel",
    "tr": "ˈhɪml̩",
    "ru": "небо"
  },
  {
    "de": "die Wolke",
    "tr": "ˈvɔlkə",
    "ru": "облако"
  },
  {
    "de": "der Stern",
    "tr": "ʃtɛʁn",
    "ru": "звезда"
  },
  {
    "de": "der Mond",
    "tr": "moːnt",
    "ru": "луна"
  },
  {
    "de": "klarer Himmel",
    "tr": "ˈklaːʁɐ ˈhɪml̩",
    "ru": "чистое небо"
  },
  {
    "de": "stark regnen",
    "tr": "ʃtaʁk ˈʁeːɡnən",
    "ru": "идет сильный дождь"
  },
  {
    "de": "leicht regnen",
    "tr": "laɪ̯çt ˈʁeːɡnən",
    "ru": "моросит"
  },
  {
    "de": "das Gewitter",
    "tr": "ɡəˈvɪtɐ",
    "ru": "гроза"
  },
  {
    "de": "die Luft",
    "tr": "lʊft",
    "ru": "воздух"
  },
  {
    "de": "die frische Luft",
    "tr": "ˈfʁɪʃə lʊft",
    "ru": "свежий воздух"
  },
  {
    "de": "draußen",
    "tr": "ˈdʁaʊ̯sn̩",
    "ru": "на улице"
  },
  {
    "de": "drinnen",
    "tr": "ˈdʁɪnən",
    "ru": "внутри"
  },
  {
    "de": "spazieren gehen",
    "tr": "ʃpaˈt͡siːʁən ˈɡeːən",
    "ru": "гулять"
  },
  {
    "de": "die Jahreszeiten wechseln",
    "tr": "ˈjaːʁəst͡saɪ̯tn̩ ˈvɛxsl̩n̩",
    "ru": "смена времен года"
  },
  {
    "de": "das Klima ist mild",
    "tr": "ˈkliːma ɪst mɪlt",
    "ru": "климат мягкий"
  },
  {
    "de": "es ist warm",
    "tr": "ɛs ɪst vaʁm",
    "ru": "тепло"
  },
  {
    "de": "es ist kalt",
    "tr": "ɛs ɪst kalt",
    "ru": "холодно"
  },
  {
    "de": "das Tier",
    "tr": "tiːɐ̯",
    "ru": "животное"
  },
  {
    "de": "der Hund",
    "tr": "hʊnt",
    "ru": "собака"
  },
  {
    "de": "die Katze",
    "tr": "ˈkat͡sə",
    "ru": "кошка"
  },
  {
    "de": "der Vogel",
    "tr": "ˈfoːɡl̩",
    "ru": "птица"
  },
  {
    "de": "der Fisch",
    "tr": "fɪʃ",
    "ru": "рыба"
  },
  {
    "de": "das Pferd",
    "tr": "pfeːʁt",
    "ru": "лошадь"
  },
  {
    "de": "die Maus",
    "tr": "maʊ̯s",
    "ru": "мышь"
  },
  {
    "de": "die Kuh",
    "tr": "kuː",
    "ru": "корова"
  },
  {
    "de": "das Schwein",
    "tr": "ʃvaɪ̯n",
    "ru": "свинья"
  },
  {
    "de": "das Schaf",
    "tr": "ʃaːf",
    "ru": "овца"
  },
  {
    "de": "die Ziege",
    "tr": "ˈt͡siːɡə",
    "ru": "коза"
  },
  {
    "de": "das Huhn",
    "tr": "huːn",
    "ru": "курица"
  },
  {
    "de": "die Ente",
    "tr": "ˈɛntə",
    "ru": "утка"
  },
  {
    "de": "die Gans",
    "tr": "ɡans",
    "ru": "гусь"
  },
  {
    "de": "der Hahn",
    "tr": "haːn",
    "ru": "петух"
  },
  {
    "de": "der Hase",
    "tr": "ˈhaːzə",
    "ru": "заяц"
  },
  {
    "de": "das Kaninchen",
    "tr": "kaˈniːnçən",
    "ru": "кролик"
  },
  {
    "de": "die Schildkröte",
    "tr": "ˈʃɪltˌkʁøːtə",
    "ru": "черепаха"
  },
  {
    "de": "der Löwe",
    "tr": "ˈløːvə",
    "ru": "лев"
  },
  {
    "de": "der Tiger",
    "tr": "ˈtiːɡɐ",
    "ru": "тигр"
  },
  {
    "de": "der Elefant",
    "tr": "eleˈfant",
    "ru": "слон"
  },
  {
    "de": "der Bär",
    "tr": "bɛːɐ̯",
    "ru": "медведь"
  },
  {
    "de": "der Wolf",
    "tr": "vɔlf",
    "ru": "волк"
  },
  {
    "de": "der Fuchs",
    "tr": "fʊks",
    "ru": "лиса"
  },
  {
    "de": "der Affe",
    "tr": "ˈafə",
    "ru": "обезьяна"
  },
  {
    "de": "das Kamel",
    "tr": "kaˈmeːl",
    "ru": "верблюд"
  },
  {
    "de": "das Krokodil",
    "tr": "kʁokoˈdiːl",
    "ru": "крокодил"
  },
  {
    "de": "die Schlange",
    "tr": "ˈʃlaŋə",
    "ru": "змея"
  },
  {
    "de": "die Spinne",
    "tr": "ˈʃpɪnə",
    "ru": "паук"
  },
  {
    "de": "die Biene",
    "tr": "ˈbiːnə",
    "ru": "пчела"
  },
  {
    "de": "die Fliege",
    "tr": "ˈfliːɡə",
    "ru": "муха"
  },
  {
    "de": "die Ameise",
    "tr": "ˈaːˌmaɪ̯zə",
    "ru": "муравей"
  },
  {
    "de": "der Frosch",
    "tr": "fʁɔʃ",
    "ru": "лягушка"
  },
  {
    "de": "der Pinguin",
    "tr": "ˈpɪŋɡu.iːn",
    "ru": "пингвин"
  },
  {
    "de": "das Tierheim",
    "tr": "ˈtiːɐ̯ˌhaɪ̯m",
    "ru": "приют для животных"
  },
  {
    "de": "der Tierarzt",
    "tr": "ˈtiːɐ̯ˌaʁt͡st",
    "ru": "ветеринар"
  },
  {
    "de": "streicheln",
    "tr": "ˈʃtʁaɪ̯çln̩",
    "ru": "гладить"
  },
  {
    "de": "füttern",
    "tr": "ˈfʏtɐn",
    "ru": "кормить"
  },
  {
    "de": "die Leine",
    "tr": "ˈlaɪ̯nə",
    "ru": "поводок"
  },
  {
    "de": "das Haustier",
    "tr": "ˈhaʊ̯sˌtiːɐ̯",
    "ru": "домашнее животное"
  },
  {
    "de": "wild",
    "tr": "vɪlt",
    "ru": "дикий"
  },
  {
    "de": "zahm",
    "tr": "tsaːm",
    "ru": "ручной"
  },
  {
    "de": "das Fell",
    "tr": "fɛl",
    "ru": "шерсть"
  },
  {
    "de": "die Pfote",
    "tr": "ˈpfoːtə",
    "ru": "лапа"
  },
  {
    "de": "der Schwanz",
    "tr": "ʃvant͡s",
    "ru": "хвост"
  },
  {
    "de": "das Horn",
    "tr": "hɔʁn",
    "ru": "рог"
  },
  {
    "de": "bellen",
    "tr": "ˈbɛln̩",
    "ru": "лаять"
  },
  {
    "de": "miauen",
    "tr": "miˈaʊ̯ən",
    "ru": "мяукать"
  },
  {
    "de": "das Küken",
    "tr": "ˈkyːkn̩",
    "ru": "цыпленок"
  },
  {
    "de": "das Futter",
    "tr": "ˈfʊtɐ",
    "ru": "корм"
  },
  {
    "de": "das Haus",
    "tr": "haʊ̯s",
    "ru": "дом"
  },
  {
    "de": "die Wohnung",
    "tr": "ˈvoːnʊŋ",
    "ru": "квартира"
  },
  {
    "de": "der Raum",
    "tr": "ʁaʊ̯m",
    "ru": "комната"
  },
  {
    "de": "das Zimmer",
    "tr": "ˈt͡sɪmɐ",
    "ru": "комната"
  },
  {
    "de": "das Wohnzimmer",
    "tr": "ˈvoːnˌt͡sɪmɐ",
    "ru": "гостиная"
  },
  {
    "de": "das Schlafzimmer",
    "tr": "ˈʃlaːfˌt͡sɪmɐ",
    "ru": "спальня"
  },
  {
    "de": "die Küche",
    "tr": "ˈkʏçə",
    "ru": "кухня"
  },
  {
    "de": "das Bad",
    "tr": "baːt",
    "ru": "ванная"
  },
  {
    "de": "der Flur",
    "tr": "fluːɐ̯",
    "ru": "коридор"
  },
  {
    "de": "der Balkon",
    "tr": "balˈkoːn",
    "ru": "балкон"
  },
  {
    "de": "der Garten",
    "tr": "ˈɡaʁtn̩",
    "ru": "сад"
  },
  {
    "de": "die Möbel",
    "tr": "ˈmøːbl̩",
    "ru": "мебель"
  },
  {
    "de": "der Tisch",
    "tr": "tɪʃ",
    "ru": "стол"
  },
  {
    "de": "der Stuhl",
    "tr": "ʃtuːl",
    "ru": "стул"
  },
  {
    "de": "das Bett",
    "tr": "bɛt",
    "ru": "кровать"
  },
  {
    "de": "der Schrank",
    "tr": "ʃʁaŋk",
    "ru": "шкаф"
  },
  {
    "de": "das Sofa",
    "tr": "ˈzoːfa",
    "ru": "диван"
  },
  {
    "de": "der Teppich",
    "tr": "ˈtɛpɪç",
    "ru": "ковёр"
  },
  {
    "de": "die Lampe",
    "tr": "ˈlampə",
    "ru": "лампа"
  },
  {
    "de": "der Spiegel",
    "tr": "ˈʃpiːɡl̩",
    "ru": "зеркало"
  },
  {
    "de": "der Fernseher",
    "tr": "ˈfɛʁnˌzeːɐ̯",
    "ru": "телевизор"
  },
  {
    "de": "die Waschmaschine",
    "tr": "ˈvaʃmaˌʃiːnə",
    "ru": "стиральная машина"
  },
  {
    "de": "der Kühlschrank",
    "tr": "ˈkyːlˌʃʁaŋk",
    "ru": "холодильник"
  },
  {
    "de": "der Herd",
    "tr": "heːɐ̯t",
    "ru": "плита"
  },
  {
    "de": "der Ofen",
    "tr": "ˈoːfn̩",
    "ru": "духовка"
  },
  {
    "de": "die Tür",
    "tr": "tyːɐ̯",
    "ru": "дверь"
  },
  {
    "de": "das Fenster",
    "tr": "ˈfɛn.stɐ",
    "ru": "окно"
  },
  {
    "de": "die Wand",
    "tr": "vant",
    "ru": "стена"
  },
  {
    "de": "der Boden",
    "tr": "ˈboːdn̩",
    "ru": "пол"
  },
  {
    "de": "sauber",
    "tr": "ˈzaʊ̯bɐ",
    "ru": "чистый"
  },
  {
    "de": "schmutzig",
    "tr": "ˈʃmʊt͡sɪç",
    "ru": "грязный"
  },
  {
    "de": "putzen",
    "tr": "ˈpʊt͡sn̩",
    "ru": "убирать"
  },
  {
    "de": "aufräumen",
    "tr": "ˈaʊ̯fˌʁɔɪ̯mən",
    "ru": "прибраться"
  },
  {
    "de": "waschen",
    "tr": "ˈvaʃn̩",
    "ru": "стирать"
  },
  {
    "de": "kochen",
    "tr": "ˈkɔxn̩",
    "ru": "готовить"
  },
  {
    "de": "spülen",
    "tr": "ˈʃpyːlən",
    "ru": "мыть посуду"
  },
  {
    "de": "die Rechnung",
    "tr": "ˈʁɛçnʊŋ",
    "ru": "квитанция"
  },
  {
    "de": "die Miete",
    "tr": "ˈmiːtə",
    "ru": "аренда"
  },
  {
    "de": "mieten",
    "tr": "ˈmiːtən",
    "ru": "снимать"
  },
  {
    "de": "vermieten",
    "tr": "fɛɐ̯ˈmiːtən",
    "ru": "сдавать"
  },
  {
    "de": "der Nachbar",
    "tr": "ˈnaχbaʁ",
    "ru": "сосед"
  },
  {
    "de": "die Nachbarin",
    "tr": "ˈnaχbaʁɪn",
    "ru": "соседка"
  },
  {
    "de": "das Zuhause",
    "tr": "t͡suˈhaʊ̯zə",
    "ru": "дом (уют)"
  },
  {
    "de": "wohnen",
    "tr": "ˈvoːnən",
    "ru": "жить"
  },
  {
    "de": "einziehen",
    "tr": "ˈaɪ̯nt͡siːən",
    "ru": "въезжать"
  },
  {
    "de": "ausziehen",
    "tr": "ˈaʊ̯st͡siːən",
    "ru": "съезжать"
  },
  {
    "de": "das Gerät",
    "tr": "ɡəˈʁɛːt",
    "ru": "прибор"
  },
  {
    "de": "kaputt",
    "tr": "kaˈpʊt",
    "ru": "сломанный"
  },
  {
    "de": "sein",
    "tr": "zaɪ̯n",
    "ru": "быть"
  },
  {
    "de": "haben",
    "tr": "ˈhaːbn̩",
    "ru": "иметь"
  },
  {
    "de": "werden",
    "tr": "ˈveːɐ̯dn̩",
    "ru": "становиться"
  },
  {
    "de": "gehen",
    "tr": "ˈɡeːən",
    "ru": "идти"
  },
  {
    "de": "fahren",
    "tr": "ˈfaːʁən",
    "ru": "ехать"
  },
  {
    "de": "kommen",
    "tr": "ˈkɔmn̩",
    "ru": "приходить"
  },
  {
    "de": "laufen",
    "tr": "ˈlaʊ̯fn̩",
    "ru": "бежать"
  },
  {
    "de": "sprechen",
    "tr": "ˈʃpʁɛçn̩",
    "ru": "говорить"
  },
  {
    "de": "sagen",
    "tr": "ˈzaːɡn̩",
    "ru": "сказать"
  },
  {
    "de": "fragen",
    "tr": "ˈfʁaːɡn̩",
    "ru": "спрашивать"
  },
  {
    "de": "antworten",
    "tr": "ˈantvɔʁtn̩",
    "ru": "отвечать"
  },
  {
    "de": "sehen",
    "tr": "ˈzeːən",
    "ru": "видеть"
  },
  {
    "de": "hören",
    "tr": "ˈhøːʁən",
    "ru": "слышать"
  },
  {
    "de": "essen",
    "tr": "ˈɛsn̩",
    "ru": "есть"
  },
  {
    "de": "trinken",
    "tr": "ˈtʁɪŋkn̩",
    "ru": "пить"
  },
  {
    "de": "schlafen",
    "tr": "ˈʃlaːfn̩",
    "ru": "спать"
  },
  {
    "de": "arbeiten",
    "tr": "ˈaʁbaɪ̯tn̩",
    "ru": "работать"
  },
  {
    "de": "lernen",
    "tr": "ˈlɛʁnən",
    "ru": "учить"
  },
  {
    "de": "studieren",
    "tr": "ʃtuˈdiːʁən",
    "ru": "изучать"
  },
  {
    "de": "spielen",
    "tr": "ˈʃpiːlən",
    "ru": "играть"
  },
  {
    "de": "schreiben",
    "tr": "ˈʃʁaɪ̯bn̩",
    "ru": "писать"
  },
  {
    "de": "lesen",
    "tr": "ˈleːzn̩",
    "ru": "читать"
  },
  {
    "de": "machen",
    "tr": "ˈmaxn̩",
    "ru": "делать"
  },
  {
    "de": "nehmen",
    "tr": "ˈneːmən",
    "ru": "брать"
  },
  {
    "de": "geben",
    "tr": "ˈɡeːbn̩",
    "ru": "давать"
  },
  {
    "de": "finden",
    "tr": "ˈfɪndn̩",
    "ru": "находить"
  },
  {
    "de": "suchen",
    "tr": "ˈzuːxn̩",
    "ru": "искать"
  },
  {
    "de": "bringen",
    "tr": "ˈbʁɪŋən",
    "ru": "приносить"
  },
  {
    "de": "bleiben",
    "tr": "ˈblaɪ̯bn̩",
    "ru": "оставаться"
  },
  {
    "de": "öffnen",
    "tr": "ˈœfnən",
    "ru": "открывать"
  },
  {
    "de": "schließen",
    "tr": "ˈʃliːsən",
    "ru": "закрывать"
  },
  {
    "de": "beginnen",
    "tr": "bəˈɡɪnən",
    "ru": "начинать"
  },
  {
    "de": "enden",
    "tr": "ˈɛndn̩",
    "ru": "заканчивать"
  },
  {
    "de": "helfen",
    "tr": "ˈhɛlfn̩",
    "ru": "помогать"
  },
  {
    "de": "brauchen",
    "tr": "ˈbʁaʊ̯xn̩",
    "ru": "нуждаться"
  },
  {
    "de": "lernen",
    "tr": "ˈlɛʁnən",
    "ru": "учить"
  },
  {
    "de": "ziehen",
    "tr": "ˈt͡siːən",
    "ru": "тянуть"
  },
  {
    "de": "tragen",
    "tr": "ˈtʁaːɡn̩",
    "ru": "нести"
  },
  {
    "de": "spielen",
    "tr": "ˈʃpiːlən",
    "ru": "играть"
  },
  {
    "de": "denken",
    "tr": "ˈdɛŋkn̩",
    "ru": "думать"
  },
  {
    "de": "glauben",
    "tr": "ˈɡlaʊ̯bn̩",
    "ru": "верить"
  },
  {
    "de": "hoffen",
    "tr": "ˈhɔfn̩",
    "ru": "надеяться"
  },
  {
    "de": "reisen",
    "tr": "ˈʁaɪ̯zn̩",
    "ru": "путешествовать"
  },
  {
    "de": "putzen",
    "tr": "ˈpʊt͡sn̩",
    "ru": "убирать"
  },
  {
    "de": "kochen",
    "tr": "ˈkɔxn̩",
    "ru": "готовить"
  },
  {
    "de": "duschen",
    "tr": "ˈduːʃn̩",
    "ru": "принимать душ"
  },
  {
    "de": "baden",
    "tr": "ˈbaːdn̩",
    "ru": "купаться"
  },
  {
    "de": "anziehen",
    "tr": "ˈant͡siːən",
    "ru": "одевать"
  },
  {
    "de": "ausziehen",
    "tr": "ˈaʊ̯st͡siːən",
    "ru": "раздевать"
  },
  {
    "de": "groß",
    "tr": "ɡʁoːs",
    "ru": "большой"
  },
  {
    "de": "klein",
    "tr": "klaɪ̯n",
    "ru": "маленький"
  },
  {
    "de": "lang",
    "tr": "laŋ",
    "ru": "длинный"
  },
  {
    "de": "kurz",
    "tr": "kʊʁt͡s",
    "ru": "короткий"
  },
  {
    "de": "schön",
    "tr": "ʃøːn",
    "ru": "красивый"
  },
  {
    "de": "hässlich",
    "tr": "ˈhɛslɪç",
    "ru": "некрасивый"
  },
  {
    "de": "gut",
    "tr": "ɡuːt",
    "ru": "хороший"
  },
  {
    "de": "schlecht",
    "tr": "ʃlɛçt",
    "ru": "плохой"
  },
  {
    "de": "neu",
    "tr": "nɔʏ̯",
    "ru": "новый"
  },
  {
    "de": "alt",
    "tr": "alt",
    "ru": "старый"
  },
  {
    "de": "teuer",
    "tr": "ˈtɔʏ̯ɐ",
    "ru": "дорогой"
  },
  {
    "de": "billig",
    "tr": "ˈbɪlɪç",
    "ru": "дешёвый"
  },
  {
    "de": "hell",
    "tr": "hɛl",
    "ru": "светлый"
  },
  {
    "de": "dunkel",
    "tr": "ˈdʊŋkl̩",
    "ru": "тёмный"
  },
  {
    "de": "warm",
    "tr": "vaʁm",
    "ru": "тёплый"
  },
  {
    "de": "kalt",
    "tr": "kalt",
    "ru": "холодный"
  },
  {
    "de": "schnell",
    "tr": "ʃnɛl",
    "ru": "быстрый"
  },
  {
    "de": "langsam",
    "tr": "ˈlaŋzaːm",
    "ru": "медленный"
  },
  {
    "de": "laut",
    "tr": "laʊ̯t",
    "ru": "громкий"
  },
  {
    "de": "leise",
    "tr": "ˈlaɪ̯zə",
    "ru": "тихий"
  },
  {
    "de": "voll",
    "tr": "fɔl",
    "ru": "полный"
  },
  {
    "de": "leer",
    "tr": "leːɐ̯",
    "ru": "пустой"
  },
  {
    "de": "sauber",
    "tr": "ˈzaʊ̯bɐ",
    "ru": "чистый"
  },
  {
    "de": "schmutzig",
    "tr": "ˈʃmʊt͡sɪç",
    "ru": "грязный"
  },
  {
    "de": "stark",
    "tr": "ʃtaʁk",
    "ru": "сильный"
  },
  {
    "de": "schwach",
    "tr": "ʃvax",
    "ru": "слабый"
  },
  {
    "de": "freundlich",
    "tr": "ˈfʁɔɪ̯ntlɪç",
    "ru": "дружелюбный"
  },
  {
    "de": "unfreundlich",
    "tr": "ˈʊnfʁɔɪ̯ntlɪç",
    "ru": "недружелюбный"
  },
  {
    "de": "glücklich",
    "tr": "ˈɡlʏklɪç",
    "ru": "счастливый"
  },
  {
    "de": "traurig",
    "tr": "ˈtʁaʊ̯ʁɪç",
    "ru": "грустный"
  },
  {
    "de": "ruhig",
    "tr": "ˈʁuːɪç",
    "ru": "спокойный"
  },
  {
    "de": "nervös",
    "tr": "nɛʁˈvøːs",
    "ru": "нервный"
  },
  {
    "de": "müde",
    "tr": "ˈmyːdə",
    "ru": "уставший"
  },
  {
    "de": "krank",
    "tr": "kʁaŋk",
    "ru": "больной"
  },
  {
    "de": "gesund",
    "tr": "ɡəˈzʊnt",
    "ru": "здоровый"
  },
  {
    "de": "reich",
    "tr": "ʁaɪ̯ç",
    "ru": "богатый"
  },
  {
    "de": "arm",
    "tr": "aʁm",
    "ru": "бедный"
  },
  {
    "de": "interessant",
    "tr": "ɪntəʁɛˈzant",
    "ru": "интересный"
  },
  {
    "de": "langweilig",
    "tr": "ˈlaŋˌvaɪ̯lɪç",
    "ru": "скучный"
  },
  {
    "de": "leicht",
    "tr": "laɪ̯çt",
    "ru": "лёгкий"
  },
  {
    "de": "schwer",
    "tr": "ʃveːɐ̯",
    "ru": "тяжёлый"
  },
  {
    "de": "richtig",
    "tr": "ˈʁɪçtɪç",
    "ru": "правильный"
  },
  {
    "de": "falsch",
    "tr": "falʃ",
    "ru": "неправильный"
  },
  {
    "de": "tief",
    "tr": "tiːf",
    "ru": "глубокий"
  },
  {
    "de": "hoch",
    "tr": "hoːx",
    "ru": "высокий"
  },
  {
    "de": "ruhig",
    "tr": "ˈʁuːɪç",
    "ru": "тихий"
  },
  {
    "de": "wild",
    "tr": "vɪlt",
    "ru": "дикий"
  },
  {
    "de": "weich",
    "tr": "vaɪ̯ç",
    "ru": "мягкий"
  },
  {
    "de": "hart",
    "tr": "haʁt",
    "ru": "твёрдый"
  },
  {
    "de": "nah",
    "tr": "naː",
    "ru": "близкий"
  },
  {
    "de": "weit",
    "tr": "vaɪ̯t",
    "ru": "далёкий"
  },
  {
    "de": "jetzt",
    "tr": "jɛt͡st",
    "ru": "сейчас"
  },
  {
    "de": "bald",
    "tr": "balt",
    "ru": "скоро"
  },
  {
    "de": "schon",
    "tr": "ʃoːn",
    "ru": "уже"
  },
  {
    "de": "noch",
    "tr": "nɔx",
    "ru": "ещё"
  },
  {
    "de": "immer",
    "tr": "ˈɪmɐ",
    "ru": "всегда"
  },
  {
    "de": "nie",
    "tr": "niː",
    "ru": "никогда"
  },
  {
    "de": "manchmal",
    "tr": "ˈmançmaːl",
    "ru": "иногда"
  },
  {
    "de": "oft",
    "tr": "ɔft",
    "ru": "часто"
  },
  {
    "de": "selten",
    "tr": "ˈzɛltn̩",
    "ru": "редко"
  },
  {
    "de": "gestern",
    "tr": "ˈɡɛstɐn",
    "ru": "вчера"
  },
  {
    "de": "heute",
    "tr": "ˈhɔʏ̯tə",
    "ru": "сегодня"
  },
  {
    "de": "morgen",
    "tr": "ˈmɔʁɡn̩",
    "ru": "завтра"
  },
  {
    "de": "draußen",
    "tr": "ˈdʁaʊ̯sn̩",
    "ru": "снаружи"
  },
  {
    "de": "drinnen",
    "tr": "ˈdʁɪnən",
    "ru": "внутри"
  },
  {
    "de": "oben",
    "tr": "ˈoːbn̩",
    "ru": "сверху"
  },
  {
    "de": "unten",
    "tr": "ˈʊntn̩",
    "ru": "снизу"
  },
  {
    "de": "links",
    "tr": "lɪŋks",
    "ru": "налево"
  },
  {
    "de": "rechts",
    "tr": "ʁɛçts",
    "ru": "направо"
  },
  {
    "de": "hinten",
    "tr": "ˈhɪntn̩",
    "ru": "сзади"
  },
  {
    "de": "vorne",
    "tr": "ˈfɔʁnə",
    "ru": "спереди"
  },
  {
    "de": "überall",
    "tr": "ˈyːbɐʔal",
    "ru": "везде"
  },
  {
    "de": "nirgendwo",
    "tr": "ˈnɪʁɡnt͡svoː",
    "ru": "нигде"
  },
  {
    "de": "hier",
    "tr": "hiːɐ̯",
    "ru": "здесь"
  },
  {
    "de": "dort",
    "tr": "dɔʁt",
    "ru": "там"
  },
  {
    "de": "zusammen",
    "tr": "t͡suˈzamən",
    "ru": "вместе"
  },
  {
    "de": "allein",
    "tr": "aˈlaɪ̯n",
    "ru": "один"
  },
  {
    "de": "genau",
    "tr": "ɡəˈnaʊ̯",
    "ru": "точно"
  },
  {
    "de": "ungefähr",
    "tr": "ˈʊnɡəfeːɐ̯",
    "ru": "примерно"
  },
  {
    "de": "schnell",
    "tr": "ʃnɛl",
    "ru": "быстро"
  },
  {
    "de": "langsam",
    "tr": "ˈlaŋzaːm",
    "ru": "медленно"
  },
  {
    "de": "gerne",
    "tr": "ˈɡɛʁnə",
    "ru": "охотно"
  },
  {
    "de": "wirklich",
    "tr": "ˈvɪʁklɪç",
    "ru": "действительно"
  },
  {
    "de": "vielleicht",
    "tr": "fiˈlaɪ̯çt",
    "ru": "возможно"
  },
  {
    "de": "leider",
    "tr": "ˈlaɪ̯dɐ",
    "ru": "к сожалению"
  },
  {
    "de": "zum Glück",
    "tr": "t͡sʊm ɡlʏk",
    "ru": "к счастью"
  },
  {
    "de": "plötzlich",
    "tr": "ˈplœt͡slɪç",
    "ru": "внезапно"
  },
  {
    "de": "sofort",
    "tr": "zoˈfɔʁt",
    "ru": "сразу"
  },
  {
    "de": "gleich",
    "tr": "ɡlaɪ̯ç",
    "ru": "сейчас же"
  },
  {
    "de": "vorhin",
    "tr": "ˈfoːʁhɪn",
    "ru": "только что"
  },
  {
    "de": "nachher",
    "tr": "ˈnaːxheːɐ̯",
    "ru": "позже"
  },
  {
    "de": "eben",
    "tr": "ˈeːbn̩",
    "ru": "именно"
  },
  {
    "de": "fast",
    "tr": "fast",
    "ru": "почти"
  },
  {
    "de": "ganz",
    "tr": "ɡant͡s",
    "ru": "совсем"
  },
  {
    "de": "weiter",
    "tr": "ˈvaɪ̯tɐ",
    "ru": "дальше"
  },
  {
    "de": "zurück",
    "tr": "t͡sʊˈʁʏk",
    "ru": "назад"
  },
  {
    "de": "oben",
    "tr": "ˈoːbn̩",
    "ru": "наверху"
  },
  {
    "de": "vorwärts",
    "tr": "ˈfoːʁvɛʁt͡s",
    "ru": "вперёд"
  },
  {
    "de": "an",
    "tr": "an",
    "ru": "на (вертикально)"
  },
  {
    "de": "auf",
    "tr": "aʊ̯f",
    "ru": "на (горизонтально)"
  },
  {
    "de": "in",
    "tr": "ɪn",
    "ru": "в"
  },
  {
    "de": "unter",
    "tr": "ˈʊntɐ",
    "ru": "под"
  },
  {
    "de": "über",
    "tr": "ˈyːbɐ",
    "ru": "над"
  },
  {
    "de": "neben",
    "tr": "ˈneːbn̩",
    "ru": "рядом"
  },
  {
    "de": "zwischen",
    "tr": "ˈt͡svɪʃn̩",
    "ru": "между"
  },
  {
    "de": "hinter",
    "tr": "ˈhɪntɐ",
    "ru": "за"
  },
  {
    "de": "vor",
    "tr": "foːɐ̯",
    "ru": "перед"
  },
  {
    "de": "mit",
    "tr": "mɪt",
    "ru": "с"
  },
  {
    "de": "ohne",
    "tr": "ˈoːnə",
    "ru": "без"
  },
  {
    "de": "für",
    "tr": "fyːɐ̯",
    "ru": "для"
  },
  {
    "de": "gegen",
    "tr": "ˈɡeːɡn̩",
    "ru": "против"
  },
  {
    "de": "um",
    "tr": "ʊm",
    "ru": "вокруг"
  },
  {
    "de": "bei",
    "tr": "baɪ̯",
    "ru": "у"
  },
  {
    "de": "zu",
    "tr": "t͡suː",
    "ru": "к"
  },
  {
    "de": "nach",
    "tr": "naːx",
    "ru": "в / после"
  },
  {
    "de": "aus",
    "tr": "aʊ̯s",
    "ru": "из"
  },
  {
    "de": "seit",
    "tr": "zaɪ̯t",
    "ru": "с (времени)"
  },
  {
    "de": "von",
    "tr": "fɔn",
    "ru": "от"
  },
  {
    "de": "über",
    "tr": "ˈyːbɐ",
    "ru": "о (тема)"
  },
  {
    "de": "trotz",
    "tr": "tʁɔt͡s",
    "ru": "несмотря на"
  },
  {
    "de": "während",
    "tr": "ˈvɛːʁənt",
    "ru": "во время"
  },
  {
    "de": "entlang",
    "tr": "ˈɛntlaŋ",
    "ru": "вдоль"
  },
  {
    "de": "außer",
    "tr": "ˈaʊ̯sɐ",
    "ru": "кроме"
  },
  {
    "de": "innerhalb",
    "tr": "ˈɪnɐhalp",
    "ru": "внутри"
  },
  {
    "de": "außerhalb",
    "tr": "ˈaʊ̯sɐhalp",
    "ru": "снаружи"
  },
  {
    "de": "oberhalb",
    "tr": "ˈoːbɐhalp",
    "ru": "над"
  },
  {
    "de": "unterhalb",
    "tr": "ˈʊntɐhalp",
    "ru": "под"
  },
  {
    "de": "vorbei",
    "tr": "foːɐ̯ˈbaɪ̯",
    "ru": "мимо"
  },
  {
    "de": "entgegen",
    "tr": "ɛntˈɡeːɡn̩",
    "ru": "навстречу"
  },
  {
    "de": "bis",
    "tr": "bɪs",
    "ru": "до"
  },
  {
    "de": "ab",
    "tr": "ap",
    "ru": "с (начиная с)"
  },
  {
    "de": "laut",
    "tr": "laʊ̯t",
    "ru": "согласно"
  },
  {
    "de": "gemäß",
    "tr": "ɡəˈmɛːs",
    "ru": "в соответствии"
  },
  {
    "de": "dank",
    "tr": "daŋk",
    "ru": "благодаря"
  },
  {
    "de": "inklusive",
    "tr": "ɪŋkluˈziːvə",
    "ru": "включая"
  },
  {
    "de": "anstatt",
    "tr": "anˈʃtat",
    "ru": "вместо"
  },
  {
    "de": "pro",
    "tr": "pʁoː",
    "ru": "в (расчёте на)"
  },
  {
    "de": "je",
    "tr": "jeː",
    "ru": "на каждого"
  },
  {
    "de": "via",
    "tr": "ˈviːa",
    "ru": "через"
  },
  {
    "de": "ohne",
    "tr": "ˈoːnə",
    "ru": "без"
  },
  {
    "de": "mitsamt",
    "tr": "mɪtˈzamt",
    "ru": "вместе с"
  },
  {
    "de": "nahe",
    "tr": "ˈnaːə",
    "ru": "близко к"
  },
  {
    "de": "unweit",
    "tr": "ˈʊnvaɪ̯t",
    "ru": "недалеко от"
  },
  {
    "de": "jenseits",
    "tr": "ˈjeːnzaɪ̯t͡s",
    "ru": "по ту сторону"
  },
  {
    "de": "diesseits",
    "tr": "ˈdiːszaɪ̯t͡s",
    "ru": "по эту сторону"
  },
  {
    "de": "zugunsten",
    "tr": "t͡suˈɡʊnstn̩",
    "ru": "в пользу"
  },
  {
    "de": "rot",
    "tr": "ʁoːt",
    "ru": "красный"
  },
  {
    "de": "blau",
    "tr": "blaʊ̯",
    "ru": "синий"
  },
  {
    "de": "grün",
    "tr": "ɡʁyːn",
    "ru": "зелёный"
  },
  {
    "de": "gelb",
    "tr": "ɡɛlp",
    "ru": "жёлтый"
  },
  {
    "de": "schwarz",
    "tr": "ʃvaʁt͡s",
    "ru": "чёрный"
  },
  {
    "de": "weiß",
    "tr": "vaɪ̯s",
    "ru": "белый"
  },
  {
    "de": "grau",
    "tr": "ɡʁaʊ̯",
    "ru": "серый"
  },
  {
    "de": "braun",
    "tr": "bʁaʊ̯n",
    "ru": "коричневый"
  },
  {
    "de": "orange",
    "tr": "oˈʁãːʒə",
    "ru": "оранжевый"
  },
  {
    "de": "lila",
    "tr": "ˈliːla",
    "ru": "фиолетовый"
  },
  {
    "de": "rosa",
    "tr": "ˈʁoːza",
    "ru": "розовый"
  },
  {
    "de": "beige",
    "tr": "beːʒ",
    "ru": "бежевый"
  },
  {
    "de": "gold",
    "tr": "ɡɔlt",
    "ru": "золотой"
  },
  {
    "de": "silber",
    "tr": "ˈzɪlbɐ",
    "ru": "серебряный"
  },
  {
    "de": "hellblau",
    "tr": "ˈhɛlbl̩aʊ̯",
    "ru": "голубой"
  },
  {
    "de": "dunkelblau",
    "tr": "ˈdʊŋkl̩blaʊ̯",
    "ru": "тёмно-синий"
  },
  {
    "de": "hellgrün",
    "tr": "ˈhɛlɡʁyːn",
    "ru": "светло-зелёный"
  },
  {
    "de": "dunkelgrün",
    "tr": "ˈdʊŋkl̩ɡʁyːn",
    "ru": "тёмно-зелёный"
  },
  {
    "de": "pastell",
    "tr": "paˈstɛl",
    "ru": "пастельный"
  },
  {
    "de": "knallrot",
    "tr": "ˈknaɫˌʁoːt",
    "ru": "ярко-красный"
  },
  {
    "de": "meerblau",
    "tr": "ˈmeːɐ̯blaʊ̯",
    "ru": "морской синий"
  },
  {
    "de": "weinrot",
    "tr": "ˈvaɪ̯nˌʁoːt",
    "ru": "бордовый"
  },
  {
    "de": "khaki",
    "tr": "ˈkaːki",
    "ru": "хаки"
  },
  {
    "de": "türkis",
    "tr": "tʏʁˈkiːs",
    "ru": "бирюзовый"
  },
  {
    "de": "minze",
    "tr": "ˈmɪnt͡sə",
    "ru": "мятный"
  },
  {
    "de": "sandfarben",
    "tr": "ˈzantˌfaʁbn̩",
    "ru": "песочный"
  },
  {
    "de": "elfenbein",
    "tr": "ˈɛlfn̩baɪ̯n",
    "ru": "слоновая кость"
  },
  {
    "de": "koralle",
    "tr": "koˈʁalə",
    "ru": "коралловый"
  },
  {
    "de": "himbeer",
    "tr": "ˈhɪmbaːɐ̯",
    "ru": "малиновый"
  },
  {
    "de": "zimt",
    "tr": "t͡sɪmt",
    "ru": "коричный"
  },
  {
    "de": "taubenblau",
    "tr": "ˈtaʊ̯bn̩blaʊ̯",
    "ru": "сизый"
  },
  {
    "de": "stahlgrau",
    "tr": "ˈʃtaːlɡʁaʊ̯",
    "ru": "стальной"
  },
  {
    "de": "neon",
    "tr": "ˈneːɔn",
    "ru": "неоновый"
  },
  {
    "de": "farbig",
    "tr": "ˈfaʁbɪç",
    "ru": "цветной"
  },
  {
    "de": "farblos",
    "tr": "ˈfaʁbloːs",
    "ru": "бесцветный"
  },
  {
    "de": "kräftig",
    "tr": "ˈkʁɛftɪç",
    "ru": "насыщенный"
  },
  {
    "de": "blass",
    "tr": "blas",
    "ru": "бледный"
  },
  {
    "de": "leuchtend",
    "tr": "ˈlɔɪ̯çtnt",
    "ru": "яркий"
  },
  {
    "de": "dunkel",
    "tr": "ˈdʊŋkl̩",
    "ru": "тёмный"
  },
  {
    "de": "hell",
    "tr": "hɛl",
    "ru": "светлый"
  },
  {
    "de": "matt",
    "tr": "mat",
    "ru": "матовый"
  },
  {
    "de": "glänzend",
    "tr": "ˈɡlɛnt͡snd",
    "ru": "глянцевый"
  },
  {
    "de": "zart",
    "tr": "t͡saʁt",
    "ru": "нежный"
  },
  {
    "de": "kräftig rot",
    "tr": "ˈkʁɛftɪç ʁoːt",
    "ru": "насыщенно-красный"
  },
  {
    "de": "kräftig blau",
    "tr": "ˈkʁɛftɪç blaʊ̯",
    "ru": "насыщенно-синий"
  },
  {
    "de": "tiefschwarz",
    "tr": "ˈtiːfˌʃvaʁt͡s",
    "ru": "глубоко чёрный"
  },
  {
    "de": "eisblaue",
    "tr": "ˈaɪ̯sblaʊ̯ə",
    "ru": "ледяной синий"
  },
  {
    "de": "regenbogenfarben",
    "tr": "ˈʁeːɡn̩ˌboːɡn̩ˌfaʁbn̩",
    "ru": "радужный"
  },
  {
    "de": "glücklich",
    "tr": "ˈɡlʏklɪç",
    "ru": "счастливый"
  },
  {
    "de": "traurig",
    "tr": "ˈtʁaʊ̯ʁɪç",
    "ru": "грустный"
  },
  {
    "de": "wütend",
    "tr": "ˈvyːtn̩t",
    "ru": "злой"
  },
  {
    "de": "ruhig",
    "tr": "ˈʁuːɪç",
    "ru": "спокойный"
  },
  {
    "de": "gestresst",
    "tr": "ɡəˈʃtʁɛst",
    "ru": "в стрессе"
  },
  {
    "de": "gelassen",
    "tr": "ɡəˈlasn̩",
    "ru": "невозмутимый"
  },
  {
    "de": "nervös",
    "tr": "nɛʁˈvøːs",
    "ru": "нервный"
  },
  {
    "de": "überrascht",
    "tr": "ˌyːbɐˈʁaʃt",
    "ru": "удивлённый"
  },
  {
    "de": "erschrocken",
    "tr": "ɛɐ̯ˈʃʁɔkən",
    "ru": "испуганный"
  },
  {
    "de": "ängstlich",
    "tr": "ˈɛŋstlɪç",
    "ru": "тревожный"
  },
  {
    "de": "mutig",
    "tr": "ˈmuːtɪç",
    "ru": "смелый"
  },
  {
    "de": "hoffnungsvoll",
    "tr": "ˈhɔfnʊŋsˌfɔl",
    "ru": "полный надежд"
  },
  {
    "de": "enttäuscht",
    "tr": "ɛnˈtɔʏ̯ʃt",
    "ru": "разочарованный"
  },
  {
    "de": "verliebt",
    "tr": "fɛɐ̯ˈliːpt",
    "ru": "влюблённый"
  },
  {
    "de": "einsam",
    "tr": "ˈaɪ̯nzaːm",
    "ru": "одинокий"
  },
  {
    "de": "neugierig",
    "tr": "ˈnɔʏ̯ˌɡiːʁɪç",
    "ru": "любопытный"
  },
  {
    "de": "erschöpft",
    "tr": "ɛɐ̯ˈʃœpft",
    "ru": "истощённый"
  },
  {
    "de": "begeistert",
    "tr": "bəˈɡaɪ̯stɐt",
    "ru": "в восторге"
  },
  {
    "de": "verwirrt",
    "tr": "fɛɐ̯ˈvɪʁt",
    "ru": "запутанный"
  },
  {
    "de": "stolz",
    "tr": "ʃtɔlt͡s",
    "ru": "гордый"
  },
  {
    "de": "schuldig",
    "tr": "ˈʃʊldɪç",
    "ru": "виноватый"
  },
  {
    "de": "lustig",
    "tr": "ˈlʊstɪç",
    "ru": "весёлый"
  },
  {
    "de": "fröhlich",
    "tr": "ˈfʁøːlɪç",
    "ru": "радостный"
  },
  {
    "de": "gelangweilt",
    "tr": "ɡəˈlaŋvaɪ̯lt",
    "ru": "скучающий"
  },
  {
    "de": "verlegen",
    "tr": "fɛɐ̯ˈleːɡn̩",
    "ru": "смущённый"
  },
  {
    "de": "zufrieden",
    "tr": "t͡suˈfʁiːdn̩",
    "ru": "довольный"
  },
  {
    "de": "besorgt",
    "tr": "bəˈzɔʁkt",
    "ru": "обеспокоенный"
  },
  {
    "de": "genervt",
    "tr": "ɡəˈnɛʁft",
    "ru": "раздражённый"
  },
  {
    "de": "hilflos",
    "tr": "ˈhɪlfl̩oːs",
    "ru": "беспомощный"
  },
  {
    "de": "optimistisch",
    "tr": "ɔptimiˈstɪʃ",
    "ru": "оптимистичный"
  },
  {
    "de": "pessimistisch",
    "tr": "pɛsimiˈstɪʃ",
    "ru": "пессимистичный"
  },
  {
    "de": "friedlich",
    "tr": "ˈfʁiːdlɪç",
    "ru": "мирный"
  },
  {
    "de": "aggressiv",
    "tr": "aɡʁɛˈsiːf",
    "ru": "агрессивный"
  },
  {
    "de": "verzweifelt",
    "tr": "fɛɐ̯ˈt͡svaɪ̯fl̩t",
    "ru": "в отчаянии"
  },
  {
    "de": "ermutigt",
    "tr": "ɛɐ̯ˈmuːtɪɡt",
    "ru": "ободрённый"
  },
  {
    "de": "gelähmt",
    "tr": "ɡəˈlɛːmt",
    "ru": "парализованный"
  },
  {
    "de": "abwesend",
    "tr": "ˈapˌveːzn̩t",
    "ru": "отсутствующий"
  },
  {
    "de": "verärgert",
    "tr": "fɛɐ̯ˈʔɛʁɡɐt",
    "ru": "сердитый"
  },
  {
    "de": "sanft",
    "tr": "zanft",
    "ru": "нежный"
  },
  {
    "de": "empfindlich",
    "tr": "ɛmˈfɪntlɪç",
    "ru": "чувствительный"
  },
  {
    "de": "tapfer",
    "tr": "ˈtapfɐ",
    "ru": "храбрый"
  },
  {
    "de": "eifersüchtig",
    "tr": "ˈaɪ̯fɐˌzʏçtɪç",
    "ru": "ревнивый"
  },
  {
    "de": "panisch",
    "tr": "ˈpaːnɪʃ",
    "ru": "в панике"
  },
  {
    "de": "entspannt",
    "tr": "ɛntˈʃpant",
    "ru": "расслабленный"
  },
  {
    "de": "unruhig",
    "tr": "ˈʊnˌʁuːɪç",
    "ru": "беспокойный"
  },
  {
    "de": "mitfühlend",
    "tr": "ˈmɪtˌfyːlənt",
    "ru": "сочувствующий"
  },
  {
    "de": "gleichgültig",
    "tr": "ˈɡlaɪ̯çˌɡʏltɪç",
    "ru": "безразличный"
  },
  {
    "de": "das Handy",
    "tr": "ˈhɛndi",
    "ru": "телефон"
  },
  {
    "de": "das Smartphone",
    "tr": "ˈsmaːtˌfoːn",
    "ru": "смартфон"
  },
  {
    "de": "der Laptop",
    "tr": "ˈlɛptɔp",
    "ru": "ноутбук"
  },
  {
    "de": "der Computer",
    "tr": "kɔmˈpjuːtɐ",
    "ru": "компьютер"
  },
  {
    "de": "der Fernseher",
    "tr": "ˈfɛʁnˌzeːɐ̯",
    "ru": "телевизор"
  },
  {
    "de": "das Radio",
    "tr": "ˈʁaːdio",
    "ru": "радио"
  },
  {
    "de": "die Kamera",
    "tr": "ˈkaməʁa",
    "ru": "камера"
  },
  {
    "de": "die Uhr",
    "tr": "uːɐ̯",
    "ru": "часы"
  },
  {
    "de": "der Drucker",
    "tr": "ˈdʁʊkɐ",
    "ru": "принтер"
  },
  {
    "de": "die Tastatur",
    "tr": "tastaˈtuːɐ̯",
    "ru": "клавиатура"
  },
  {
    "de": "die Maus",
    "tr": "maʊ̯s",
    "ru": "мышь"
  },
  {
    "de": "das Kabel",
    "tr": "ˈkaːbl̩",
    "ru": "кабель"
  },
  {
    "de": "die Steckdose",
    "tr": "ˈʃtɛkˌdoːzə",
    "ru": "розетка"
  },
  {
    "de": "der Stecker",
    "tr": "ˈʃtɛkɐ",
    "ru": "вилка"
  },
  {
    "de": "die Lampe",
    "tr": "ˈlampə",
    "ru": "лампа"
  },
  {
    "de": "die Batterie",
    "tr": "batəˈʁiː",
    "ru": "батарейка"
  },
  {
    "de": "der Akku",
    "tr": "ˈaku",
    "ru": "аккумулятор"
  },
  {
    "de": "das Ladegerät",
    "tr": "ˈlaːdəɡəˌʁɛːt",
    "ru": "зарядное устройство"
  },
  {
    "de": "die Fernbedienung",
    "tr": "ˈfɛʁn bədiːnʊŋ",
    "ru": "пульт"
  },
  {
    "de": "der Lautsprecher",
    "tr": "ˈlaʊ̯tˌʃpʁɛçɐ",
    "ru": "колонка"
  },
  {
    "de": "die Kopfhörer",
    "tr": "ˈkɔpfˌhøːʁɐ",
    "ru": "наушники"
  },
  {
    "de": "das Mikrofon",
    "tr": "mikʁoˈfoːn",
    "ru": "микрофон"
  },
  {
    "de": "die App",
    "tr": "ɛp",
    "ru": "приложение"
  },
  {
    "de": "das Programm",
    "tr": "pʁoˈɡʁam",
    "ru": "программа"
  },
  {
    "de": "die Datei",
    "tr": "daˈtaɪ̯",
    "ru": "файл"
  },
  {
    "de": "die Taste",
    "tr": "ˈtastə",
    "ru": "кнопка"
  },
  {
    "de": "das Display",
    "tr": "ˈdɪspleː",
    "ru": "экран"
  },
  {
    "de": "der Bildschirm",
    "tr": "ˈbɪlt͡ʃɪʁm",
    "ru": "монитор"
  },
  {
    "de": "der Router",
    "tr": "ˈʁuːtɐ",
    "ru": "роутер"
  },
  {
    "de": "das Internet",
    "tr": "ˈɪntɐnɛt",
    "ru": "интернет"
  },
  {
    "de": "der Strom",
    "tr": "ʃtʁoːm",
    "ru": "электричество"
  },
  {
    "de": "die Maschine",
    "tr": "maˈʃiːnə",
    "ru": "машина (механизм)"
  },
  {
    "de": "die Werkzeug",
    "tr": "ˈvɛʁkˌt͡sɔɪ̯k",
    "ru": "инструмент"
  },
  {
    "de": "die Schere",
    "tr": "ˈʃeːʁə",
    "ru": "ножницы"
  },
  {
    "de": "der Hammer",
    "tr": "ˈhamɐ",
    "ru": "молоток"
  },
  {
    "de": "der Schraubenzieher",
    "tr": "ˈʃʁaʊ̯bn̩ˌt͡siːɐ̯",
    "ru": "отвёртка"
  },
  {
    "de": "die Bohrmaschine",
    "tr": "ˈboːɐ̯maˌʃiːnə",
    "ru": "дрель"
  },
  {
    "de": "die Kette",
    "tr": "ˈkɛtə",
    "ru": "цепь"
  },
  {
    "de": "der Schlüssel",
    "tr": "ˈʃlʏsl̩",
    "ru": "ключ"
  },
  {
    "de": "der Rucksack",
    "tr": "ˈʁʊkˌzak",
    "ru": "рюкзак"
  },
  {
    "de": "die Tasche",
    "tr": "ˈtaʃə",
    "ru": "сумка"
  },
  {
    "de": "die Brieftasche",
    "tr": "ˈbʁiːfˌtaʃə",
    "ru": "бумажник"
  },
  {
    "de": "das Portemonnaie",
    "tr": "pɔʁmɔˈneː",
    "ru": "кошелёк"
  },
  {
    "de": "der Ausweis",
    "tr": "ˈaʊ̯sˌvaɪ̯s",
    "ru": "удостоверение"
  },
  {
    "de": "die Karte",
    "tr": "ˈkaʁtə",
    "ru": "карта"
  },
  {
    "de": "der Stift",
    "tr": "ʃtɪft",
    "ru": "ручка"
  },
  {
    "de": "der Block",
    "tr": "blɔk",
    "ru": "блокнот"
  },
  {
    "de": "das Papier",
    "tr": "paˈpiːɐ̯",
    "ru": "бумага"
  },
  {
    "de": "die Flasche",
    "tr": "ˈflaʃə",
    "ru": "бутылка"
  },
  {
    "de": "die Tasse",
    "tr": "ˈtasə",
    "ru": "чашка"
  }
]
    

    2) Объект с блоками по темам:
       {
         "topics": [
          {
  "topic": "A1: Приветствия и базовые фразы",
  "words": [
    {"de": "Hallo", "tr": "ˈhalo", "ru": "привет"},
    {"de": "Guten Tag", "tr": "ˌɡuːtn̩ ˈtaːk", "ru": "добрый день"},
    {"de": "Guten Morgen", "tr": "ˌɡuːtn̩ ˈmɔʁɡn̩", "ru": "доброе утро"},
    {"de": "Guten Abend", "tr": "ˌɡuːtn̩ ˈaːbn̩t", "ru": "добрый вечер"},
    {"de": "Gute Nacht", "tr": "ˌɡuːtə ˈnaxt", "ru": "спокойной ночи"},
    {"de": "Tschüss", "tr": "tʃʏs", "ru": "пока"},
    {"de": "Auf Wiedersehen", "tr": "aʊ̯f ˈviːdɐzeːən", "ru": "до свидания"},
    {"de": "Bis später", "tr": "bɪs ˈʃpɛːtɐ", "ru": "до позже"},
    {"de": "Bis morgen", "tr": "bɪs ˈmɔʁɡn̩", "ru": "до завтра"},
    {"de": "Willkommen", "tr": "vɪlˈkɔmən", "ru": "добро пожаловать"},
    {"de": "Danke", "tr": "ˈdaŋkə", "ru": "спасибо"},
    {"de": "Vielen Dank", "tr": "ˈfiːlən daŋk", "ru": "большое спасибо"},
    {"de": "Bitte", "tr": "ˈbɪtə", "ru": "пожалуйста"},
    {"de": "Entschuldigung", "tr": "ɛntˈʃʊldɪɡʊŋ", "ru": "извините"},
    {"de": "Es tut mir leid", "tr": "ɛs tuːt miːɐ̯ laɪ̯t", "ru": "мне жаль"},
    {"de": "Ja", "tr": "jaː", "ru": "да"},
    {"de": "Nein", "tr": "naɪ̯n", "ru": "нет"},
    {"de": "Vielleicht", "tr": "fiˈlaɪ̯çt", "ru": "возможно"},
    {"de": "Genau", "tr": "ɡəˈnaʊ̯", "ru": "верно"},
    {"de": "Wirklich", "tr": "ˈvɪʁklɪç", "ru": "действительно"},
    {"de": "Natürlich", "tr": "naˈtyːɐ̯lɪç", "ru": "конечно"},
    {"de": "Klar", "tr": "klaːɐ̯", "ru": "понятно"},
    {"de": "Ich verstehe", "tr": "ɪç fɛɐ̯ˈʃteːə", "ru": "я понимаю"},
    {"de": "Ich weiß", "tr": "ɪç vaɪ̯s", "ru": "я знаю"},
    {"de": "Ich weiß nicht", "tr": "ɪç vaɪ̯s nɪçt", "ru": "я не знаю"},
    {"de": "Wie geht’s?", "tr": "viː ɡeːts", "ru": "как дела?"},
    {"de": "Gut", "tr": "ɡuːt", "ru": "хорошо"},
    {"de": "Sehr gut", "tr": "zeːɐ̯ ɡuːt", "ru": "очень хорошо"},
    {"de": "Nicht so gut", "tr": "nɪçt zoː ɡuːt", "ru": "не очень"},
    {"de": "Schlecht", "tr": "ʃlɛçt", "ru": "плохо"},
    {"de": "Und dir?", "tr": "ʊnt diːɐ̯", "ru": "а у тебя?"},
    {"de": "Und Ihnen?", "tr": "ʊnt ˈiːnən", "ru": "а у вас?"},
    {"de": "Wie bitte?", "tr": "ˈviː ˌbɪtə", "ru": "что, простите?"},
    {"de": "Noch einmal, bitte", "tr": "nɔx ˈaɪ̯nmal ˈbɪtə", "ru": "ещё раз, пожалуйста"},
    {"de": "Kein Problem", "tr": "kaɪ̯n pʁoˈbleːm", "ru": "нет проблем"},
    {"de": "Alles gut", "tr": "ˈaləs ɡuːt", "ru": "всё хорошо"},
    {"de": "Viel Glück", "tr": "fiːl ɡlʏk", "ru": "удачи"},
    {"de": "Gute Besserung", "tr": "ˌɡuːtə ˈbɛsəʁʊŋ", "ru": "выздоравливай"},
    {"de": "Frohe Weihnachten", "tr": "ˌfʁoːə ˈvaɪ̯naxtn̩", "ru": "с Рождеством"},
    {"de": "Guten Rutsch", "tr": "ˌɡuːtn̩ ʁʊtʃ", "ru": "с наступающим"},
    {"de": "Herzlichen Glückwunsch", "tr": "ˈhɛʁtslɪçən ˈɡlʏkvʊnʃ", "ru": "поздравляю"},
    {"de": "Viel Spaß", "tr": "fiːl ʃpaːs", "ru": "веселись"},
    {"de": "Pass auf!", "tr": "pas aʊ̯f", "ru": "осторожно"},
    {"de": "Hilfe!", "tr": "ˈhɪlfə", "ru": "помощь"},
    {"de": "Achtung!", "tr": "axton", "ru": "внимание"}
    ]
},
{
    "topic": "A1: Личные данные и знакомство",
    "words": [
    {"de": "Ich", "tr": "ɪç", "ru": "я"},
    {"de": "Du", "tr": "duː", "ru": "ты"},
    {"de": "Er", "tr": "eːɐ̯", "ru": "он"},
    {"de": "Sie", "tr": "ziː", "ru": "она"},
    {"de": "Es", "tr": "ɛs", "ru": "оно"},
    {"de": "Wir", "tr": "viːɐ̯", "ru": "мы"},
    {"de": "Ihr", "tr": "iːɐ̯", "ru": "вы"},
    {"de": "Sie (plural)", "tr": "ziː", "ru": "они"},
    {"de": "Sie (formal)", "tr": "ziː", "ru": "Вы"},
    {"de": "Name", "tr": "ˈnaːmə", "ru": "имя"},
    {"de": "Vorname", "tr": "ˈfoːɐ̯ˌnaːmə", "ru": "имя (личное)"},
    {"de": "Nachname", "tr": "ˈnaːxˌnaːmə", "ru": "фамилия"},
    {"de": "Alter", "tr": "ˈaltɐ", "ru": "возраст"},
    {"de": "Adresse", "tr": "aˈdʁɛsə", "ru": "адрес"},
    {"de": "Straße", "tr": "ˈʃtʁaːsə", "ru": "улица"},
    {"de": "Hausnummer", "tr": "ˈhaʊ̯sˌnʊmɐ", "ru": "номер дома"},
    {"de": "Wohnort", "tr": "ˈvoːnˌʔɔʁt", "ru": "место проживания"},
    {"de": "Stadt", "tr": "ʃtat", "ru": "город"},
    {"de": "Land", "tr": "lant", "ru": "страна"},
    {"de": "Geburtsdatum", "tr": "ɡəˈbʊʁtsˌdaːtʊm", "ru": "дата рождения"},
    {"de": "Geburtsort", "tr": "ɡəˈbʊʁtsˌʔɔʁt", "ru": "место рождения"},
    {"de": "Telefon", "tr": "ˈteːləfoːn", "ru": "телефон"},
    {"de": "Nummer", "tr": "ˈnʊmɐ", "ru": "номер"},
    {"de": "Beruf", "tr": "bəˈʁuːf", "ru": "профессия"},
    {"de": "Arbeit", "tr": "ˈaʁbaɪ̯t", "ru": "работа"},
    {"de": "Firma", "tr": "ˈfɪʁma", "ru": "фирма"},
    {"de": "Student", "tr": "ʃtuˈdɛnt", "ru": "студент"},
    {"de": "Schüler", "tr": "ˈʃyːlɐ", "ru": "школьник"},
    {"de": "Lehrer", "tr": "ˈleːʁɐ", "ru": "учитель"},
    {"de": "Kollege", "tr": "kɔˈleːɡə", "ru": "коллега"},
    {"de": "Freund", "tr": "fʁɔɪ̯nt", "ru": "друг"},
    {"de": "Freundin", "tr": "ˈfʁɔɪ̯ndɪn", "ru": "подруга"},
    {"de": "Familie", "tr": "faˈmiːli̯ə", "ru": "семья"},
    {"de": "Vater", "tr": "ˈfaːtɐ", "ru": "отец"},
    {"de": "Mutter", "tr": "ˈmʊtɐ", "ru": "мать"},
    {"de": "Bruder", "tr": "ˈbʁuːdɐ", "ru": "брат"},
    {"de": "Schwester", "tr": "ˈʃvɛstɐ", "ru": "сестра"},
    {"de": "Ehemann", "tr": "ˈeːəˌman", "ru": "муж"},
    {"de": "Ehefrau", "tr": "ˈeːəˌfʁaʊ̯", "ru": "жена"},
    {"de": "Kind", "tr": "kɪnt", "ru": "ребенок"},
    {"de": "Sohn", "tr": "zoːn", "ru": "сын"},
    {"de": "Tochter", "tr": "ˈtɔxtɐ", "ru": "дочь"},
    {"de": "Hobby", "tr": "ˈhɔbi", "ru": "хобби"},
    {"de": "Interesse", "tr": "ɪntəˈʁɛsə", "ru": "интерес"},
    {"de": "Sprache", "tr": "ˈʃpʁaːxə", "ru": "язык"},
    {"de": "Deutsch", "tr": "dɔɪ̯tʃ", "ru": "немецкий"},
    {"de": "Englisch", "tr": "ˈɛŋlɪʃ", "ru": "английский"},
    {"de": "wohne", "tr": "ˈvoːnə", "ru": "живу"}
  ]
},
{
  "topic": "A1: Люди и внешность",
  "words": [
    {"de": "Person", "tr": "pɛʁˈzoːn", "ru": "человек"},
    {"de": "Mann", "tr": "man", "ru": "мужчина"},
    {"de": "Frau", "tr": "fʁaʊ̯", "ru": "женщина"},
    {"de": "Junge", "tr": "ˈjʊŋə", "ru": "мальчик"},
    {"de": "Mädchen", "tr": "ˈmɛːtçən", "ru": "девочка"},
    {"de": "Leute", "tr": "ˈlɔɪ̯tə", "ru": "люди"},
    {"de": "Körper", "tr": "ˈkœʁpɐ", "ru": "тело"},
    {"de": "Kopf", "tr": "kɔpf", "ru": "голова"},
    {"de": "Gesicht", "tr": "ɡəˈzɪçt", "ru": "лицо"},
    {"de": "Auge", "tr": "ˈaʊ̯ɡə", "ru": "глаз"},
    {"de": "Ohren", "tr": "ˈoːʁən", "ru": "уши"},
    {"de": "Nase", "tr": "ˈnaːzə", "ru": "нос"},
    {"de": "Mund", "tr": "mʊnt", "ru": "рот"},
    {"de": "Haare", "tr": "ˈhaːʁə", "ru": "волосы"},
    {"de": "Hals", "tr": "hals", "ru": "шея"},
    {"de": "Schulter", "tr": "ˈʃʊltɐ", "ru": "плечо"},
    {"de": "Arm", "tr": "aʁm", "ru": "рука"},
    {"de": "Hand", "tr": "hant", "ru": "кисть руки"},
    {"de": "Finger", "tr": "ˈfɪŋɐ", "ru": "палец"},
    {"de": "Brust", "tr": "bʁʊst", "ru": "грудь"},
    {"de": "Bauch", "tr": "baʊ̯x", "ru": "живот"},
    {"de": "Rücken", "tr": "ˈʁʏkn̩", "ru": "спина"},
    {"de": "Bein", "tr": "baɪ̯n", "ru": "нога"},
    {"de": "Fuß", "tr": "fuːs", "ru": "ступня"},
    {"de": "Größe", "tr": "ˈɡʁøːsə", "ru": "рост"},
    {"de": "Gewicht", "tr": "ɡəˈvɪçt", "ru": "вес"},
    {"de": "groß", "tr": "ɡʁoːs", "ru": "высокий"},
    {"de": "klein", "tr": "klaɪ̯n", "ru": "низкий"},
    {"de": "dick", "tr": "dɪk", "ru": "полный"},
    {"de": "dünn", "tr": "dʏn", "ru": "худой"},
    {"de": "alt", "tr": "alt", "ru": "старый"},
    {"de": "jung", "tr": "jʊŋ", "ru": "молодой"},
    {"de": "schön", "tr": "ʃøːn", "ru": "красивый"},
    {"de": "hässlich", "tr": "ˈhɛslɪç", "ru": "некрасивый"},
    {"de": "stark", "tr": "ʃtaʁk", "ru": "сильный"},
    {"de": "schwach", "tr": "ʃvax", "ru": "слабый"},
    {"de": "müde", "tr": "ˈmyːdə", "ru": "усталый"},
    {"de": "krank", "tr": "kʁaŋk", "ru": "больной"},
    {"de": "gesund", "tr": "ɡəˈzʊnt", "ru": "здоровый"},
    {"de": "glücklich", "tr": "ˈɡlʏklɪç", "ru": "счастливый"},
    {"de": "traurig", "tr": "ˈtʁaʊ̯ʁɪç", "ru": "грустный"},
    {"de": "freundlich", "tr": "ˈfʁɔɪ̯ntlɪç", "ru": "дружелюбный"},
    {"de": "nett", "tr": "nɛt", "ru": "милый"},
    {"de": "ernst", "tr": "ɛʁnst", "ru": "серьёзный"},
    {"de": "laut", "tr": "laʊ̯t", "ru": "громкий"},
    {"de": "leise", "tr": "ˈlaɪ̯zə", "ru": "тихий"},
    {"de": "langsam", "tr": "ˈlaŋzaːm", "ru": "медленный"},
    {"de": "schnell", "tr": "ʃnɛl", "ru": "быстрый"},
    {"de": "neu", "tr": "nɔɪ̯", "ru": "новый"},
    {"de": "alt (Sache)", "tr": "alt", "ru": "старый (предмет)"},
    {"de": "heiß", "tr": "haɪ̯s", "ru": "горячий"},
    {"de": "kalt", "tr": "kalt", "ru": "холодный"}
  ]
},
{
  "topic": "A1: Семья",
  "words": [
    {"de": "die Familie", "tr": "diː faˈmiːli̯ə", "ru": "семья"},
    {"de": "der Vater", "tr": "ˈfaːtɐ", "ru": "отец"},
    {"de": "die Mutter", "tr": "ˈmʊtɐ", "ru": "мать"},
    {"de": "die Eltern", "tr": "ˈɛltɐn", "ru": "родители"},
    {"de": "der Sohn", "tr": "zoːn", "ru": "сын"},
    {"de": "die Tochter", "tr": "ˈtɔxtɐ", "ru": "дочь"},
    {"de": "der Bruder", "tr": "ˈbʁuːdɐ", "ru": "брат"},
    {"de": "die Schwester", "tr": "ˈʃvɛstɐ", "ru": "сестра"},
    {"de": "der Onkel", "tr": "ˈɔŋkl̩", "ru": "дядя"},
    {"de": "die Tante", "tr": "ˈtantə", "ru": "тётя"},
    {"de": "der Cousin", "tr": "kuˈzɛ̃ː", "ru": "кузен"},
    {"de": "die Cousine", "tr": "kuˈziːnə", "ru": "кузина"},
    {"de": "die Großeltern", "tr": "ˈɡʁoːsˌʔɛltɐn", "ru": "бабушка и дедушка"},
    {"de": "die Großmutter", "tr": "ˈɡʁoːsˌmʊtɐ", "ru": "бабушка"},
    {"de": "der Großvater", "tr": "ˈɡʁoːsˌfaːtɐ", "ru": "дедушка"},
    {"de": "das Kind", "tr": "kɪnt", "ru": "ребёнок"},
    {"de": "die Kinder", "tr": "ˈkɪndɐ", "ru": "дети"},
    {"de": "die Geschwister", "tr": "ɡəˈʃvɪstɐ", "ru": "братья и сёстры"},
    {"de": "der Neffe", "tr": "ˈnɛfə", "ru": "племянник"},
    {"de": "die Nichte", "tr": "ˈnɪçtə", "ru": "племянница"},
    {"de": "die Schwiegereltern", "tr": "ˈʃviːɡɐˌʔɛltɐn", "ru": "свёкры"},
    {"de": "die Schwiegermutter", "tr": "ˈʃviːɡɐˌmʊtɐ", "ru": "свекровь / тёща"},
    {"de": "der Schwiegervater", "tr": "ˈʃviːɡɐˌfaːtɐ", "ru": "свёкор / тесть"},
    {"de": "verheiratet", "tr": "fɛɐ̯ˈhaɪ̯ʁatət", "ru": "женат / замужем"},
    {"de": "ledig", "tr": "ˈleːdɪç", "ru": "холост / не замужем"},
    {"de": "geschieden", "tr": "ɡəˈʃiːdn̩", "ru": "разведён"},
    {"de": "verlobt", "tr": "fɛɐ̯ˈloːpt", "ru": "помолвлен"},
    {"de": "die Beziehung", "tr": "bəˈt͡siːʊŋ", "ru": "отношения"},
    {"de": "der Partner", "tr": "ˈpaʁtnɐ", "ru": "партнёр"},
    {"de": "die Partnerin", "tr": "ˈpaʁtnəʁɪn", "ru": "партнёрша"},
    {"de": "die Ehe", "tr": "ˈeːə", "ru": "брак"},
    {"de": "der Ehemann", "tr": "ˈeːəˌman", "ru": "муж"},
    {"de": "die Ehefrau", "tr": "ˈeːəˌfʁaʊ̯", "ru": "жена"},
    {"de": "die Hochzeit", "tr": "ˈhɔxˌt͡saɪ̯t", "ru": "свадьба"},
    {"de": "die Scheidung", "tr": "ˈʃaɪ̯dʊŋ", "ru": "развод"},
    {"de": "die Liebe", "tr": "ˈliːbə", "ru": "любовь"},
    {"de": "der Streit", "tr": "ʃtʁaɪ̯t", "ru": "ссора"},
    {"de": "die Unterstützung", "tr": "ʊntɐˈʃtʏt͡sʊŋ", "ru": "поддержка"},
    {"de": "die Tradition", "tr": "tʁadiˈt͡si̯oːn", "ru": "традиция"},
    {"de": "die Generation", "tr": "ɡenəʁaˈt͡si̯oːn", "ru": "поколение"},
    {"de": "zusammen", "tr": "t͡suˈzamən", "ru": "вместе"},
    {"de": "allein", "tr": "aˈlaɪ̯n", "ru": "один"},
    {"de": "verwandt", "tr": "fɛɐ̯ˈvant", "ru": "родственник"},
    {"de": "sich kümmern", "tr": "zɪç ˈkʏmɐʁn", "ru": "заботиться"},
    {"de": "sich treffen", "tr": "zɪç ˈtʁɛfn̩", "ru": "встречаться"},
    {"de": "besuchen", "tr": "bəˈzuːxn̩", "ru": "навещать"},
    {"de": "wohnen", "tr": "ˈvoːnən", "ru": "жить"},
    {"de": "leben", "tr": "ˈleːbn̩", "ru": "жить (существовать)"}
  ]
},
{
  "topic": "A1: Дом",
  "words": [
    {"de": "das Haus", "tr": "das haʊ̯s", "ru": "дом"},
    {"de": "die Wohnung", "tr": "ˈvoːnʊŋ", "ru": "квартира"},
    {"de": "das Zimmer", "tr": "ˈt͡sɪmɐ", "ru": "комната"},
    {"de": "das Wohnzimmer", "tr": "ˈvoːnˌt͡sɪmɐ", "ru": "гостиная"},
    {"de": "das Schlafzimmer", "tr": "ˈʃlaːfˌt͡sɪmɐ", "ru": "спальня"},
    {"de": "die Küche", "tr": "ˈkʏçə", "ru": "кухня"},
    {"de": "das Badezimmer", "tr": "ˈbaːdəˌt͡sɪmɐ", "ru": "ванная"},
    {"de": "die Toilette", "tr": "to̯aˈlɛtə", "ru": "туалет"},
    {"de": "der Flur", "tr": "fluːɐ̯", "ru": "коридор"},
    {"de": "der Balkon", "tr": "balˈkoːn", "ru": "балкон"},
    {"de": "der Garten", "tr": "ˈɡaʁtn̩", "ru": "сад"},
    {"de": "die Garage", "tr": "ɡaˈʁaːʒə", "ru": "гараж"},
    {"de": "das Fenster", "tr": "ˈfɛnstɐ", "ru": "окно"},
    {"de": "die Tür", "tr": "tyːɐ̯", "ru": "дверь"},
    {"de": "die Wand", "tr": "vant", "ru": "стена"},
    {"de": "der Boden", "tr": "ˈboːdn̩", "ru": "пол"},
    {"de": "die Decke", "tr": "ˈdɛkə", "ru": "потолок"},
    {"de": "das Bett", "tr": "bɛt", "ru": "кровать"},
    {"de": "der Tisch", "tr": "tɪʃ", "ru": "стол"},
    {"de": "der Stuhl", "tr": "ʃtuːl", "ru": "стул"},
    {"de": "das Sofa", "tr": "ˈzoːfa", "ru": "диван"},
    {"de": "der Schrank", "tr": "ʃʁaŋk", "ru": "шкаф"},
    {"de": "das Regal", "tr": "ʁeˈɡaːl", "ru": "полка"},
    {"de": "der Teppich", "tr": "ˈtɛpɪç", "ru": "ковёр"},
    {"de": "die Lampe", "tr": "ˈlampə", "ru": "лампа"},
    {"de": "die Heizung", "tr": "ˈhaɪ̯t͡sʊŋ", "ru": "отопление"},
    {"de": "der Kühlschrank", "tr": "ˈkyːlʃʁaŋk", "ru": "холодильник"},
    {"de": "der Herd", "tr": "heːɐ̯t", "ru": "плита"},
    {"de": "die Spüle", "tr": "ˈʃpyːlə", "ru": "раковина"},
    {"de": "die Dusche", "tr": "ˈduːʃə", "ru": "душ"},
    {"de": "die Badewanne", "tr": "ˈbaːdəˌvanə", "ru": "ванна"},
    {"de": "die Waschmaschine", "tr": "ˈvaʃmaˌʃiːnə", "ru": "стиральная машина"},
    {"de": "der Staubsauger", "tr": "ˈʃtaʊ̯pˌzaʊ̯ɡɐ", "ru": "пылесос"},
    {"de": "der Schlüssel", "tr": "ˈʃlʏsl̩", "ru": "ключ"},
    {"de": "die Miete", "tr": "ˈmiːtə", "ru": "аренда"},
    {"de": "der Vermieter", "tr": "fɛɐ̯ˈmiːtɐ", "ru": "арендодатель"},
    {"de": "der Mieter", "tr": "ˈmiːtɐ", "ru": "арендатор"},
    {"de": "die Nachbarn", "tr": "ˈnaxbaʁn̩", "ru": "соседи"},
    {"de": "das Gebäude", "tr": "ɡəˈbɔʏ̯də", "ru": "здание"},
    {"de": "der Eingang", "tr": "ˈaɪ̯nˌɡaŋ", "ru": "вход"},
    {"de": "der Ausgang", "tr": "ˈaʊ̯sˌɡaŋ", "ru": "выход"},
    {"de": "der Aufzug", "tr": "ˈaʊ̯fˌt͡suːk", "ru": "лифт"},
    {"de": "die Treppe", "tr": "ˈtʁɛpə", "ru": "лестница"},
    {"de": "die Klingel", "tr": "ˈklɪŋl̩", "ru": "звонок"},
    {"de": "der Mietvertrag", "tr": "ˈmiːtˌfɛɐ̯ˌtʁaːk", "ru": "договор аренды"},
    {"de": "die Anzeige", "tr": "ˈant͡saɪ̯ɡə", "ru": "объявление"},
    {"de": "das Möbel", "tr": "ˈmøːbl̩", "ru": "мебель"},
    {"de": "einziehen", "tr": "ˈaɪ̯nˌt͡siːən", "ru": "въезжать"},
    {"de": "ausziehen", "tr": "ˈaʊ̯sˌt͡siːən", "ru": "съезжать"}
  ]
},
{
  "topic": "A1: Еда и продукты",
  "words": [
    {"de": "das Essen", "tr": "das ˈɛsn̩", "ru": "еда"},
    {"de": "das Getränk", "tr": "ɡəˈtʁɛŋk", "ru": "напиток"},
    {"de": "das Wasser", "tr": "ˈvasɐ", "ru": "вода"},
    {"de": "der Saft", "tr": "zaft", "ru": "сок"},
    {"de": "die Milch", "tr": "mɪlç", "ru": "молоко"},
    {"de": "der Kaffee", "tr": "ˈkafeː", "ru": "кофе"},
    {"de": "der Tee", "tr": "teː", "ru": "чай"},
    {"de": "die Suppe", "tr": "ˈzʊpə", "ru": "суп"},
    {"de": "das Brot", "tr": "broːt", "ru": "хлеб"},
    {"de": "die Brötchen", "tr": "ˈbʁøːtçən", "ru": "булочки"},
    {"de": "die Butter", "tr": "ˈbʊtɐ", "ru": "масло"},
    {"de": "der Käse", "tr": "ˈkɛːzə", "ru": "сыр"},
    {"de": "das Fleisch", "tr": "flaɪ̯ʃ", "ru": "мясо"},
    {"de": "das Hähnchen", "tr": "ˈhɛːnçən", "ru": "курица"},
    {"de": "der Fisch", "tr": "fɪʃ", "ru": "рыба"},
    {"de": "die Wurst", "tr": "vʊʁst", "ru": "колбаса"},
    {"de": "das Ei", "tr": "aɪ̯", "ru": "яйцо"},
    {"de": "der Reis", "tr": "ʁaɪ̯s", "ru": "рис"},
    {"de": "die Nudeln", "tr": "ˈnuːdl̩n", "ru": "макароны"},
    {"de": "das Gemüse", "tr": "ɡəˈmyːzə", "ru": "овощи"},
    {"de": "das Obst", "tr": "oːpst", "ru": "фрукты"},
    {"de": "der Apfel", "tr": "ˈapfl̩", "ru": "яблоко"},
    {"de": "die Banane", "tr": "baˈnaːnə", "ru": "банан"},
    {"de": "die Orange", "tr": "oˈʁãːʒə", "ru": "апельсин"},
    {"de": "die Trauben", "tr": "ˈtʁaʊ̯bn̩", "ru": "виноград"},
    {"de": "die Kartoffel", "tr": "kaʁˈtɔfl̩", "ru": "картофель"},
    {"de": "die Tomate", "tr": "toˈmaːtə", "ru": "помидор"},
    {"de": "die Gurke", "tr": "ˈɡʊʁkə", "ru": "огурец"},
    {"de": "die Zwiebel", "tr": "ˈt͡sviːbl̩", "ru": "лук"},
    {"de": "die Karotte", "tr": "kaˈʁɔtə", "ru": "морковь"},
    {"de": "der Salat", "tr": "zaˈlaːt", "ru": "салат"},
    {"de": "die Pizza", "tr": "ˈpɪt͡sa", "ru": "пицца"},
    {"de": "der Hamburger", "tr": "ˈhambʊʁɡɐ", "ru": "гамбургер"},
    {"de": "die Pommes", "tr": "ˈpɔmə", "ru": "картофель фри"},
    {"de": "der Zucker", "tr": "ˈt͡sʊkɐ", "ru": "сахар"},
    {"de": "das Salz", "tr": "zalt͡s", "ru": "соль"},
    {"de": "der Pfeffer", "tr": "ˈpfɛfɐ", "ru": "перец"},
    {"de": "das Öl", "tr": "øːl", "ru": "масло (растительное)"},
    {"de": "der Honig", "tr": "ˈhoːnɪç", "ru": "мёд"},
    {"de": "die Schokolade", "tr": "ʃokoˈlaːdə", "ru": "шоколад"},
    {"de": "der Kuchen", "tr": "ˈkuːxn̩", "ru": "пирог, торт"},
    {"de": "das Eis", "tr": "aɪ̯s", "ru": "мороженое"},
    {"de": "frisch", "tr": "fʁɪʃ", "ru": "свежий"},
    {"de": "kalt", "tr": "kalt", "ru": "холодный"},
    {"de": "heiß", "tr": "haɪ̯s", "ru": "горячий"},
    {"de": "süß", "tr": "zyːs", "ru": "сладкий"},
    {"de": "salzig", "tr": "ˈzaltsɪç", "ru": "солёный"},
    {"de": "bitter", "tr": "ˈbɪtɐ", "ru": "горький"},
    {"de": "scharf", "tr": "ʃaʁf", "ru": "острый"},
    {"de": "lecker", "tr": "ˈlɛkɐ", "ru": "вкусный"}
  ]
},
{
  "topic": "A1: Время и дни недели",
  "words": [
    {"de": "die Zeit", "tr": "t͡saɪ̯t", "ru": "время"},
    {"de": "die Uhr", "tr": "uːɐ̯", "ru": "часы"},
    {"de": "die Uhrzeit", "tr": "ˈuːɐ̯ˌt͡saɪ̯t", "ru": "время (на часах)"},
    {"de": "die Stunde", "tr": "ˈʃtʊndə", "ru": "час"},
    {"de": "die Minute", "tr": "miˈnuːtə", "ru": "минута"},
    {"de": "die Sekunde", "tr": "zeˈkʊndə", "ru": "секунда"},
    {"de": "der Morgen", "tr": "ˈmɔʁɡn̩", "ru": "утро"},
    {"de": "der Vormittag", "tr": "ˈfoːɐ̯mɪtaːk", "ru": "до полудня"},
    {"de": "der Mittag", "tr": "ˈmɪtaːk", "ru": "полдень"},
    {"de": "der Nachmittag", "tr": "ˈnaːxmɪtaːk", "ru": "после обеда"},
    {"de": "der Abend", "tr": "ˈaːbn̩t", "ru": "вечер"},
    {"de": "die Nacht", "tr": "naxt", "ru": "ночь"},
    {"de": "Montag", "tr": "ˈmoːntaːk", "ru": "понедельник"},
    {"de": "Dienstag", "tr": "ˈdiːnstaːk", "ru": "вторник"},
    {"de": "Mittwoch", "tr": "ˈmɪtvɔx", "ru": "среда"},
    {"de": "Donnerstag", "tr": "ˈdɔnɐstaːk", "ru": "четверг"},
    {"de": "Freitag", "tr": "ˈfʁaɪ̯taːk", "ru": "пятница"},
    {"de": "Samstag", "tr": "ˈzamstaːk", "ru": "суббота"},
    {"de": "Sonntag", "tr": "ˈzɔnˌtaːk", "ru": "воскресенье"},
    {"de": "heute", "tr": "ˈhɔɪ̯tə", "ru": "сегодня"},
    {"de": "gestern", "tr": "ˈɡɛstɐn", "ru": "вчера"},
    {"de": "morgen", "tr": "ˈmɔʁɡn̩", "ru": "завтра"},
    {"de": "jetzt", "tr": "jɛt͡st", "ru": "сейчас"},
    {"de": "später", "tr": "ˈʃpɛːtɐ", "ru": "позже"},
    {"de": "früh", "tr": "fʁyː", "ru": "рано"},
    {"de": "zu spät", "tr": "t͡suː ʃpɛːt", "ru": "слишком поздно"},
    {"de": "pünktlich", "tr": "ˈpʏŋktlɪç", "ru": "пунктуальный"},
    {"de": "der Kalender", "tr": "kaˈlɛndɐ", "ru": "календарь"},
    {"de": "der Termin", "tr": "tɛʁˈmiːn", "ru": "встреча, запись"},
    {"de": "die Woche", "tr": "ˈvɔxə", "ru": "неделя"},
    {"de": "das Wochenende", "tr": "ˈvɔxənˌʔɛndə", "ru": "выходные"},
    {"de": "der Monat", "tr": "ˈmoːnaːt", "ru": "месяц"},
    {"de": "das Jahr", "tr": "jaːɐ̯", "ru": "год"},
    {"de": "die Jahreszeit", "tr": "ˈjaːʁəst͡saɪ̯t", "ru": "время года"},
    {"de": "immer", "tr": "ˈɪmɐ", "ru": "всегда"},
    {"de": "nie", "tr": "niː", "ru": "никогда"},
    {"de": "manchmal", "tr": "ˈmançmaːl", "ru": "иногда"},
    {"de": "oft", "tr": "ɔft", "ru": "часто"},
    {"de": "selten", "tr": "ˈzɛltn̩", "ru": "редко"},
    {"de": "morgens", "tr": "ˈmɔʁɡn̩s", "ru": "по утрам"},
    {"de": "mittags", "tr": "ˈmɪtaːks", "ru": "в полдень"},
    {"de": "abends", "tr": "ˈaːbn̩ts", "ru": "по вечерам"},
    {"de": "nachts", "tr": "naxts", "ru": "по ночам"},
    {"de": "bald", "tr": "balt", "ru": "скоро"},
    {"de": "vorher", "tr": "ˈfoːɐ̯heːɐ̯", "ru": "до этого"},
    {"de": "nachher", "tr": "ˈnaːxheːɐ̯", "ru": "после этого"},
    {"de": "rechtzeitig", "tr": "ˈʁɛçtˌt͡saɪ̯tɪç", "ru": "своевременно"},
    {"de": "der Wecker", "tr": "ˈvɛkɐ", "ru": "будильник"},
    {"de": "der Zeitplan", "tr": "ˈt͡saɪ̯tˌplaːn", "ru": "расписание"},
    {"de": "die Pause", "tr": "ˈpaʊ̯zə", "ru": "перерыв"}
  ]
},
{
  "topic": "A1: Город и транспорт",
  "words": [
    {"de": "die Stadt", "tr": "ʃtat", "ru": "город"},
    {"de": "das Dorf", "tr": "dɔʁf", "ru": "деревня"},
    {"de": "das Zentrum", "tr": "ˈt͡sɛntʁʊm", "ru": "центр"},
    {"de": "der Stadtrand", "tr": "ˈʃtatˌʁant", "ru": "окраина"},
    {"de": "die Straße", "tr": "ˈʃtʁaːsə", "ru": "улица"},
    {"de": "der Platz", "tr": "plat͡s", "ru": "площадь"},
    {"de": "die Kreuzung", "tr": "ˈkʁɔʏ̯t͡sʊŋ", "ru": "перекресток"},
    {"de": "die Ampel", "tr": "ˈampəl", "ru": "светофор"},
    {"de": "der Bahnhof", "tr": "ˈbaːnhoːf", "ru": "вокзал"},
    {"de": "die Haltestelle", "tr": "ˈhaltəˌʃtɛlə", "ru": "остановка"},
    {"de": "die Station", "tr": "ʃtaˈt͡si̯oːn", "ru": "станция"},
    {"de": "der Bus", "tr": "bʊs", "ru": "автобус"},
    {"de": "die U-Bahn", "tr": "ˈuːˌbaːn", "ru": "метро"},
    {"de": "die S-Bahn", "tr": "ˈɛsˌbaːn", "ru": "городская электричка"},
    {"de": "das Taxi", "tr": "ˈtaksi", "ru": "такси"},
    {"de": "das Auto", "tr": "ˈaʊ̯to", "ru": "машина"},
    {"de": "der Zug", "tr": "t͡suːk", "ru": "поезд"},
    {"de": "das Fahrrad", "tr": "ˈfaːʁaːt", "ru": "велосипед"},
    {"de": "der Fahrer", "tr": "ˈfaːʁɐ", "ru": "водитель"},
    {"de": "fahren", "tr": "ˈfaːʁən", "ru": "ехать"},
    {"de": "gehen", "tr": "ˈɡeːən", "ru": "идти"},
    {"de": "zu Fuß", "tr": "t͡suː fuːs", "ru": "пешком"},
    {"de": "links", "tr": "lɪŋks", "ru": "налево"},
    {"de": "rechts", "tr": "ʁɛçts", "ru": "направо"},
    {"de": "geradeaus", "tr": "ɡəˈʁaːdəˌaʊ̯s", "ru": "прямо"},
    {"de": "abbiegen", "tr": "ˈapˌbiːɡn̩", "ru": "поворачивать"},
    {"de": "der Weg", "tr": "veːk", "ru": "путь"},
    {"de": "weit", "tr": "vaɪ̯t", "ru": "далеко"},
    {"de": "nah", "tr": "naː", "ru": "близко"},
    {"de": "die Apotheke", "tr": "apoˈteːkə", "ru": "аптека"},
    {"de": "der Supermarkt", "tr": "ˈzuːpɐˌmaʁkt", "ru": "супермаркет"},
    {"de": "das Geschäft", "tr": "ɡəˈʃɛft", "ru": "магазин"},
    {"de": "die Bank", "tr": "baŋk", "ru": "банк"},
    {"de": "die Post", "tr": "pɔst", "ru": "почта"},
    {"de": "das Rathaus", "tr": "ˈʁaːtˌhaʊ̯s", "ru": "ратуша"},
    {"de": "die Polizei", "tr": "poliˈt͡saɪ̯", "ru": "полиция"},
    {"de": "das Krankenhaus", "tr": "ˈkʁaŋkn̩ˌhaʊ̯s", "ru": "больница"},
    {"de": "die Schule", "tr": "ˈʃuːlə", "ru": "школа"},
    {"de": "die Bibliothek", "tr": "biblioˈteːk", "ru": "библиотека"},
    {"de": "der Park", "tr": "paʁk", "ru": "парк"},
    {"de": "der Spielplatz", "tr": "ˈʃpiːlˌplat͡s", "ru": "детская площадка"},
    {"de": "das Restaurant", "tr": "ʁɛstoˈʁãː", "ru": "ресторан"},
    {"de": "die Bäckerei", "tr": "bɛkəˈʁaɪ̯", "ru": "пекарня"},
    {"de": "die Tankstelle", "tr": "ˈtaŋkˌʃtɛlə", "ru": "заправка"},
    {"de": "suchen", "tr": "ˈzuːxn̩", "ru": "искать"},
    {"de": "finden", "tr": "ˈfɪndn̩", "ru": "находить"},
    {"de": "verlieren", "tr": "fɛɐ̯ˈliːʁən", "ru": "терять"},
    {"de": "besuchen", "tr": "bəˈzuːxn̩", "ru": "посещать"},
    {"de": "besichtigen", "tr": "bəˈzɪçtɪɡən", "ru": "осматривать"},
    {"de": "die Richtung", "tr": "ˈʁɪçtʊŋ", "ru": "направление"}
  ]
},
{
  "topic": "A1: Учеба и школа",
  "words": [
    {"de": "die Schule", "tr": "ˈʃuːlə", "ru": "школа"},
    {"de": "die Klasse", "tr": "ˈklasə", "ru": "класс"},
    {"de": "das Klassenzimmer", "tr": "ˈklasn̩ˌt͡sɪmɐ", "ru": "классная комната"},
    {"de": "der Lehrer", "tr": "ˈleːʁɐ", "ru": "учитель"},
    {"de": "die Lehrerin", "tr": "ˈleːʁəʁɪn", "ru": "учительница"},
    {"de": "der Schüler", "tr": "ˈʃyːlɐ", "ru": "школьник"},
    {"de": "die Schülerin", "tr": "ˈʃyːləʁɪn", "ru": "школьница"},
    {"de": "das Fach", "tr": "fax", "ru": "предмет"},
    {"de": "der Unterricht", "tr": "ˈʊntɐʁɪçt", "ru": "урок"},
    {"de": "lernen", "tr": "ˈlɛʁnən", "ru": "учить"},
    {"de": "studieren", "tr": "ʃtuˈdiːʁən", "ru": "изучать"},
    {"de": "lesen", "tr": "ˈleːzn̩", "ru": "читать"},
    {"de": "schreiben", "tr": "ˈʃʁaɪ̯bn̩", "ru": "писать"},
    {"de": "rechnen", "tr": "ˈʁɛçnən", "ru": "считать"},
    {"de": "die Aufgabe", "tr": "ˈaʊ̯fˌɡaːbə", "ru": "задание"},
    {"de": "die Hausaufgabe", "tr": "ˈhaʊ̯sʔaʊ̯fˌɡaːbə", "ru": "домашнее задание"},
    {"de": "die Prüfung", "tr": "ˈpʁyːfʊŋ", "ru": "экзамен"},
    {"de": "der Test", "tr": "tɛst", "ru": "тест"},
    {"de": "die Note", "tr": "ˈnoːtə", "ru": "оценка"},
    {"de": "die Frage", "tr": "ˈfʁaːɡə", "ru": "вопрос"},
    {"de": "die Antwort", "tr": "ˈantvɔʁt", "ru": "ответ"},
    {"de": "verstehen", "tr": "fɛɐ̯ˈʃteːən", "ru": "понимать"},
    {"de": "wiederholen", "tr": "viːdɐˈhoːlən", "ru": "повторять"},
    {"de": "die Pause", "tr": "ˈpaʊ̯zə", "ru": "перемена"},
    {"de": "der Schulhof", "tr": "ˈʃuːlhoːf", "ru": "школьный двор"},
    {"de": "das Buch", "tr": "buːx", "ru": "книга"},
    {"de": "das Heft", "tr": "hɛft", "ru": "тетрадь"},
    {"de": "der Bleistift", "tr": "ˈblaɪ̯ˌʃtɪft", "ru": "карандаш"},
    {"de": "der Kugelschreiber", "tr": "ˈkuːɡl̩ˌʃʁaɪ̯bɐ", "ru": "ручка"},
    {"de": "das Papier", "tr": "paˈpiːɐ̯", "ru": "бумага"},
    {"de": "die Tafel", "tr": "ˈtaːfl̩", "ru": "доска"},
    {"de": "der Radiergummi", "tr": "ʁaˈdiːɐ̯ˌɡʊmi", "ru": "ластик"},
    {"de": "das Lineal", "tr": "lɪniˈaːl", "ru": "линейка"},
    {"de": "der Rucksack", "tr": "ˈʁʊkˌzak", "ru": "рюкзак"},
    {"de": "die Schultasche", "tr": "ˈʃuːlˌtaʃə", "ru": "школьная сумка"},
    {"de": "der Computer", "tr": "kɔmˈpjuːtɐ", "ru": "компьютер"},
    {"de": "das Internet", "tr": "ˈɪntɐnɛt", "ru": "интернет"},
    {"de": "die Bibliothek", "tr": "biblioˈteːk", "ru": "библиотека"},
    {"de": "die Universität", "tr": "univeʁziˈtɛːt", "ru": "университет"},
    {"de": "der Student", "tr": "ʃtuˈdɛnt", "ru": "студент"},
    {"de": "die Studentin", "tr": "ʃtuˈdɛntɪn", "ru": "студентка"},
    {"de": "prüfen", "tr": "ˈpʁyːfən", "ru": "проверять"},
    {"de": "erklären", "tr": "ɛɐ̯ˈklɛːʁən", "ru": "объяснять"},
    {"de": "aufpassen", "tr": "ˈaʊ̯fˌpasn̩", "ru": "быть внимательным"},
    {"de": "beginnen", "tr": "bəˈɡɪnən", "ru": "начинать"},
    {"de": "enden", "tr": "ˈɛndn̩", "ru": "заканчивать"},
    {"de": "prüfungsfrei", "tr": "ˈpʁyːfʊŋsˌfʁaɪ̯", "ru": "без экзаменов"},
    {"de": "der Stundenplan", "tr": "ˈʃtʊndn̩ˌplaːn", "ru": "расписание"},
    {"de": "die Bildung", "tr": "ˈbɪldʊŋ", "ru": "образование"}
  ]
},
{
  "topic": "A1: Покупки и магазины",
  "words": [
    {"de": "kaufen", "tr": "ˈkaʊ̯fn̩", "ru": "покупать"},
    {"de": "verkaufen", "tr": "fɛɐ̯ˈkaʊ̯fn̩", "ru": "продавать"},
    {"de": "der Laden", "tr": "ˈlaːdn̩", "ru": "магазин"},
    {"de": "das Geschäft", "tr": "ɡəˈʃɛft", "ru": "магазин"},
    {"de": "der Supermarkt", "tr": "ˈzuːpɐˌmaʁkt", "ru": "супермаркет"},
    {"de": "das Einkaufszentrum", "tr": "ˈaɪ̯nkaʊ̯fsˌt͡sɛntʁʊm", "ru": "торговый центр"},
    {"de": "die Bäckerei", "tr": "bɛkəˈʁaɪ̯", "ru": "пекарня"},
    {"de": "die Metzgerei", "tr": "mɛt͡sɡəˈʁaɪ̯", "ru": "мясная лавка"},
    {"de": "die Apotheke", "tr": "apoˈteːkə", "ru": "аптека"},
    {"de": "die Kasse", "tr": "ˈkasə", "ru": "касса"},
    {"de": "die Schlange", "tr": "ˈʃlaŋə", "ru": "очередь"},
    {"de": "der Einkauf", "tr": "ˈaɪ̯nˌkaʊ̯f", "ru": "покупка"},
    {"de": "einkaufen", "tr": "ˈaɪ̯nˌkaʊ̯fn̩", "ru": "делать покупки"},
    {"de": "das Angebot", "tr": "ˈanɡəˌboːt", "ru": "предложение, акция"},
    {"de": "der Preis", "tr": "pʁaɪ̯s", "ru": "цена"},
    {"de": "billig", "tr": "ˈbɪlɪç", "ru": "дешевый"},
    {"de": "teuer", "tr": "ˈtɔɪ̯ɐ", "ru": "дорогой"},
    {"de": "die Rechnung", "tr": "ˈʁɛçnʊŋ", "ru": "счет"},
    {"de": "bezahlen", "tr": "bəˈt͡saːlən", "ru": "платить"},
    {"de": "bar bezahlen", "tr": "baːɐ̯ bəˈt͡saːlən", "ru": "платить наличными"},
    {"de": "mit Karte zahlen", "tr": "mɪt ˈkaʁtə ˈt͡saːlən", "ru": "платить картой"},
    {"de": "die Kreditkarte", "tr": "kʁeˈdiːtˌkaʁtə", "ru": "кредитная карта"},
    {"de": "der Verkäufer", "tr": "fɛɐ̯ˈkɔɪ̯fɐ", "ru": "продавец"},
    {"de": "die Verkäuferin", "tr": "fɛɐ̯ˈkɔɪ̯fʁɪn", "ru": "продавщица"},
    {"de": "die Tüte", "tr": "ˈtyːtə", "ru": "пакет"},
    {"de": "die Tasche", "tr": "ˈtaʃə", "ru": "сумка"},
    {"de": "probieren", "tr": "pʁoˈbiːʁən", "ru": "пробовать"},
    {"de": "anprobieren", "tr": "ˈanpʁoˌbiːʁən", "ru": "примерять"},
    {"de": "passen", "tr": "ˈpasn̩", "ru": "подходить"},
    {"de": "zurückgeben", "tr": "t͡suˈʁʏkˌɡeːbn̩", "ru": "возвращать"},
    {"de": "suchen", "tr": "ˈzuːxn̩", "ru": "искать"},
    {"de": "finden", "tr": "ˈfɪndn̩", "ru": "находить"},
    {"de": "brauchen", "tr": "ˈbʁaʊ̯xn̩", "ru": "нуждаться"},
    {"de": "die Größe", "tr": "ˈɡʁøːsə", "ru": "размер"},
    {"de": "die Farbe", "tr": "ˈfaʁbə", "ru": "цвет"},
    {"de": "die Ware", "tr": "ˈvaːʁə", "ru": "товар"},
    {"de": "die Qualität", "tr": "kvaliˈtɛːt", "ru": "качество"},
    {"de": "die Quittung", "tr": "ˈkvɪtʊŋ", "ru": "чек"},
    {"de": "reduziert", "tr": "ʁeduˈt͡siːɐ̯t", "ru": "со скидкой"},
    {"de": "im Angebot sein", "tr": "ɪm ˈanɡəˌboːt zaɪ̯n", "ru": "быть по акции"},
    {"de": "öffnen", "tr": "ˈœfnən", "ru": "открывать"},
    {"de": "schließen", "tr": "ˈʃliːsən", "ru": "закрывать"},
    {"de": "geöffnet", "tr": "ɡəˈœfnət", "ru": "открыто"},
    {"de": "geschlossen", "tr": "ɡəˈʃlɔsn̩", "ru": "закрыто"},
    {"de": "die Öffnungszeiten", "tr": "ˈœfnʊŋsˌt͡saɪ̯tn̩", "ru": "часы работы"},
    {"de": "das Sonderangebot", "tr": "ˈzɔndɐˌanɡəˌboːt", "ru": "специальное предложение"},
    {"de": "der Prospekt", "tr": "pʁoˈspɛkt", "ru": "рекламная листовка"},
    {"de": "der Kunde", "tr": "ˈkʊndə", "ru": "клиент"},
    {"de": "die Kundin", "tr": "ˈkʊndɪn", "ru": "клиентка"}
  ]
},
{
  "topic": "A1: Здоровье и самочувствие",
  "words": [
    {"de": "gesund", "tr": "ɡəˈzʊnt", "ru": "здоровый"},
    {"de": "die Gesundheit", "tr": "ɡəˈzʊndhaɪ̯t", "ru": "здоровье"},
    {"de": "krank", "tr": "kʁaŋk", "ru": "больной"},
    {"de": "die Krankheit", "tr": "ˈkʁaŋkhaɪ̯t", "ru": "болезнь"},
    {"de": "das Fieber", "tr": "ˈfiːbɐ", "ru": "жар"},
    {"de": "die Erkältung", "tr": "ɛɐ̯ˈkɛltʊŋ", "ru": "простуда"},
    {"de": "der Husten", "tr": "ˈhuːstn̩", "ru": "кашель"},
    {"de": "der Schnupfen", "tr": "ˈʃnʊpfn̩", "ru": "насморк"},
    {"de": "die Kopfschmerzen", "tr": "ˈkɔp͡fʃmɛʁt͡sn̩", "ru": "головная боль"},
    {"de": "die Bauchschmerzen", "tr": "ˈbaʊ̯xʃmɛʁt͡sn̩", "ru": "боль в животе"},
    {"de": "die Tablette", "tr": "taˈblɛtə", "ru": "таблетка"},
    {"de": "die Medizin", "tr": "mediˈt͡siːn", "ru": "лекарство"},
    {"de": "das Rezept", "tr": "ʁeˈt͡sɛpt", "ru": "рецепт"},
    {"de": "der Arzt", "tr": "aʁt͡st", "ru": "врач"},
    {"de": "die Ärztin", "tr": "ˈɛːʁt͡stin", "ru": "врач (женщина)"},
    {"de": "die Apotheke", "tr": "apoˈteːkə", "ru": "аптека"},
    {"de": "der Termin", "tr": "tɛʁˈmiːn", "ru": "запись к врачу"},
    {"de": "die Untersuchung", "tr": "ʊntɐˈzuːxʊŋ", "ru": "обследование"},
    {"de": "die Verletzung", "tr": "fɛɐ̯ˈlɛt͡sʊŋ", "ru": "травма"},
    {"de": "die Wunde", "tr": "ˈvʊndə", "ru": "рана"},
    {"de": "das Blut", "tr": "bluːt", "ru": "кровь"},
    {"de": "der Notfall", "tr": "ˈnoːtˌfal", "ru": "чрезвычайный случай"},
    {"de": "die Hilfe", "tr": "ˈhɪlfə", "ru": "помощь"},
    {"de": "helfen", "tr": "ˈhɛlfn̩", "ru": "помогать"},
    {"de": "retten", "tr": "ˈʁɛtn̩", "ru": "спасать"},
    {"de": "weh tun", "tr": "veː tuːn", "ru": "болеть (о части тела)"},
    {"de": "sich verletzen", "tr": "zɪç fɛɐ̯ˈlɛt͡sn̩", "ru": "пораниться"},
    {"de": "müde", "tr": "ˈmyːdə", "ru": "усталый"},
    {"de": "schwach", "tr": "ʃvax", "ru": "слабый"},
    {"de": "fit", "tr": "fɪt", "ru": "в форме"},
    {"de": "sich ausruhen", "tr": "zɪç ˈaʊ̯sˌʁuːən", "ru": "отдыхать"},
    {"de": "schlafen", "tr": "ˈʃlaːfn̩", "ru": "спать"},
    {"de": "gut schlafen", "tr": "ɡuːt ˈʃlaːfn̩", "ru": "хорошо спать"},
    {"de": "schlecht schlafen", "tr": "ʃlɛçt ˈʃlaːfn̩", "ru": "плохо спать"},
    {"de": "sich fühlen", "tr": "zɪç ˈfyːlən", "ru": "чувствовать себя"},
    {"de": "hungrig", "tr": "ˈhʊŋʁɪç", "ru": "голодный"},
    {"de": "durstig", "tr": "ˈdʊʁstɪç", "ru": "испытывающий жажду"},
    {"de": "trinken", "tr": "ˈtʁɪŋkn̩", "ru": "пить"},
    {"de": "viel Wasser trinken", "tr": "fiːl ˈvasɐ ˈtʁɪŋkn̩", "ru": "пить много воды"},
    {"de": "gesund essen", "tr": "ɡəˈzʊnt ˈɛsn̩", "ru": "питаться правильно"},
    {"de": "die Diät", "tr": "diˈʔɛːt", "ru": "диета"},
    {"de": "Sport machen", "tr": "ʃpɔʁt ˈmaxn̩", "ru": "заниматься спортом"},
    {"de": "die Übung", "tr": "ˈyːbʊŋ", "ru": "упражнение"},
    {"de": "der Schmerz", "tr": "ʃmɛʁt͡s", "ru": "боль"},
    {"de": "schlimm", "tr": "ʃlɪm", "ru": "тяжелый, плохой"},
    {"de": "leicht", "tr": "laɪ̯çt", "ru": "легкий"},
    {"de": "die Praxis", "tr": "ˈpʁaksɪs", "ru": "поликлиника, кабинет"},
    {"de": "das Krankenhaus", "tr": "ˈkʁaŋkn̩ˌhaʊ̯s", "ru": "больница"},
    {"de": "der Patient", "tr": "paˈt͡si̯ɛnt", "ru": "пациент"},
    {"de": "die Patientin", "tr": "paˈt͡si̯ɛntɪn", "ru": "пациентка"}
  ]
},
{
  "topic": "A1: Работа и профессии",
  "words": [
    {"de": "der Beruf", "tr": "bəˈʁuːf", "ru": "профессия"},
    {"de": "arbeiten", "tr": "ˈaʁbaɪ̯tn̩", "ru": "работать"},
    {"de": "die Arbeit", "tr": "ˈaʁbaɪ̯t", "ru": "работа"},
    {"de": "der Chef", "tr": "ʃɛf", "ru": "шеф"},
    {"de": "die Chefin", "tr": "ˈʃɛfɪn", "ru": "шефиnя"},
    {"de": "die Firma", "tr": "ˈfɪʁma", "ru": "компания"},
    {"de": "das Büro", "tr": "byˈʁoː", "ru": "офис"},
    {"de": "die Fabrik", "tr": "faˈbʁɪk", "ru": "завод"},
    {"de": "der Kollege", "tr": "koˈleːɡə", "ru": "коллега"},
    {"de": "die Kollegin", "tr": "koˈleːɡɪn", "ru": "коллега (женщина)"},
    {"de": "der Kunde", "tr": "ˈkʊndə", "ru": "клиент"},
    {"de": "die Kundin", "tr": "ˈkʊndɪn", "ru": "клиентка"},
    {"de": "der Verkäufer", "tr": "fɛɐ̯ˈkɔɪ̯fɐ", "ru": "продавец"},
    {"de": "der Lehrer", "tr": "ˈleːʁɐ", "ru": "учитель"},
    {"de": "der Fahrer", "tr": "ˈfaːʁɐ", "ru": "водитель"},
    {"de": "der Arzt", "tr": "aʁt͡st", "ru": "врач"},
    {"de": "der Koch", "tr": "kɔx", "ru": "повар"},
    {"de": "der Kellner", "tr": "ˈkɛl.nɐ", "ru": "официант"},
    {"de": "die Kellnerin", "tr": "ˈkɛl.nəʁɪn", "ru": "официантка"},
    {"de": "der Mechaniker", "tr": "meˈçaːnɪkɐ", "ru": "механик"},
    {"de": "der Ingenieur", "tr": "ɪnʒeˈnøːɐ̯", "ru": "инженер"},
    {"de": "die Stelle", "tr": "ˈʃtɛlə", "ru": "место работы"},
    {"de": "die Bewerbung", "tr": "bəˈvɛʁbʊŋ", "ru": "заявление на работу"},
    {"de": "der Vertrag", "tr": "fɛɐ̯ˈtʁaːk", "ru": "контракт"},
    {"de": "kündigen", "tr": "ˈkʏndɪɡən", "ru": "увольняться"},
    {"de": "der Lohn", "tr": "loːn", "ru": "зарплата"},
    {"de": "das Gehalt", "tr": "ɡəˈhalt", "ru": "оклад"},
    {"de": "verdienen", "tr": "fɛɐ̯ˈdiːnən", "ru": "зарабатывать"},
    {"de": "das Team", "tr": "tiːm", "ru": "команда"},
    {"de": "der Kollege", "tr": "koˈleːɡə", "ru": "коллега"},
    {"de": "zusammenarbeiten", "tr": "t͡suˈzamənˌaʁbaɪ̯tn̩", "ru": "работать вместе"},
    {"de": "die Pause", "tr": "ˈpaʊ̯zə", "ru": "перерыв"},
    {"de": "die Arbeitszeit", "tr": "ˈaʁbaɪ̯t͡sˌt͡saɪ̯t", "ru": "рабочее время"},
    {"de": "Vollzeit", "tr": "ˈfɔlt͡saɪ̯t", "ru": "полный рабочий день"},
    {"de": "Teilzeit", "tr": "ˈtaɪ̯lt͡saɪ̯t", "ru": "неполная занятость"},
    {"de": "das Praktikum", "tr": "ˈpʁaktikʊm", "ru": "практика"},
    {"de": "der Berufserfahrung", "tr": "bəˈʁuːfsʔɛɐ̯ˌfaːʁʊŋ", "ru": "профессиональный опыт"},
    {"de": "der Service", "tr": "ˈzœʁvɪs", "ru": "сервис"},
    {"de": "anrufen", "tr": "ˈanˌʁuːfn̩", "ru": "звонить"},
    {"de": "das Meeting", "tr": "ˈmiːtɪŋ", "ru": "встреча, митинг"},
    {"de": "der Termin", "tr": "tɛʁˈmiːn", "ru": "встреча"},
    {"de": "pünktlich sein", "tr": "ˈpʏŋktlɪç zaɪ̯n", "ru": "быть пунктуальным"},
    {"de": "die Verantwortung", "tr": "fɛɐ̯ˈantvɔʁtʊŋ", "ru": "ответственность"},
    {"de": "die Aufgabe", "tr": "ˈaʊ̯fˌɡaːbə", "ru": "задача"},
    {"de": "anstrengend", "tr": "ˈanʃtʁɛŋənt", "ru": "напряженный"},
    {"de": "einfach", "tr": "ˈaɪ̯nfax", "ru": "легкий"},
    {"de": "schwer", "tr": "ʃveːɐ̯", "ru": "трудный"},
    {"de": "der Kollege", "tr": "koˈleːɡə", "ru": "коллега"},
    {"de": "die Karriere", "tr": "kaˈʁiːʁə", "ru": "карьера"},
    {"de": "der Arbeitsplatz", "tr": "ˈaʁbaɪ̯t͡sˌplat͡s", "ru": "рабочее место"},
    {"de": "arbeitslos", "tr": "ˈaʁbaɪ̯t͡sˌloːs", "ru": "безработный"}
  ]
},
{
  "topic": "A1: Хобби и свободное время",
  "words": [
    {"de": "das Hobby", "tr": "ˈhɔbi", "ru": "хобби"},
    {"de": "die Freizeit", "tr": "ˈfʁaɪ̯t͡saɪ̯t", "ru": "свободное время"},
    {"de": "spielen", "tr": "ˈʃpiːlən", "ru": "играть"},
    {"de": "Fußball spielen", "tr": "ˈfuːsbal ˈʃpiːlən", "ru": "играть в футбол"},
    {"de": "Tennis spielen", "tr": "ˈtɛnɪs ˈʃpiːlən", "ru": "играть в теннис"},
    {"de": "schwimmen", "tr": "ˈʃvɪmən", "ru": "плавать"},
    {"de": "laufen", "tr": "ˈlaʊ̯fn̩", "ru": "бегать"},
    {"de": "wandern", "tr": "ˈvandɐn", "ru": "ходить в поход"},
    {"de": "Rad fahren", "tr": "ʁaːt ˈfaːʁən", "ru": "ездить на велосипеде"},
    {"de": "trainieren", "tr": "tʁaˈniːʁən", "ru": "тренироваться"},
    {"de": "ins Fitnessstudio gehen", "tr": "ɪns ˈfɪtnɛsˌʃtuːdio ˈɡeːən", "ru": "ходить в зал"},
    {"de": "lesen", "tr": "ˈleːzn̩", "ru": "читать"},
    {"de": "ein Buch lesen", "tr": "aɪ̯n buːx ˈleːzn̩", "ru": "читать книгу"},
    {"de": "schreiben", "tr": "ˈʃʁaɪ̯bn̩", "ru": "писать"},
    {"de": "zeichnen", "tr": "ˈt͡saɪ̯çnən", "ru": "рисовать (карандашом)"},
    {"de": "malen", "tr": "ˈmaːlən", "ru": "рисовать (красками)"},
    {"de": "fotografieren", "tr": "fotoɡʁaˈfiːʁən", "ru": "фотографировать"},
    {"de": "tanzen", "tr": "ˈtant͡sn̩", "ru": "танцевать"},
    {"de": "singen", "tr": "ˈzɪŋən", "ru": "петь"},
    {"de": "Musik hören", "tr": "muˈziːk ˈhøːʁən", "ru": "слушать музыку"},
    {"de": "fernsehen", "tr": "ˈfɛʁnˌzeːən", "ru": "смотреть телевизор"},
    {"de": "eine Serie schauen", "tr": "ˈeːnə ˈzeːʁi̯ə ˈʃaʊ̯ən", "ru": "смотреть сериал"},
    {"de": "ins Kino gehen", "tr": "ɪns ˈkiːno ˈɡeːən", "ru": "ходить в кино"},
    {"de": "ins Theater gehen", "tr": "ɪns teˈaːtɐ ˈɡeːən", "ru": "ходить в театр"},
    {"de": "kochen", "tr": "ˈkɔxn̩", "ru": "готовить"},
    {"de": "backen", "tr": "ˈbakn̩", "ru": "печь"},
    {"de": "Computerspiele spielen", "tr": "kɔmˈpjuːtɐˌʃpiːlə ˈʃpiːlən", "ru": "играть в компьютерные игры"},
    {"de": "Videospiele spielen", "tr": "ˈviːde.oˌʃpiːlə ˈʃpiːlən", "ru": "играть в видеоигры"},
    {"de": "reisen", "tr": "ˈʁaɪ̯zn̩", "ru": "путешествовать"},
    {"de": "Freunde treffen", "tr": "ˈfʁɔɪ̯ndə ˈtʁɛfn̩", "ru": "встречаться с друзьями"},
    {"de": "ausgehen", "tr": "ˈaʊ̯sˌɡeːən", "ru": "выходить в свет"},
    {"de": "spazieren gehen", "tr": "ʃpaˈt͡siːʁən ˈɡeːən", "ru": "гулять"},
    {"de": "Entspannung", "tr": "ɛntˈʃpanʊŋ", "ru": "расслабление"},
    {"de": "sich entspannen", "tr": "zɪç ɛntˈʃpanən", "ru": "расслабляться"},
    {"de": "die Freizeit genießen", "tr": "ˈfʁaɪ̯t͡saɪ̯t ɡəˈniːsən", "ru": "наслаждаться свободным временем"},
    {"de": "Gitarre spielen", "tr": "ɡiˈtaʁə ˈʃpiːlən", "ru": "играть на гитаре"},
    {"de": "ein Instrument spielen", "tr": "aɪ̯n ɪnstruˈmɛnt ˈʃpiːlən", "ru": "играть на инструменте"},
    {"de": "sammeln", "tr": "ˈzaməln̩", "ru": "коллекционировать"},
    {"de": "Brettspiele", "tr": "ˈbʁɛtˌʃpiːlə", "ru": "настольные игры"},
    {"de": "die Karte", "tr": "ˈkaʁtə", "ru": "карта, карточка"},
    {"de": "der Ausflug", "tr": "ˈaʊ̯sˌfluːk", "ru": "поездка, вылазка"},
    {"de": "joggen", "tr": "ˈd͡ʒɔɡn̩", "ru": "бегать трусцой"},
    {"de": "Yoga machen", "tr": "ˈjoːɡa ˈmaxn̩", "ru": "заниматься йогой"},
    {"de": "entspannende Musik", "tr": "ɛntˈʃpanəndə muˈziːk", "ru": "расслабляющая музыка"},
    {"de": "sich ausruhen", "tr": "zɪç ˈaʊ̯sˌʁuːən", "ru": "отдыхать"},
    {"de": "faulenzen", "tr": "ˈfaʊ̯lɛnt͡sən", "ru": "лениться, бездельничать"},
    {"de": "Zeit mit der Familie", "tr": "t͡saɪ̯t mɪt deːɐ̯ faˈmiːli̯ə", "ru": "время с семьей"},
    {"de": "Zeit mit Freunden", "tr": "t͡saɪ̯t mɪt ˈfʁɔɪ̯ndn̩", "ru": "время с друзьями"},
    {"de": "das Interesse", "tr": "ɪntəˈʁɛsə", "ru": "интерес"},
    {"de": "sich interessieren für", "tr": "zɪç ɪntəʁɛˈsiːʁən fyːɐ̯", "ru": "интересоваться чем-то"}
  ]
},
{
  "topic": "A1: Погода и природа",
  "words": [
    {"de": "das Wetter", "tr": "ˈvɛtɐ", "ru": "погода"},
    {"de": "die Sonne", "tr": "ˈzɔnə", "ru": "солнце"},
    {"de": "sonnig", "tr": "ˈzɔnɪç", "ru": "солнечно"},
    {"de": "der Regen", "tr": "ˈʁeːɡn̩", "ru": "дождь"},
    {"de": "regnen", "tr": "ˈʁeːɡnən", "ru": "идет дождь"},
    {"de": "der Schnee", "tr": "ʃneː", "ru": "снег"},
    {"de": "schneien", "tr": "ˈʃnaɪ̯ən", "ru": "идет снег"},
    {"de": "bewölkt", "tr": "bəˈvœlkt", "ru": "пасмурно"},
    {"de": "der Wind", "tr": "vɪnt", "ru": "ветер"},
    {"de": "windig", "tr": "ˈvɪndɪç", "ru": "ветрено"},
    {"de": "der Sturm", "tr": "ʃtʊʁm", "ru": "буря"},
    {"de": "warm", "tr": "vaʁm", "ru": "теплый"},
    {"de": "kalt", "tr": "kalt", "ru": "холодный"},
    {"de": "heiß", "tr": "haɪ̯s", "ru": "жаркий"},
    {"de": "die Temperatur", "tr": "tɛmpɛʁaˈtuːɐ̯", "ru": "температура"},
    {"de": "das Klima", "tr": "ˈkliːma", "ru": "климат"},
    {"de": "die Jahreszeit", "tr": "ˈjaːʁəst͡saɪ̯t", "ru": "время года"},
    {"de": "der Frühling", "tr": "ˈfʁyːlɪŋ", "ru": "весна"},
    {"de": "der Sommer", "tr": "ˈzɔmɐ", "ru": "лето"},
    {"de": "der Herbst", "tr": "hɛʁpst", "ru": "осень"},
    {"de": "der Winter", "tr": "ˈvɪntɐ", "ru": "зима"},
    {"de": "die Natur", "tr": "naˈtuːɐ̯", "ru": "природа"},
    {"de": "der Baum", "tr": "baʊ̯m", "ru": "дерево"},
    {"de": "die Blume", "tr": "ˈbluːmə", "ru": "цветок"},
    {"de": "die Pflanze", "tr": "ˈpflant͡sə", "ru": "растение"},
    {"de": "das Gras", "tr": "ɡʁaːs", "ru": "трава"},
    {"de": "der Wald", "tr": "valt", "ru": "лес"},
    {"de": "der See", "tr": "zeː", "ru": "озеро"},
    {"de": "der Fluss", "tr": "flʊs", "ru": "река"},
    {"de": "das Meer", "tr": "meːɐ̯", "ru": "море"},
    {"de": "der Strand", "tr": "ʃtʁant", "ru": "пляж"},
    {"de": "der Berg", "tr": "bɛʁk", "ru": "гора"},
    {"de": "das Tal", "tr": "taːl", "ru": "долина"},
    {"de": "der Himmel", "tr": "ˈhɪml̩", "ru": "небо"},
    {"de": "die Wolke", "tr": "ˈvɔlkə", "ru": "облако"},
    {"de": "der Stern", "tr": "ʃtɛʁn", "ru": "звезда"},
    {"de": "der Mond", "tr": "moːnt", "ru": "луна"},
    {"de": "klarer Himmel", "tr": "ˈklaːʁɐ ˈhɪml̩", "ru": "чистое небо"},
    {"de": "stark regnen", "tr": "ʃtaʁk ˈʁeːɡnən", "ru": "идет сильный дождь"},
    {"de": "leicht regnen", "tr": "laɪ̯çt ˈʁeːɡnən", "ru": "моросит"},
    {"de": "das Gewitter", "tr": "ɡəˈvɪtɐ", "ru": "гроза"},
    {"de": "die Luft", "tr": "lʊft", "ru": "воздух"},
    {"de": "die frische Luft", "tr": "ˈfʁɪʃə lʊft", "ru": "свежий воздух"},
    {"de": "draußen", "tr": "ˈdʁaʊ̯sn̩", "ru": "на улице"},
    {"de": "drinnen", "tr": "ˈdʁɪnən", "ru": "внутри"},
    {"de": "spazieren gehen", "tr": "ʃpaˈt͡siːʁən ˈɡeːən", "ru": "гулять"},
    {"de": "die Jahreszeiten wechseln", "tr": "ˈjaːʁəst͡saɪ̯tn̩ ˈvɛxsl̩n̩", "ru": "смена времен года"},
    {"de": "das Klima ist mild", "tr": "ˈkliːma ɪst mɪlt", "ru": "климат мягкий"},
    {"de": "es ist warm", "tr": "ɛs ɪst vaʁm", "ru": "тепло"},
    {"de": "es ist kalt", "tr": "ɛs ɪst kalt", "ru": "холодно"}
  ]
},
{
  "topic": "A1: Животные",
  "words": [
    {"de": "das Tier", "tr": "tiːɐ̯", "ru": "животное"},
    {"de": "der Hund", "tr": "hʊnt", "ru": "собака"},
    {"de": "die Katze", "tr": "ˈkat͡sə", "ru": "кошка"},
    {"de": "der Vogel", "tr": "ˈfoːɡl̩", "ru": "птица"},
    {"de": "der Fisch", "tr": "fɪʃ", "ru": "рыба"},
    {"de": "das Pferd", "tr": "pfeːʁt", "ru": "лошадь"},
    {"de": "die Maus", "tr": "maʊ̯s", "ru": "мышь"},
    {"de": "die Kuh", "tr": "kuː", "ru": "корова"},
    {"de": "das Schwein", "tr": "ʃvaɪ̯n", "ru": "свинья"},
    {"de": "das Schaf", "tr": "ʃaːf", "ru": "овца"},
    {"de": "die Ziege", "tr": "ˈt͡siːɡə", "ru": "коза"},
    {"de": "das Huhn", "tr": "huːn", "ru": "курица"},
    {"de": "die Ente", "tr": "ˈɛntə", "ru": "утка"},
    {"de": "die Gans", "tr": "ɡans", "ru": "гусь"},
    {"de": "der Hahn", "tr": "haːn", "ru": "петух"},
    {"de": "der Hase", "tr": "ˈhaːzə", "ru": "заяц"},
    {"de": "das Kaninchen", "tr": "kaˈniːnçən", "ru": "кролик"},
    {"de": "die Schildkröte", "tr": "ˈʃɪltˌkʁøːtə", "ru": "черепаха"},
    {"de": "der Löwe", "tr": "ˈløːvə", "ru": "лев"},
    {"de": "der Tiger", "tr": "ˈtiːɡɐ", "ru": "тигр"},
    {"de": "der Elefant", "tr": "eleˈfant", "ru": "слон"},
    {"de": "der Bär", "tr": "bɛːɐ̯", "ru": "медведь"},
    {"de": "der Wolf", "tr": "vɔlf", "ru": "волк"},
    {"de": "der Fuchs", "tr": "fʊks", "ru": "лиса"},
    {"de": "der Affe", "tr": "ˈafə", "ru": "обезьяна"},
    {"de": "das Kamel", "tr": "kaˈmeːl", "ru": "верблюд"},
    {"de": "das Krokodil", "tr": "kʁokoˈdiːl", "ru": "крокодил"},
    {"de": "die Schlange", "tr": "ˈʃlaŋə", "ru": "змея"},
    {"de": "die Spinne", "tr": "ˈʃpɪnə", "ru": "паук"},
    {"de": "die Biene", "tr": "ˈbiːnə", "ru": "пчела"},
    {"de": "die Fliege", "tr": "ˈfliːɡə", "ru": "муха"},
    {"de": "die Ameise", "tr": "ˈaːˌmaɪ̯zə", "ru": "муравей"},
    {"de": "der Frosch", "tr": "fʁɔʃ", "ru": "лягушка"},
    {"de": "der Pinguin", "tr": "ˈpɪŋɡu.iːn", "ru": "пингвин"},
    {"de": "das Tierheim", "tr": "ˈtiːɐ̯ˌhaɪ̯m", "ru": "приют для животных"},
    {"de": "der Tierarzt", "tr": "ˈtiːɐ̯ˌaʁt͡st", "ru": "ветеринар"},
    {"de": "streicheln", "tr": "ˈʃtʁaɪ̯çln̩", "ru": "гладить"},
    {"de": "füttern", "tr": "ˈfʏtɐn", "ru": "кормить"},
    {"de": "die Leine", "tr": "ˈlaɪ̯nə", "ru": "поводок"},
    {"de": "das Haustier", "tr": "ˈhaʊ̯sˌtiːɐ̯", "ru": "домашнее животное"},
    {"de": "wild", "tr": "vɪlt", "ru": "дикий"},
    {"de": "zahm", "tr": "tsaːm", "ru": "ручной"},
    {"de": "das Fell", "tr": "fɛl", "ru": "шерсть"},
    {"de": "die Pfote", "tr": "ˈpfoːtə", "ru": "лапа"},
    {"de": "der Schwanz", "tr": "ʃvant͡s", "ru": "хвост"},
    {"de": "das Horn", "tr": "hɔʁn", "ru": "рог"},
    {"de": "bellen", "tr": "ˈbɛln̩", "ru": "лаять"},
    {"de": "miauen", "tr": "miˈaʊ̯ən", "ru": "мяукать"},
    {"de": "das Küken", "tr": "ˈkyːkn̩", "ru": "цыпленок"},
    {"de": "das Futter", "tr": "ˈfʊtɐ", "ru": "корм"}
  ],
{
  "topic": "A1: Быт и дом",
  "words": [
    {"de": "das Haus", "tr": "haʊ̯s", "ru": "дом"},
    {"de": "die Wohnung", "tr": "ˈvoːnʊŋ", "ru": "квартира"},
    {"de": "der Raum", "tr": "ʁaʊ̯m", "ru": "комната"},
    {"de": "das Zimmer", "tr": "ˈt͡sɪmɐ", "ru": "комната"},
    {"de": "das Wohnzimmer", "tr": "ˈvoːnˌt͡sɪmɐ", "ru": "гостиная"},
    {"de": "das Schlafzimmer", "tr": "ˈʃlaːfˌt͡sɪmɐ", "ru": "спальня"},
    {"de": "die Küche", "tr": "ˈkʏçə", "ru": "кухня"},
    {"de": "das Bad", "tr": "baːt", "ru": "ванная"},
    {"de": "der Flur", "tr": "fluːɐ̯", "ru": "коридор"},
    {"de": "der Balkon", "tr": "balˈkoːn", "ru": "балкон"},
    {"de": "der Garten", "tr": "ˈɡaʁtn̩", "ru": "сад"},
    {"de": "die Möbel", "tr": "ˈmøːbl̩", "ru": "мебель"},
    {"de": "der Tisch", "tr": "tɪʃ", "ru": "стол"},
    {"de": "der Stuhl", "tr": "ʃtuːl", "ru": "стул"},
    {"de": "das Bett", "tr": "bɛt", "ru": "кровать"},
    {"de": "der Schrank", "tr": "ʃʁaŋk", "ru": "шкаф"},
    {"de": "das Sofa", "tr": "ˈzoːfa", "ru": "диван"},
    {"de": "der Teppich", "tr": "ˈtɛpɪç", "ru": "ковёр"},
    {"de": "die Lampe", "tr": "ˈlampə", "ru": "лампа"},
    {"de": "der Spiegel", "tr": "ˈʃpiːɡl̩", "ru": "зеркало"},
    {"de": "der Fernseher", "tr": "ˈfɛʁnˌzeːɐ̯", "ru": "телевизор"},
    {"de": "die Waschmaschine", "tr": "ˈvaʃmaˌʃiːnə", "ru": "стиральная машина"},
    {"de": "der Kühlschrank", "tr": "ˈkyːlˌʃʁaŋk", "ru": "холодильник"},
    {"de": "der Herd", "tr": "heːɐ̯t", "ru": "плита"},
    {"de": "der Ofen", "tr": "ˈoːfn̩", "ru": "духовка"},
    {"de": "die Tür", "tr": "tyːɐ̯", "ru": "дверь"},
    {"de": "das Fenster", "tr": "ˈfɛn.stɐ", "ru": "окно"},
    {"de": "die Wand", "tr": "vant", "ru": "стена"},
    {"de": "der Boden", "tr": "ˈboːdn̩", "ru": "пол"},
    {"de": "sauber", "tr": "ˈzaʊ̯bɐ", "ru": "чистый"},
    {"de": "schmutzig", "tr": "ˈʃmʊt͡sɪç", "ru": "грязный"},
    {"de": "putzen", "tr": "ˈpʊt͡sn̩", "ru": "убирать"},
    {"de": "aufräumen", "tr": "ˈaʊ̯fˌʁɔɪ̯mən", "ru": "прибраться"},
    {"de": "waschen", "tr": "ˈvaʃn̩", "ru": "стирать"},
    {"de": "kochen", "tr": "ˈkɔxn̩", "ru": "готовить"},
    {"de": "spülen", "tr": "ˈʃpyːlən", "ru": "мыть посуду"},
    {"de": "die Rechnung", "tr": "ˈʁɛçnʊŋ", "ru": "квитанция"},
    {"de": "die Miete", "tr": "ˈmiːtə", "ru": "аренда"},
    {"de": "mieten", "tr": "ˈmiːtən", "ru": "снимать"},
    {"de": "vermieten", "tr": "fɛɐ̯ˈmiːtən", "ru": "сдавать"},
    {"de": "der Nachbar", "tr": "ˈnaχbaʁ", "ru": "сосед"},
    {"de": "die Nachbarin", "tr": "ˈnaχbaʁɪn", "ru": "соседка"},
    {"de": "das Zuhause", "tr": "t͡suˈhaʊ̯zə", "ru": "дом (уют)"},
    {"de": "wohnen", "tr": "ˈvoːnən", "ru": "жить"},
    {"de": "einziehen", "tr": "ˈaɪ̯nt͡siːən", "ru": "въезжать"},
    {"de": "ausziehen", "tr": "ˈaʊ̯st͡siːən", "ru": "съезжать"},
    {"de": "das Gerät", "tr": "ɡəˈʁɛːt", "ru": "прибор"},
    {"de": "kaputt", "tr": "kaˈpʊt", "ru": "сломанный"}
  ]
},
{
  "topic": "A1: Глаголы",
  "words": [
    {"de": "sein", "tr": "zaɪ̯n", "ru": "быть"},
    {"de": "haben", "tr": "ˈhaːbn̩", "ru": "иметь"},
    {"de": "werden", "tr": "ˈveːɐ̯dn̩", "ru": "становиться"},
    {"de": "gehen", "tr": "ˈɡeːən", "ru": "идти"},
    {"de": "fahren", "tr": "ˈfaːʁən", "ru": "ехать"},
    {"de": "kommen", "tr": "ˈkɔmn̩", "ru": "приходить"},
    {"de": "laufen", "tr": "ˈlaʊ̯fn̩", "ru": "бежать"},
    {"de": "sprechen", "tr": "ˈʃpʁɛçn̩", "ru": "говорить"},
    {"de": "sagen", "tr": "ˈzaːɡn̩", "ru": "сказать"},
    {"de": "fragen", "tr": "ˈfʁaːɡn̩", "ru": "спрашивать"},
    {"de": "antworten", "tr": "ˈantvɔʁtn̩", "ru": "отвечать"},
    {"de": "sehen", "tr": "ˈzeːən", "ru": "видеть"},
    {"de": "hören", "tr": "ˈhøːʁən", "ru": "слышать"},
    {"de": "essen", "tr": "ˈɛsn̩", "ru": "есть"},
    {"de": "trinken", "tr": "ˈtʁɪŋkn̩", "ru": "пить"},
    {"de": "schlafen", "tr": "ˈʃlaːfn̩", "ru": "спать"},
    {"de": "arbeiten", "tr": "ˈaʁbaɪ̯tn̩", "ru": "работать"},
    {"de": "lernen", "tr": "ˈlɛʁnən", "ru": "учить"},
    {"de": "studieren", "tr": "ʃtuˈdiːʁən", "ru": "изучать"},
    {"de": "spielen", "tr": "ˈʃpiːlən", "ru": "играть"},
    {"de": "schreiben", "tr": "ˈʃʁaɪ̯bn̩", "ru": "писать"},
    {"de": "lesen", "tr": "ˈleːzn̩", "ru": "читать"},
    {"de": "machen", "tr": "ˈmaxn̩", "ru": "делать"},
    {"de": "nehmen", "tr": "ˈneːmən", "ru": "брать"},
    {"de": "geben", "tr": "ˈɡeːbn̩", "ru": "давать"},
    {"de": "finden", "tr": "ˈfɪndn̩", "ru": "находить"},
    {"de": "suchen", "tr": "ˈzuːxn̩", "ru": "искать"},
    {"de": "bringen", "tr": "ˈbʁɪŋən", "ru": "приносить"},
    {"de": "bleiben", "tr": "ˈblaɪ̯bn̩", "ru": "оставаться"},
    {"de": "öffnen", "tr": "ˈœfnən", "ru": "открывать"},
    {"de": "schließen", "tr": "ˈʃliːsən", "ru": "закрывать"},
    {"de": "beginnen", "tr": "bəˈɡɪnən", "ru": "начинать"},
    {"de": "enden", "tr": "ˈɛndn̩", "ru": "заканчивать"},
    {"de": "helfen", "tr": "ˈhɛlfn̩", "ru": "помогать"},
    {"de": "brauchen", "tr": "ˈbʁaʊ̯xn̩", "ru": "нуждаться"},
    {"de": "lernen", "tr": "ˈlɛʁnən", "ru": "учить"},
    {"de": "ziehen", "tr": "ˈt͡siːən", "ru": "тянуть"},
    {"de": "tragen", "tr": "ˈtʁaːɡn̩", "ru": "нести"},
    {"de": "spielen", "tr": "ˈʃpiːlən", "ru": "играть"},
    {"de": "denken", "tr": "ˈdɛŋkn̩", "ru": "думать"},
    {"de": "glauben", "tr": "ˈɡlaʊ̯bn̩", "ru": "верить"},
    {"de": "hoffen", "tr": "ˈhɔfn̩", "ru": "надеяться"},
    {"de": "reisen", "tr": "ˈʁaɪ̯zn̩", "ru": "путешествовать"},
    {"de": "putzen", "tr": "ˈpʊt͡sn̩", "ru": "убирать"},
    {"de": "kochen", "tr": "ˈkɔxn̩", "ru": "готовить"},
    {"de": "duschen", "tr": "ˈduːʃn̩", "ru": "принимать душ"},
    {"de": "baden", "tr": "ˈbaːdn̩", "ru": "купаться"},
    {"de": "anziehen", "tr": "ˈant͡siːən", "ru": "одевать"},
    {"de": "ausziehen", "tr": "ˈaʊ̯st͡siːən", "ru": "раздевать"}
  ]
},
{
  "topic": "A1: Прилагательные",
  "words": [
    {"de": "groß", "tr": "ɡʁoːs", "ru": "большой"},
    {"de": "klein", "tr": "klaɪ̯n", "ru": "маленький"},
    {"de": "lang", "tr": "laŋ", "ru": "длинный"},
    {"de": "kurz", "tr": "kʊʁt͡s", "ru": "короткий"},
    {"de": "schön", "tr": "ʃøːn", "ru": "красивый"},
    {"de": "hässlich", "tr": "ˈhɛslɪç", "ru": "некрасивый"},
    {"de": "gut", "tr": "ɡuːt", "ru": "хороший"},
    {"de": "schlecht", "tr": "ʃlɛçt", "ru": "плохой"},
    {"de": "neu", "tr": "nɔʏ̯", "ru": "новый"},
    {"de": "alt", "tr": "alt", "ru": "старый"},
    {"de": "teuer", "tr": "ˈtɔʏ̯ɐ", "ru": "дорогой"},
    {"de": "billig", "tr": "ˈbɪlɪç", "ru": "дешёвый"},
    {"de": "hell", "tr": "hɛl", "ru": "светлый"},
    {"de": "dunkel", "tr": "ˈdʊŋkl̩", "ru": "тёмный"},
    {"de": "warm", "tr": "vaʁm", "ru": "тёплый"},
    {"de": "kalt", "tr": "kalt", "ru": "холодный"},
    {"de": "schnell", "tr": "ʃnɛl", "ru": "быстрый"},
    {"de": "langsam", "tr": "ˈlaŋzaːm", "ru": "медленный"},
    {"de": "laut", "tr": "laʊ̯t", "ru": "громкий"},
    {"de": "leise", "tr": "ˈlaɪ̯zə", "ru": "тихий"},
    {"de": "voll", "tr": "fɔl", "ru": "полный"},
    {"de": "leer", "tr": "leːɐ̯", "ru": "пустой"},
    {"de": "sauber", "tr": "ˈzaʊ̯bɐ", "ru": "чистый"},
    {"de": "schmutzig", "tr": "ˈʃmʊt͡sɪç", "ru": "грязный"},
    {"de": "stark", "tr": "ʃtaʁk", "ru": "сильный"},
    {"de": "schwach", "tr": "ʃvax", "ru": "слабый"},
    {"de": "freundlich", "tr": "ˈfʁɔɪ̯ntlɪç", "ru": "дружелюбный"},
    {"de": "unfreundlich", "tr": "ˈʊnfʁɔɪ̯ntlɪç", "ru": "недружелюбный"},
    {"de": "glücklich", "tr": "ˈɡlʏklɪç", "ru": "счастливый"},
    {"de": "traurig", "tr": "ˈtʁaʊ̯ʁɪç", "ru": "грустный"},
    {"de": "ruhig", "tr": "ˈʁuːɪç", "ru": "спокойный"},
    {"de": "nervös", "tr": "nɛʁˈvøːs", "ru": "нервный"},
    {"de": "müde", "tr": "ˈmyːdə", "ru": "уставший"},
    {"de": "krank", "tr": "kʁaŋk", "ru": "больной"},
    {"de": "gesund", "tr": "ɡəˈzʊnt", "ru": "здоровый"},
    {"de": "reich", "tr": "ʁaɪ̯ç", "ru": "богатый"},
    {"de": "arm", "tr": "aʁm", "ru": "бедный"},
    {"de": "interessant", "tr": "ɪntəʁɛˈzant", "ru": "интересный"},
    {"de": "langweilig", "tr": "ˈlaŋˌvaɪ̯lɪç", "ru": "скучный"},
    {"de": "leicht", "tr": "laɪ̯çt", "ru": "лёгкий"},
    {"de": "schwer", "tr": "ʃveːɐ̯", "ru": "тяжёлый"},
    {"de": "richtig", "tr": "ˈʁɪçtɪç", "ru": "правильный"},
    {"de": "falsch", "tr": "falʃ", "ru": "неправильный"},
    {"de": "tief", "tr": "tiːf", "ru": "глубокий"},
    {"de": "hoch", "tr": "hoːx", "ru": "высокий"},
    {"de": "ruhig", "tr": "ˈʁuːɪç", "ru": "тихий"},
    {"de": "wild", "tr": "vɪlt", "ru": "дикий"},
    {"de": "weich", "tr": "vaɪ̯ç", "ru": "мягкий"},
    {"de": "hart", "tr": "haʁt", "ru": "твёрдый"},
    {"de": "nah", "tr": "naː", "ru": "близкий"},
    {"de": "weit", "tr": "vaɪ̯t", "ru": "далёкий"}
  ]
},
{
  "topic": "A1: Наречия",
  "words": [
    {"de": "jetzt", "tr": "jɛt͡st", "ru": "сейчас"},
    {"de": "bald", "tr": "balt", "ru": "скоро"},
    {"de": "schon", "tr": "ʃoːn", "ru": "уже"},
    {"de": "noch", "tr": "nɔx", "ru": "ещё"},
    {"de": "immer", "tr": "ˈɪmɐ", "ru": "всегда"},
    {"de": "nie", "tr": "niː", "ru": "никогда"},
    {"de": "manchmal", "tr": "ˈmançmaːl", "ru": "иногда"},
    {"de": "oft", "tr": "ɔft", "ru": "часто"},
    {"de": "selten", "tr": "ˈzɛltn̩", "ru": "редко"},
    {"de": "gestern", "tr": "ˈɡɛstɐn", "ru": "вчера"},
    {"de": "heute", "tr": "ˈhɔʏ̯tə", "ru": "сегодня"},
    {"de": "morgen", "tr": "ˈmɔʁɡn̩", "ru": "завтра"},
    {"de": "draußen", "tr": "ˈdʁaʊ̯sn̩", "ru": "снаружи"},
    {"de": "drinnen", "tr": "ˈdʁɪnən", "ru": "внутри"},
    {"de": "oben", "tr": "ˈoːbn̩", "ru": "сверху"},
    {"de": "unten", "tr": "ˈʊntn̩", "ru": "снизу"},
    {"de": "links", "tr": "lɪŋks", "ru": "налево"},
    {"de": "rechts", "tr": "ʁɛçts", "ru": "направо"},
    {"de": "hinten", "tr": "ˈhɪntn̩", "ru": "сзади"},
    {"de": "vorne", "tr": "ˈfɔʁnə", "ru": "спереди"},
    {"de": "überall", "tr": "ˈyːbɐʔal", "ru": "везде"},
    {"de": "nirgendwo", "tr": "ˈnɪʁɡnt͡svoː", "ru": "нигде"},
    {"de": "hier", "tr": "hiːɐ̯", "ru": "здесь"},
    {"de": "dort", "tr": "dɔʁt", "ru": "там"},
    {"de": "zusammen", "tr": "t͡suˈzamən", "ru": "вместе"},
    {"de": "allein", "tr": "aˈlaɪ̯n", "ru": "один"},
    {"de": "genau", "tr": "ɡəˈnaʊ̯", "ru": "точно"},
    {"de": "ungefähr", "tr": "ˈʊnɡəfeːɐ̯", "ru": "примерно"},
    {"de": "schnell", "tr": "ʃnɛl", "ru": "быстро"},
    {"de": "langsam", "tr": "ˈlaŋzaːm", "ru": "медленно"},
    {"de": "gerne", "tr": "ˈɡɛʁnə", "ru": "охотно"},
    {"de": "wirklich", "tr": "ˈvɪʁklɪç", "ru": "действительно"},
    {"de": "vielleicht", "tr": "fiˈlaɪ̯çt", "ru": "возможно"},
    {"de": "leider", "tr": "ˈlaɪ̯dɐ", "ru": "к сожалению"},
    {"de": "zum Glück", "tr": "t͡sʊm ɡlʏk", "ru": "к счастью"},
    {"de": "plötzlich", "tr": "ˈplœt͡slɪç", "ru": "внезапно"},
    {"de": "sofort", "tr": "zoˈfɔʁt", "ru": "сразу"},
    {"de": "gleich", "tr": "ɡlaɪ̯ç", "ru": "сейчас же"},
    {"de": "vorhin", "tr": "ˈfoːʁhɪn", "ru": "только что"},
    {"de": "nachher", "tr": "ˈnaːxheːɐ̯", "ru": "позже"},
    {"de": "eben", "tr": "ˈeːbn̩", "ru": "именно"},
    {"de": "fast", "tr": "fast", "ru": "почти"},
    {"de": "ganz", "tr": "ɡant͡s", "ru": "совсем"},
    {"de": "weiter", "tr": "ˈvaɪ̯tɐ", "ru": "дальше"},
    {"de": "zurück", "tr": "t͡sʊˈʁʏk", "ru": "назад"},
    {"de": "oben", "tr": "ˈoːbn̩", "ru": "наверху"},
    {"de": "vorwärts", "tr": "ˈfoːʁvɛʁt͡s", "ru": "вперёд"}
  ]
},
{
  "topic": "A1: Предлоги",
  "words": [
    {"de": "an", "tr": "an", "ru": "на (вертикально)"},
    {"de": "auf", "tr": "aʊ̯f", "ru": "на (горизонтально)"},
    {"de": "in", "tr": "ɪn", "ru": "в"},
    {"de": "unter", "tr": "ˈʊntɐ", "ru": "под"},
    {"de": "über", "tr": "ˈyːbɐ", "ru": "над"},
    {"de": "neben", "tr": "ˈneːbn̩", "ru": "рядом"},
    {"de": "zwischen", "tr": "ˈt͡svɪʃn̩", "ru": "между"},
    {"de": "hinter", "tr": "ˈhɪntɐ", "ru": "за"},
    {"de": "vor", "tr": "foːɐ̯", "ru": "перед"},
    {"de": "mit", "tr": "mɪt", "ru": "с"},
    {"de": "ohne", "tr": "ˈoːnə", "ru": "без"},
    {"de": "für", "tr": "fyːɐ̯", "ru": "для"},
    {"de": "gegen", "tr": "ˈɡeːɡn̩", "ru": "против"},
    {"de": "um", "tr": "ʊm", "ru": "вокруг"},
    {"de": "bei", "tr": "baɪ̯", "ru": "у"},
    {"de": "zu", "tr": "t͡suː", "ru": "к"},
    {"de": "nach", "tr": "naːx", "ru": "в / после"},
    {"de": "aus", "tr": "aʊ̯s", "ru": "из"},
    {"de": "seit", "tr": "zaɪ̯t", "ru": "с (времени)"},
    {"de": "von", "tr": "fɔn", "ru": "от"},
    {"de": "über", "tr": "ˈyːbɐ", "ru": "о (тема)"},
    {"de": "trotz", "tr": "tʁɔt͡s", "ru": "несмотря на"},
    {"de": "während", "tr": "ˈvɛːʁənt", "ru": "во время"},
    {"de": "entlang", "tr": "ˈɛntlaŋ", "ru": "вдоль"},
    {"de": "außer", "tr": "ˈaʊ̯sɐ", "ru": "кроме"},
    {"de": "innerhalb", "tr": "ˈɪnɐhalp", "ru": "внутри"},
    {"de": "außerhalb", "tr": "ˈaʊ̯sɐhalp", "ru": "снаружи"},
    {"de": "oberhalb", "tr": "ˈoːbɐhalp", "ru": "над"},
    {"de": "unterhalb", "tr": "ˈʊntɐhalp", "ru": "под"},
    {"de": "vorbei", "tr": "foːɐ̯ˈbaɪ̯", "ru": "мимо"},
    {"de": "entgegen", "tr": "ɛntˈɡeːɡn̩", "ru": "навстречу"},
    {"de": "bis", "tr": "bɪs", "ru": "до"},
    {"de": "ab", "tr": "ap", "ru": "с (начиная с)"},
    {"de": "laut", "tr": "laʊ̯t", "ru": "согласно"},
    {"de": "gemäß", "tr": "ɡəˈmɛːs", "ru": "в соответствии"},
    {"de": "dank", "tr": "daŋk", "ru": "благодаря"},
    {"de": "inklusive", "tr": "ɪŋkluˈziːvə", "ru": "включая"},
    {"de": "anstatt", "tr": "anˈʃtat", "ru": "вместо"},
    {"de": "pro", "tr": "pʁoː", "ru": "в (расчёте на)"},
    {"de": "je", "tr": "jeː", "ru": "на каждого"},
    {"de": "via", "tr": "ˈviːa", "ru": "через"},
    {"de": "ohne", "tr": "ˈoːnə", "ru": "без"},
    {"de": "mitsamt", "tr": "mɪtˈzamt", "ru": "вместе с"},
    {"de": "nahe", "tr": "ˈnaːə", "ru": "близко к"},
    {"de": "unweit", "tr": "ˈʊnvaɪ̯t", "ru": "недалеко от"},
    {"de": "jenseits", "tr": "ˈjeːnzaɪ̯t͡s", "ru": "по ту сторону"},
    {"de": "diesseits", "tr": "ˈdiːszaɪ̯t͡s", "ru": "по эту сторону"},
    {"de": "zugunsten", "tr": "t͡suˈɡʊnstn̩", "ru": "в пользу"}
  ]
},
{
  "topic": "A1: Цвета",
  "words": [
    {"de": "rot", "tr": "ʁoːt", "ru": "красный"},
    {"de": "blau", "tr": "blaʊ̯", "ru": "синий"},
    {"de": "grün", "tr": "ɡʁyːn", "ru": "зелёный"},
    {"de": "gelb", "tr": "ɡɛlp", "ru": "жёлтый"},
    {"de": "schwarz", "tr": "ʃvaʁt͡s", "ru": "чёрный"},
    {"de": "weiß", "tr": "vaɪ̯s", "ru": "белый"},
    {"de": "grau", "tr": "ɡʁaʊ̯", "ru": "серый"},
    {"de": "braun", "tr": "bʁaʊ̯n", "ru": "коричневый"},
    {"de": "orange", "tr": "oˈʁãːʒə", "ru": "оранжевый"},
    {"de": "lila", "tr": "ˈliːla", "ru": "фиолетовый"},
    {"de": "rosa", "tr": "ˈʁoːza", "ru": "розовый"},
    {"de": "beige", "tr": "beːʒ", "ru": "бежевый"},
    {"de": "gold", "tr": "ɡɔlt", "ru": "золотой"},
    {"de": "silber", "tr": "ˈzɪlbɐ", "ru": "серебряный"},
    {"de": "hellblau", "tr": "ˈhɛlbl̩aʊ̯", "ru": "голубой"},
    {"de": "dunkelblau", "tr": "ˈdʊŋkl̩blaʊ̯", "ru": "тёмно-синий"},
    {"de": "hellgrün", "tr": "ˈhɛlɡʁyːn", "ru": "светло-зелёный"},
    {"de": "dunkelgrün", "tr": "ˈdʊŋkl̩ɡʁyːn", "ru": "тёмно-зелёный"},
    {"de": "pastell", "tr": "paˈstɛl", "ru": "пастельный"},
    {"de": "knallrot", "tr": "ˈknaɫˌʁoːt", "ru": "ярко-красный"},
    {"de": "meerblau", "tr": "ˈmeːɐ̯blaʊ̯", "ru": "морской синий"},
    {"de": "weinrot", "tr": "ˈvaɪ̯nˌʁoːt", "ru": "бордовый"},
    {"de": "khaki", "tr": "ˈkaːki", "ru": "хаки"},
    {"de": "türkis", "tr": "tʏʁˈkiːs", "ru": "бирюзовый"},
    {"de": "minze", "tr": "ˈmɪnt͡sə", "ru": "мятный"},
    {"de": "sandfarben", "tr": "ˈzantˌfaʁbn̩", "ru": "песочный"},
    {"de": "elfenbein", "tr": "ˈɛlfn̩baɪ̯n", "ru": "слоновая кость"},
    {"de": "koralle", "tr": "koˈʁalə", "ru": "коралловый"},
    {"de": "himbeer", "tr": "ˈhɪmbaːɐ̯", "ru": "малиновый"},
    {"de": "zimt", "tr": "t͡sɪmt", "ru": "коричный"},
    {"de": "taubenblau", "tr": "ˈtaʊ̯bn̩blaʊ̯", "ru": "сизый"},
    {"de": "stahlgrau", "tr": "ˈʃtaːlɡʁaʊ̯", "ru": "стальной"},
    {"de": "neon", "tr": "ˈneːɔn", "ru": "неоновый"},
    {"de": "farbig", "tr": "ˈfaʁbɪç", "ru": "цветной"},
    {"de": "farblos", "tr": "ˈfaʁbloːs", "ru": "бесцветный"},
    {"de": "kräftig", "tr": "ˈkʁɛftɪç", "ru": "насыщенный"},
    {"de": "blass", "tr": "blas", "ru": "бледный"},
    {"de": "leuchtend", "tr": "ˈlɔɪ̯çtnt", "ru": "яркий"},
    {"de": "dunkel", "tr": "ˈdʊŋkl̩", "ru": "тёмный"},
    {"de": "hell", "tr": "hɛl", "ru": "светлый"},
    {"de": "matt", "tr": "mat", "ru": "матовый"},
    {"de": "glänzend", "tr": "ˈɡlɛnt͡snd", "ru": "глянцевый"},
    {"de": "zart", "tr": "t͡saʁt", "ru": "нежный"},
    {"de": "kräftig rot", "tr": "ˈkʁɛftɪç ʁoːt", "ru": "насыщенно-красный"},
    {"de": "kräftig blau", "tr": "ˈkʁɛftɪç blaʊ̯", "ru": "насыщенно-синий"},
    {"de": "tiefschwarz", "tr": "ˈtiːfˌʃvaʁt͡s", "ru": "глубоко чёрный"},
    {"de": "eisblaue", "tr": "ˈaɪ̯sblaʊ̯ə", "ru": "ледяной синий"},
    {"de": "regenbogenfarben", "tr": "ˈʁeːɡn̩ˌboːɡn̩ˌfaʁbn̩", "ru": "радужный"}
    {"de": "glücklich", "tr": "ˈɡlʏklɪç", "ru": "счастливый"},
    {"de": "traurig", "tr": "ˈtʁaʊ̯ʁɪç", "ru": "грустный"},
    {"de": "wütend", "tr": "ˈvyːtn̩t", "ru": "злой"},
    {"de": "ruhig", "tr": "ˈʁuːɪç", "ru": "спокойный"},
    {"de": "gestresst", "tr": "ɡəˈʃtʁɛst", "ru": "в стрессе"},
    {"de": "gelassen", "tr": "ɡəˈlasn̩", "ru": "невозмутимый"},
    {"de": "nervös", "tr": "nɛʁˈvøːs", "ru": "нервный"},
    {"de": "überrascht", "tr": "ˌyːbɐˈʁaʃt", "ru": "удивлённый"},
    {"de": "erschrocken", "tr": "ɛɐ̯ˈʃʁɔkən", "ru": "испуганный"},
    {"de": "ängstlich", "tr": "ˈɛŋstlɪç", "ru": "тревожный"},
    {"de": "mutig", "tr": "ˈmuːtɪç", "ru": "смелый"},
    {"de": "hoffnungsvoll", "tr": "ˈhɔfnʊŋsˌfɔl", "ru": "полный надежд"},
    {"de": "enttäuscht", "tr": "ɛnˈtɔʏ̯ʃt", "ru": "разочарованный"},
    {"de": "verliebt", "tr": "fɛɐ̯ˈliːpt", "ru": "влюблённый"},
    {"de": "einsam", "tr": "ˈaɪ̯nzaːm", "ru": "одинокий"},
    {"de": "neugierig", "tr": "ˈnɔʏ̯ˌɡiːʁɪç", "ru": "любопытный"},
    {"de": "erschöpft", "tr": "ɛɐ̯ˈʃœpft", "ru": "истощённый"},
    {"de": "begeistert", "tr": "bəˈɡaɪ̯stɐt", "ru": "в восторге"},
    {"de": "verwirrt", "tr": "fɛɐ̯ˈvɪʁt", "ru": "запутанный"},
    {"de": "stolz", "tr": "ʃtɔlt͡s", "ru": "гордый"},
    {"de": "schuldig", "tr": "ˈʃʊldɪç", "ru": "виноватый"},
    {"de": "lustig", "tr": "ˈlʊstɪç", "ru": "весёлый"},
    {"de": "fröhlich", "tr": "ˈfʁøːlɪç", "ru": "радостный"},
    {"de": "gelangweilt", "tr": "ɡəˈlaŋvaɪ̯lt", "ru": "скучающий"},
    {"de": "verlegen", "tr": "fɛɐ̯ˈleːɡn̩", "ru": "смущённый"},
    {"de": "zufrieden", "tr": "t͡suˈfʁiːdn̩", "ru": "довольный"},
    {"de": "besorgt", "tr": "bəˈzɔʁkt", "ru": "обеспокоенный"},
    {"de": "genervt", "tr": "ɡəˈnɛʁft", "ru": "раздражённый"},
    {"de": "hilflos", "tr": "ˈhɪlfl̩oːs", "ru": "беспомощный"},
    {"de": "optimistisch", "tr": "ɔptimiˈstɪʃ", "ru": "оптимистичный"},
    {"de": "pessimistisch", "tr": "pɛsimiˈstɪʃ", "ru": "пессимистичный"},
    {"de": "friedlich", "tr": "ˈfʁiːdlɪç", "ru": "мирный"},
    {"de": "aggressiv", "tr": "aɡʁɛˈsiːf", "ru": "агрессивный"},
    {"de": "verzweifelt", "tr": "fɛɐ̯ˈt͡svaɪ̯fl̩t", "ru": "в отчаянии"},
    {"de": "ermutigt", "tr": "ɛɐ̯ˈmuːtɪɡt", "ru": "ободрённый"},
    {"de": "gelähmt", "tr": "ɡəˈlɛːmt", "ru": "парализованный"},
    {"de": "abwesend", "tr": "ˈapˌveːzn̩t", "ru": "отсутствующий"},
    {"de": "verärgert", "tr": "fɛɐ̯ˈʔɛʁɡɐt", "ru": "сердитый"},
    {"de": "sanft", "tr": "zanft", "ru": "нежный"},
    {"de": "empfindlich", "tr": "ɛmˈfɪntlɪç", "ru": "чувствительный"},
    {"de": "tapfer", "tr": "ˈtapfɐ", "ru": "храбрый"},
    {"de": "eifersüchtig", "tr": "ˈaɪ̯fɐˌzʏçtɪç", "ru": "ревнивый"},
    {"de": "panisch", "tr": "ˈpaːnɪʃ", "ru": "в панике"},
    {"de": "entspannt", "tr": "ɛntˈʃpant", "ru": "расслабленный"},
    {"de": "unruhig", "tr": "ˈʊnˌʁuːɪç", "ru": "беспокойный"},
    {"de": "mitfühlend", "tr": "ˈmɪtˌfyːlənt", "ru": "сочувствующий"},
    {"de": "gleichgültig", "tr": "ˈɡlaɪ̯çˌɡʏltɪç", "ru": "безразличный"}
  ]
},
{
  "topic": "A1: Предметы и техника",
  "words": [
    {"de": "das Handy", "tr": "ˈhɛndi", "ru": "телефон"},
    {"de": "das Smartphone", "tr": "ˈsmaːtˌfoːn", "ru": "смартфон"},
    {"de": "der Laptop", "tr": "ˈlɛptɔp", "ru": "ноутбук"},
    {"de": "der Computer", "tr": "kɔmˈpjuːtɐ", "ru": "компьютер"},
    {"de": "der Fernseher", "tr": "ˈfɛʁnˌzeːɐ̯", "ru": "телевизор"},
    {"de": "das Radio", "tr": "ˈʁaːdio", "ru": "радио"},
    {"de": "die Kamera", "tr": "ˈkaməʁa", "ru": "камера"},
    {"de": "die Uhr", "tr": "uːɐ̯", "ru": "часы"},
    {"de": "der Drucker", "tr": "ˈdʁʊkɐ", "ru": "принтер"},
    {"de": "die Tastatur", "tr": "tastaˈtuːɐ̯", "ru": "клавиатура"},
    {"de": "die Maus", "tr": "maʊ̯s", "ru": "мышь"},
    {"de": "das Kabel", "tr": "ˈkaːbl̩", "ru": "кабель"},
    {"de": "die Steckdose", "tr": "ˈʃtɛkˌdoːzə", "ru": "розетка"},
    {"de": "der Stecker", "tr": "ˈʃtɛkɐ", "ru": "вилка"},
    {"de": "die Lampe", "tr": "ˈlampə", "ru": "лампа"},
    {"de": "die Batterie", "tr": "batəˈʁiː", "ru": "батарейка"},
    {"de": "der Akku", "tr": "ˈaku", "ru": "аккумулятор"},
    {"de": "das Ladegerät", "tr": "ˈlaːdəɡəˌʁɛːt", "ru": "зарядное устройство"},
    {"de": "die Fernbedienung", "tr": "ˈfɛʁn bədiːnʊŋ", "ru": "пульт"},
    {"de": "der Lautsprecher", "tr": "ˈlaʊ̯tˌʃpʁɛçɐ", "ru": "колонка"},
    {"de": "die Kopfhörer", "tr": "ˈkɔpfˌhøːʁɐ", "ru": "наушники"},
    {"de": "das Mikrofon", "tr": "mikʁoˈfoːn", "ru": "микрофон"},
    {"de": "die App", "tr": "ɛp", "ru": "приложение"},
    {"de": "das Programm", "tr": "pʁoˈɡʁam", "ru": "программа"},
    {"de": "die Datei", "tr": "daˈtaɪ̯", "ru": "файл"},
    {"de": "die Taste", "tr": "ˈtastə", "ru": "кнопка"},
    {"de": "das Display", "tr": "ˈdɪspleː", "ru": "экран"},
    {"de": "der Bildschirm", "tr": "ˈbɪlt͡ʃɪʁm", "ru": "монитор"},
    {"de": "der Router", "tr": "ˈʁuːtɐ", "ru": "роутер"},
    {"de": "das Internet", "tr": "ˈɪntɐnɛt", "ru": "интернет"},
    {"de": "der Strom", "tr": "ʃtʁoːm", "ru": "электричество"},
    {"de": "die Maschine", "tr": "maˈʃiːnə", "ru": "машина (механизм)"},
    {"de": "die Werkzeug", "tr": "ˈvɛʁkˌt͡sɔɪ̯k", "ru": "инструмент"},
    {"de": "die Schere", "tr": "ˈʃeːʁə", "ru": "ножницы"},
    {"de": "der Hammer", "tr": "ˈhamɐ", "ru": "молоток"},
    {"de": "der Schraubenzieher", "tr": "ˈʃʁaʊ̯bn̩ˌt͡siːɐ̯", "ru": "отвёртка"},
    {"de": "die Bohrmaschine", "tr": "ˈboːɐ̯maˌʃiːnə", "ru": "дрель"},
    {"de": "die Kette", "tr": "ˈkɛtə", "ru": "цепь"},
    {"de": "der Schlüssel", "tr": "ˈʃlʏsl̩", "ru": "ключ"},
    {"de": "der Rucksack", "tr": "ˈʁʊkˌzak", "ru": "рюкзак"},
    {"de": "die Tasche", "tr": "ˈtaʃə", "ru": "сумка"},
    {"de": "die Brieftasche", "tr": "ˈbʁiːfˌtaʃə", "ru": "бумажник"},
    {"de": "das Portemonnaie", "tr": "pɔʁmɔˈneː", "ru": "кошелёк"},
    {"de": "der Ausweis", "tr": "ˈaʊ̯sˌvaɪ̯s", "ru": "удостоверение"},
    {"de": "die Karte", "tr": "ˈkaʁtə", "ru": "карта"},
    {"de": "der Stift", "tr": "ʃtɪft", "ru": "ручка"},
    {"de": "der Block", "tr": "blɔk", "ru": "блокнот"},
    {"de": "das Papier", "tr": "paˈpiːɐ̯", "ru": "бумага"},
    {"de": "die Flasche", "tr": "ˈflaʃə", "ru": "бутылка"},
    {"de": "die Tasse", "tr": "ˈtasə", "ru": "чашка"}
  ]
}


    global WORDS, WORDS_BY_TOPIC

    WORDS = []
    WORDS_BY_TOPIC = defaultdict(list)

    file_path = Path(path)
    if not file_path.exists():
        print(f"Файл {path} не найден. Положи words.json рядом с main.py")
        return

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    def add_word(raw: Dict[str, Any], topic_raw: str) -> None:
        """Добавляет одно слово в WORDS и WORDS_BY_TOPIC."""
        topic_raw = (topic_raw or "").strip()
        topic = TOPIC_NAME_MAP.get(topic_raw, TOPIC_DICT)

        idx = len(WORDS)
        word: Word = {
            "id": idx,
            "de": raw["de"],
            "tr": raw["tr"],
            "ru": raw["ru"],
            "topic": topic,
        }
        WORDS.append(word)

        WORDS_BY_TOPIC[topic].append(idx)
        WORDS_BY_TOPIC[TOPIC_DICT].append(idx)

    # Вариант 1: плоский список
    if isinstance(data, list):
        for raw in data:
            topic_raw = raw.get("topic") or raw.get("theme") or ""
            add_word(raw, topic_raw)

    # Вариант 2: объект с ключом "topics"
    elif isinstance(data, dict) and "topics" in data:
        for block in data["topics"]:
            topic_raw = block.get("topic") or block.get("name") or ""
            words_list = block.get("words", [])
            for raw in words_list:
                add_word(raw, topic_raw)
    else:
        print("Непонятный формат words.json. Ожидается список или объект с ключом 'topics'.")
        return

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

    Переотправляем то же самое слово после неправильного ответа.
    Список remaining не трогаем, чтобы слово не повторялось как новое.

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
