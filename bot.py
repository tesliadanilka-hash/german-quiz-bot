
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
TOPIC_ABSTRACT = "Абстрактные понятия"
TOPIC_VERBS = "Базовые глаголы"
TOPIC_TIME = "Время и календарь"
TOPIC_CITY = "Город и транспорт"
TOPIC_HOME = "Дом и жилье"
TOPIC_FOOD = "Еда и магазин"
TOPIC_ANIMALS = "Животные"
TOPIC_TOOLS = "Инструменты и быт"
TOPIC_IT = "Компьютер и интернет"
TOPIC_PERSONAL = "Личные данные"
TOPIC_CLOTHES = "Одежда"
TOPIC_WEATHER = "Погода и природа"
TOPIC_OBJECTS = "Предметы и вещи"
TOPIC_GREETINGS = "Приветствия и базовые фразы"
TOPIC_JOBS = "Профессии и работа"
TOPIC_FAMILY = "Семья"
TOPIC_DICT = "Словарь A1-B1"
TOPIC_BODY = "Тело и здоровье"
TOPIC_HOBBY = "Хобби и спорт"
TOPIC_COLORS_NUM = "Цвета и числа"
TOPIC_SCHOOL = "Школа и учеба"
TOPIC_EMOTIONS = "Эмоции и характер"

ALL_TOPICS = [
    TOPIC_GREETINGS,
    TOPIC_ABSTRACT,
    TOPIC_VERBS,
    TOPIC_TIME,
    TOPIC_CITY,
    TOPIC_HOME,
    TOPIC_FOOD,
    TOPIC_ANIMALS,
    TOPIC_TOOLS,
    TOPIC_IT,
    TOPIC_PERSONAL,
    TOPIC_CLOTHES,
    TOPIC_WEATHER,
    TOPIC_OBJECTS,
    TOPIC_JOBS,
    TOPIC_FAMILY,
    TOPIC_BODY,
    TOPIC_HOBBY,
    TOPIC_COLORS_NUM,
    TOPIC_SCHOOL,
    TOPIC_EMOTIONS,
    TOPIC_DICT,
]

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
# ГРАММАТИКА A1
# ==========================

# ВАЖНО
# СЮДА ТЫ ВСТАВЛЯЕШЬ СВОЙ СПИСОК GRAMMAR_RULES, КОТОРЫЙ МЫ РАНЬШЕ ПИСАЛИ.
# ПРИМЕР СТРУКТУРЫ ОСТАВЛЯЮ, НО ВСЕ ВНУТРИ СПИСКА МОЖЕШЬ ЗАМЕНИТЬ.

GRAMMAR_RULES: List[GrammarRule] = [
    # 1. sein
    {
        "id": 1,
        "level": "A1",
        "title": "Глагол sein (быть)",
        "description": (
            "Глагол \"sein\" один из самых важных и часто используемых глаголов в немецком языке. "
            "Он означает \"быть\" и является неправильным, поэтому его формы нужно выучить.\n\n"
            "Формы глагола \"sein\":\n"
            "ich bin\n"
            "du bist\n"
            "er/sie/es ist\n"
            "wir sind\n"
            "ihr seid\n"
            "sie/Sie sind\n\n"
            "Глагол \"sein\" используют, чтобы говорить о том, кто человек, где он находится и в каком состоянии."
        ),
        "examples": [
            {"de": "Ich bin müde.", "ru": "Я устал."},
            {"de": "Du bist krank.", "ru": "Ты болен."},
            {"de": "Er ist Lehrer.", "ru": "Он учитель."},
            {"de": "Wir sind zu Hause.", "ru": "Мы дома."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильную форму глагола \"sein\".",
                "question_de": "Ich ___ müde.",
                "options": ["bin", "bist", "ist", "seid"],
                "correct": 0,
                "answer_de": "Ich bin müde.",
                "answer_ru": "Я устал."
            },
            {
                "prompt": "Выбери правильную форму глагола \"sein\".",
                "question_de": "Du ___ krank.",
                "options": ["bin", "bist", "ist", "sind"],
                "correct": 1,
                "answer_de": "Du bist krank.",
                "answer_ru": "Ты болен."
            },
            {
                "prompt": "Выбери правильную форму глагола \"sein\".",
                "question_de": "Er ___ zu Hause.",
                "options": ["bin", "bist", "ist", "seid"],
                "correct": 2,
                "answer_de": "Er ist zu Hause.",
                "answer_ru": "Он дома."
            },
            {
                "prompt": "Выбери правильную форму глагола \"sein\".",
                "question_de": "Wir ___ Freunde.",
                "options": ["bin", "bist", "ist", "sind"],
                "correct": 3,
                "answer_de": "Wir sind Freunde.",
                "answer_ru": "Мы друзья."
            },
            {
                "prompt": "Выбери правильную форму глагола \"sein\".",
                "question_de": "Ihr ___ Schüler.",
                "options": ["bin", "bist", "ist", "seid"],
                "correct": 3,
                "answer_de": "Ihr seid Schüler.",
                "answer_ru": "Вы ученики."
            }
        ]
    },

    # 2. haben
    {
        "id": 2,
        "level": "A1",
        "title": "Глагол haben (иметь)",
        "description": (
            "Глагол \"haben\" означает \"иметь\". С его помощью говорят о том, чем человек владеет или что у него есть.\n\n"
            "Формы глагола \"haben\":\n"
            "ich habe\n"
            "du hast\n"
            "er/sie/es hat\n"
            "wir haben\n"
            "ihr habt\n"
            "sie/Sie haben\n\n"
            "Глагол \"haben\" часто используют с существительными: иметь книгу, машину, время, деньги."
        ),
        "examples": [
            {"de": "Ich habe ein Auto.", "ru": "У меня есть машина."},
            {"de": "Du hast Zeit.", "ru": "У тебя есть время."},
            {"de": "Er hat ein Problem.", "ru": "У него есть проблема."},
            {"de": "Wir haben eine Wohnung.", "ru": "У нас есть квартира."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильную форму глагола \"haben\".",
                "question_de": "Ich ___ ein Buch.",
                "options": ["habe", "hast", "hat", "haben"],
                "correct": 0,
                "answer_de": "Ich habe ein Buch.",
                "answer_ru": "У меня есть книга."
            },
            {
                "prompt": "Выбери правильную форму глагола \"haben\".",
                "question_de": "Du ___ eine Frage.",
                "options": ["habe", "hast", "hat", "habt"],
                "correct": 1,
                "answer_de": "Du hast eine Frage.",
                "answer_ru": "У тебя есть вопрос."
            },
            {
                "prompt": "Выбери правильную форму глагола \"haben\".",
                "question_de": "Er ___ ein Problem.",
                "options": ["habe", "hast", "hat", "haben"],
                "correct": 2,
                "answer_de": "Er hat ein Problem.",
                "answer_ru": "У него есть проблема."
            },
            {
                "prompt": "Выбери правильную форму глагола \"haben\".",
                "question_de": "Wir ___ eine Wohnung.",
                "options": ["habe", "hast", "hat", "haben"],
                "correct": 3,
                "answer_de": "Wir haben eine Wohnung.",
                "answer_ru": "У нас есть квартира."
            },
            {
                "prompt": "Выбери правильную форму глагола \"haben\".",
                "question_de": "Sie ___ zwei Kinder.",
                "options": ["habe", "hast", "hat", "haben"],
                "correct": 3,
                "answer_de": "Sie haben zwei Kinder.",
                "answer_ru": "У них есть двое детей."
            }
        ]
    },

    # 3. определенный артикль
    {
        "id": 3,
        "level": "A1",
        "title": "Определенный артикль der, die, das",
        "description": (
            "Определенный артикль используют, когда говорят о конкретном предмете.\n\n"
            "der мужской род\n"
            "die женский род\n"
            "das средний род\n\n"
            "Во множественном числе для всех родов используется die. "
            "Артикль всегда стоит перед существительным."
        ),
        "examples": [
            {"de": "Der Tisch ist groß.", "ru": "Стол большой."},
            {"de": "Die Lampe ist neu.", "ru": "Лампа новая."},
            {"de": "Das Auto ist alt.", "ru": "Машина старая."},
            {"de": "Die Kinder sind laut.", "ru": "Дети шумные."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильный артикль.",
                "question_de": "___ Tisch (стол)",
                "options": ["Der", "Die", "Das", "Den"],
                "correct": 0,
                "answer_de": "Der Tisch.",
                "answer_ru": "Стол."
            },
            {
                "prompt": "Выбери правильный артикль.",
                "question_de": "___ Lampe (лампа)",
                "options": ["Der", "Die", "Das", "Dem"],
                "correct": 1,
                "answer_de": "Die Lampe.",
                "answer_ru": "Лампа."
            },
            {
                "prompt": "Выбери правильный артикль.",
                "question_de": "___ Auto (машина)",
                "options": ["Der", "Die", "Das", "Den"],
                "correct": 2,
                "answer_de": "Das Auto.",
                "answer_ru": "Машина."
            },
            {
                "prompt": "Выбери правильный артикль.",
                "question_de": "___ Mann (мужчина)",
                "options": ["Der", "Die", "Das", "Dem"],
                "correct": 0,
                "answer_de": "Der Mann.",
                "answer_ru": "Мужчина."
            },
            {
                "prompt": "Выбери правильный артикль во множественном числе.",
                "question_de": "___ Kinder (дети)",
                "options": ["Der", "Die", "Das", "Den"],
                "correct": 1,
                "answer_de": "Die Kinder.",
                "answer_ru": "Дети."
            }
        ]
    },

    # 4. неопределенный артикль
    {
        "id": 4,
        "level": "A1",
        "title": "Неопределенный артикль ein, eine",
        "description": (
            "Неопределенный артикль используют, когда говорят о предмете не конкретно или в первый раз.\n\n"
            "ein мужской и средний род\n"
            "eine женский род\n\n"
            "Неопределенный артикль не используют во множественном числе."
        ),
        "examples": [
            {"de": "Ich kaufe ein Buch.", "ru": "Я покупаю книгу."},
            {"de": "Sie hat eine Katze.", "ru": "У нее есть кошка."},
            {"de": "Er fährt ein Auto.", "ru": "Он ездит на машине."},
            {"de": "Wir suchen eine Wohnung.", "ru": "Мы ищем квартиру."}
        ],
        "questions": [
            {
                "prompt": "Подставь правильный неопределенный артикль.",
                "question_de": "Ich kaufe ___ Buch. (книга, ср. род)",
                "options": ["ein", "eine", "-", "der"],
                "correct": 0,
                "answer_de": "Ich kaufe ein Buch.",
                "answer_ru": "Я покупаю книгу."
            },
            {
                "prompt": "Подставь правильный неопределенный артикль.",
                "question_de": "Sie hat ___ Katze. (кошка, ж. род)",
                "options": ["ein", "eine", "-", "die"],
                "correct": 1,
                "answer_de": "Sie hat eine Katze.",
                "answer_ru": "У нее есть кошка."
            },
            {
                "prompt": "Подставь правильный неопределенный артикль.",
                "question_de": "Er sucht ___ Wohnung. (квартира, ж. род)",
                "options": ["ein", "eine", "-", "der"],
                "correct": 1,
                "answer_de": "Er sucht eine Wohnung.",
                "answer_ru": "Он ищет квартиру."
            },
            {
                "prompt": "Подставь правильный неопределенный артикль.",
                "question_de": "Wir kaufen ___ Auto. (машина, ср. род)",
                "options": ["ein", "eine", "-", "das"],
                "correct": 0,
                "answer_de": "Wir kaufen ein Auto.",
                "answer_ru": "Мы покупаем машину."
            },
            {
                "prompt": "Выбери правильное предложение.",
                "question_de": "Как правильно?",
                "options": [
                    "Ich habe eine Auto.",
                    "Ich habe ein Auto.",
                    "Ich habe ein Katze.",
                    "Ich habe eine Buch."
                ],
                "correct": 1,
                "answer_de": "Ich habe ein Auto.",
                "answer_ru": "У меня есть машина."
            }
        ]
    },

    # 5. порядок слов
    {
        "id": 5,
        "level": "A1",
        "title": "Порядок слов: глагол на втором месте",
        "description": (
            "Самое важное правило немецкого предложения: глагол стоит на втором месте.\n\n"
            "Это значит, что сначала идет одно целое место подлежащее или обстоятельство, "
            "а на второй позиции всегда стоит сказуемое спряженный глагол.\n\n"
            "Пример:\n"
            "Ich gehe heute nach Hause.\n"
            "Heute gehe ich nach Hause.\n"
            "В обоих предложениях глагол \"gehe\" стоит на втором месте."
        ),
        "examples": [
            {"de": "Ich wohne in Deutschland.", "ru": "Я живу в Германии."},
            {"de": "Heute arbeite ich zu Hause.", "ru": "Сегодня я работаю дома."},
            {"de": "Morgen fahre ich nach Berlin.", "ru": "Завтра я еду в Берлин."},
            {"de": "Mein Bruder lernt Deutsch.", "ru": "Мой брат учит немецкий."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильный порядок слов.",
                "question_de": "Я живу в Германии.",
                "options": [
                    "Ich in Deutschland wohne.",
                    "Ich wohne in Deutschland.",
                    "Wohne ich in Deutschland.",
                    "In Deutschland ich wohne."
                ],
                "correct": 1,
                "answer_de": "Ich wohne in Deutschland.",
                "answer_ru": "Я живу в Германии."
            },
            {
                "prompt": "Выбери правильный порядок слов.",
                "question_de": "Сегодня я работаю дома.",
                "options": [
                    "Heute ich arbeite zu Hause.",
                    "Ich arbeite heute zu Hause.",
                    "Heute arbeite ich zu Hause.",
                    "Ich heute arbeite zu Hause."
                ],
                "correct": 2,
                "answer_de": "Heute arbeite ich zu Hause.",
                "answer_ru": "Сегодня я работаю дома."
            },
            {
                "prompt": "Выбери правильный порядок слов.",
                "question_de": "Завтра я еду в Берлин.",
                "options": [
                    "Morgen ich fahre nach Berlin.",
                    "Ich fahre nach Berlin morgen.",
                    "Morgen fahre ich nach Berlin.",
                    "Fahre ich morgen nach Berlin."
                ],
                "correct": 2,
                "answer_de": "Morgen fahre ich nach Berlin.",
                "answer_ru": "Завтра я еду в Берлин."
            },
            {
                "prompt": "Выбери правильный порядок слов.",
                "question_de": "Мой брат учит немецкий.",
                "options": [
                    "Mein Bruder lernt Deutsch.",
                    "Mein Bruder Deutsch lernt.",
                    "Lernt Deutsch mein Bruder.",
                    "Deutsch lernt mein Bruder."
                ],
                "correct": 0,
                "answer_de": "Mein Bruder lernt Deutsch.",
                "answer_ru": "Мой брат учит немецкий."
            },
            {
                "prompt": "Выбери правильный порядок слов.",
                "question_de": "Вечером я читаю книгу.",
                "options": [
                    "Abends lese ich ein Buch.",
                    "Abends ich lese ein Buch.",
                    "Ich lese ein Buch abends.",
                    "Ich ein Buch lese abends."
                ],
                "correct": 0,
                "answer_de": "Abends lese ich ein Buch.",
                "answer_ru": "Вечером я читаю книгу."
            }
        ]
    },

    # 6. личные местоимения
    {
        "id": 6,
        "level": "A1",
        "title": "Личные местоимения в Nominativ",
        "description": (
            "Личные местоимения заменяют существительные и отвечают за лицо и число.\n\n"
            "ich я\n"
            "du ты\n"
            "er он\n"
            "sie она\n"
            "es оно\n"
            "wir мы\n"
            "ihr вы множественное число\n"
            "sie они\n"
            "Sie Вы вежливая форма"
        ),
        "examples": [
            {"de": "Ich komme aus Russland.", "ru": "Я из России."},
            {"de": "Du lernst Deutsch.", "ru": "Ты учишь немецкий."},
            {"de": "Wir spielen Fußball.", "ru": "Мы играем в футбол."},
            {"de": "Sie wohnen in Berlin.", "ru": "Они живут в Берлине."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильное местоимение.",
                "question_de": "___ komme aus Spanien. (я)",
                "options": ["Du", "Ich", "Er", "Sie"],
                "correct": 1,
                "answer_de": "Ich komme aus Spanien.",
                "answer_ru": "Я из Испании."
            },
            {
                "prompt": "Выбери правильное местоимение.",
                "question_de": "___ lernst Deutsch. (ты)",
                "options": ["Ich", "Du", "Er", "Wir"],
                "correct": 1,
                "answer_de": "Du lernst Deutsch.",
                "answer_ru": "Ты учишь немецкий."
            },
            {
                "prompt": "Выбери правильное местоимение.",
                "question_de": "___ ist Lehrerin. (она)",
                "options": ["Er", "Sie", "Es", "Wir"],
                "correct": 1,
                "answer_de": "Sie ist Lehrerin.",
                "answer_ru": "Она учительница."
            },
            {
                "prompt": "Выбери правильное местоимение.",
                "question_de": "___ wohnen in Wien. (они)",
                "options": ["Sie", "Wir", "Ihr", "Es"],
                "correct": 0,
                "answer_de": "Sie wohnen in Wien.",
                "answer_ru": "Они живут в Вене."
            },
            {
                "prompt": "Выбери правильное местоимение.",
                "question_de": "___ seid müde. (вы множественное)",
                "options": ["Du", "Ihr", "Wir", "Sie"],
                "correct": 1,
                "answer_de": "Ihr seid müde.",
                "answer_ru": "Вы устали."
            }
        ]
    },

    # 7. притяжательные местоимения
    {
        "id": 7,
        "level": "A1",
        "title": "Притяжательные местоимения mein, dein и другие",
        "description": (
            "Притяжательные местоимения показывают принадлежность.\n\n"
            "mein мой\n"
            "dein твой\n"
            "sein его\n"
            "ihr ее\n"
            "unser наш\n"
            "euer ваш множественное\n"
            "ihr их\n"
            "Ihr Ваш вежливая форма\n\n"
            "В Nominativ единственного числа без окончания для мужского и среднего рода."
        ),
        "examples": [
            {"de": "Das ist mein Auto.", "ru": "Это моя машина."},
            {"de": "Ist das dein Buch?", "ru": "Это твоя книга?"},
            {"de": "Sein Bruder wohnt in Hamburg.", "ru": "Его брат живет в Гамбурге."},
            {"de": "Unsere Wohnung ist klein.", "ru": "Наша квартира маленькая."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильное притяжательное местоимение.",
                "question_de": "Das ist ___ Haus. (мой)",
                "options": ["dein", "sein", "mein", "ihr"],
                "correct": 2,
                "answer_de": "Das ist mein Haus.",
                "answer_ru": "Это мой дом."
            },
            {
                "prompt": "Выбери правильное притяжательное местоимение.",
                "question_de": "Ist das ___ Auto? (твой)",
                "options": ["mein", "dein", "sein", "unser"],
                "correct": 1,
                "answer_de": "Ist das dein Auto?",
                "answer_ru": "Это твоя машина?"
            },
            {
                "prompt": "Выбери правильное притяжательное местоимение.",
                "question_de": "Wie heißt ___ Mutter? (твоя)",
                "options": ["mein", "deine", "dein", "ihr"],
                "correct": 1,
                "answer_de": "Wie heißt deine Mutter?",
                "answer_ru": "Как зовут твою маму?"
            },
            {
                "prompt": "Выбери правильное притяжательное местоимение.",
                "question_de": "___ Freund kommt morgen. (его)",
                "options": ["Ihr", "Sein", "Ihrer", "Euer"],
                "correct": 1,
                "answer_de": "Sein Freund kommt morgen.",
                "answer_ru": "Его друг придет завтра."
            },
            {
                "prompt": "Выбери правильное притяжательное местоимение.",
                "question_de": "___ Kinder spielen im Garten. (их)",
                "options": ["Ihre", "Eure", "ihre", "Unser"],
                "correct": 2,
                "answer_de": "Ihre Kinder spielen im Garten.",
                "answer_ru": "Их дети играют в саду."
            }
        ]
    },

    # 8. отрицание nicht и kein
    {
        "id": 8,
        "level": "A1",
        "title": "Отрицание: nicht и kein",
        "description": (
            "В немецком есть два основных способа отрицания: \"nicht\" и \"kein\".\n\n"
            "nicht ставится перед прилагательным, наречием, глаголом или целым предложением.\n"
            "kein используется вместо неопределенного артикля, когда мы отрицаем существительное.\n\n"
            "kein мужской и средний род, keine женский род и множественное число."
        ),
        "examples": [
            {"de": "Ich bin nicht müde.", "ru": "Я не устал."},
            {"de": "Er arbeitet heute nicht.", "ru": "Он сегодня не работает."},
            {"de": "Ich habe kein Auto.", "ru": "У меня нет машины."},
            {"de": "Wir haben keine Zeit.", "ru": "У нас нет времени."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильное отрицание.",
                "question_de": "Ich bin ___ müde.",
                "options": ["kein", "keine", "nicht", "nichts"],
                "correct": 2,
                "answer_de": "Ich bin nicht müde.",
                "answer_ru": "Я не устал."
            },
            {
                "prompt": "Выбери правильное отрицание.",
                "question_de": "Ich habe ___ Auto.",
                "options": ["nicht", "kein", "keine", "kein Auto nicht"],
                "correct": 1,
                "answer_de": "Ich habe kein Auto.",
                "answer_ru": "У меня нет машины."
            },
            {
                "prompt": "Выбери правильное отрицание.",
                "question_de": "Wir haben ___ Zeit.",
                "options": ["kein", "keine", "nicht", "keinen"],
                "correct": 1,
                "answer_de": "Wir haben keine Zeit.",
                "answer_ru": "У нас нет времени."
            },
            {
                "prompt": "Выбери правильное отрицание.",
                "question_de": "Er wohnt ___ in Berlin.",
                "options": ["kein", "keine", "nicht", "niemals"],
                "correct": 2,
                "answer_de": "Er wohnt nicht in Berlin.",
                "answer_ru": "Он не живет в Берлине."
            },
            {
                "prompt": "Выбери правильное отрицание.",
                "question_de": "Sie hat ___ Kinder.",
                "options": ["nicht", "kein", "keine", "keinen"],
                "correct": 2,
                "answer_de": "Sie hat keine Kinder.",
                "answer_ru": "У нее нет детей."
            }
        ]
    },

    # 9. вопросы ja nein и W-Fragen
    {
        "id": 9,
        "level": "A1",
        "title": "Вопросы: Ja-Nein и W-Fragen",
        "description": (
            "В немецком есть два типа вопросов.\n\n"
            "1. Ja-Nein-Fragen вопросы да/нет. Глагол ставится на первое место.\n"
            "Beispiel: Kommst du heute?\n\n"
            "2. W-Fragen вопросы с вопросительным словом: wo, wer, was, wann, wie и другие. "
            "Сначала идет вопросительное слово, затем глагол.\n"
            "Beispiel: Wo wohnst du?"
        ),
        "examples": [
            {"de": "Kommst du heute?", "ru": "Ты придешь сегодня?"},
            {"de": "Wohnst du in Köln?", "ru": "Ты живешь в Кельне?"},
            {"de": "Wo arbeitest du?", "ru": "Где ты работаешь?"},
            {"de": "Wann fährst du nach Hause?", "ru": "Когда ты едешь домой?"}
        ],
        "questions": [
            {
                "prompt": "Выбери правильный вопрос Ja-Nein.",
                "question_de": "Ты живешь в Берлине?",
                "options": [
                    "Wohnst du in Berlin?",
                    "Du wohnst in Berlin?",
                    "In Berlin wohnst du?",
                    "Wo wohnst du in Berlin?"
                ],
                "correct": 0,
                "answer_de": "Wohnst du in Berlin?",
                "answer_ru": "Ты живешь в Берлине?"
            },
            {
                "prompt": "Выбери правильный вопрос с wo.",
                "question_de": "Где ты работаешь?",
                "options": [
                    "Du arbeitest wo?",
                    "Wo arbeitest du?",
                    "Arbeitest du wo?",
                    "Wo du arbeitest?"
                ],
                "correct": 1,
                "answer_de": "Wo arbeitest du?",
                "answer_ru": "Где ты работаешь?"
            },
            {
                "prompt": "Выбери правильный вопрос Ja-Nein.",
                "question_de": "Ты говоришь по-немецки?",
                "options": [
                    "Sprichst du Deutsch?",
                    "Du sprichst Deutsch?",
                    "Deutsch sprichst du?",
                    "Wo sprichst du Deutsch?"
                ],
                "correct": 0,
                "answer_de": "Sprichst du Deutsch?",
                "answer_ru": "Ты говоришь по-немецки?"
            },
            {
                "prompt": "Выбери правильный вопрос с wann.",
                "question_de": "Когда ты идешь домой?",
                "options": [
                    "Wann gehst du nach Hause?",
                    "Gehst du wann nach Hause?",
                    "Du gehst wann nach Hause?",
                    "Wann du gehst nach Hause?"
                ],
                "correct": 0,
                "answer_de": "Wann gehst du nach Hause?",
                "answer_ru": "Когда ты идешь домой?"
            },
            {
                "prompt": "Выбери правильный вопрос с wie.",
                "question_de": "Как тебя зовут?",
                "options": [
                    "Wie heißt du?",
                    "Du heißt wie?",
                    "Heißt du wie?",
                    "Wie du heißt?"
                ],
                "correct": 0,
                "answer_de": "Wie heißt du?",
                "answer_ru": "Как тебя зовут?"
            }
        ]
    },

    # 10. предлоги времени
    {
        "id": 10,
        "level": "A1",
        "title": "Предлоги времени: am, um, im",
        "description": (
            "Часто используемые предлоги времени:\n\n"
            "am для дней недели и дат: am Montag, am 3. Mai\n"
            "um для точного времени по часам: um 8 Uhr\n"
            "im для месяцев и времен года: im Juli, im Winter"
        ),
        "examples": [
            {"de": "Am Montag habe ich Deutschkurs.", "ru": "В понедельник у меня курс немецкого."},
            {"de": "Der Termin ist um 9 Uhr.", "ru": "Встреча в 9 часов."},
            {"de": "Im Januar ist es kalt.", "ru": "В январе холодно."},
            {"de": "Im Sommer fahre ich ans Meer.", "ru": "Летом я еду на море."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильный предлог времени.",
                "question_de": "___ Freitag gehe ich ins Kino.",
                "options": ["Um", "Am", "Im", "In"],
                "correct": 1,
                "answer_de": "Am Freitag gehe ich ins Kino.",
                "answer_ru": "В пятницу я иду в кино."
            },
            {
                "prompt": "Выбери правильный предлог времени.",
                "question_de": "Der Kurs beginnt ___ 18 Uhr.",
                "options": ["am", "um", "im", "in"],
                "correct": 1,
                "answer_de": "Der Kurs beginnt um 18 Uhr.",
                "answer_ru": "Курс начинается в 18 часов."
            },
            {
                "prompt": "Выбери правильный предлог времени.",
                "question_de": "___ August machen wir Urlaub.",
                "options": ["Am", "Um", "Im", "In"],
                "correct": 2,
                "answer_de": "Im August machen wir Urlaub.",
                "answer_ru": "В августе мы берем отпуск."
            },
            {
                "prompt": "Выбери правильный предлог времени.",
                "question_de": "___ Winter ist es oft kalt.",
                "options": ["Am", "Um", "Im", "In"],
                "correct": 2,
                "answer_de": "Im Winter ist es oft kalt.",
                "answer_ru": "Зимой часто холодно."
            },
            {
                "prompt": "Выбери правильный предлог времени.",
                "question_de": "Das Meeting ist ___ Mittwoch.",
                "options": ["um", "am", "im", "in"],
                "correct": 1,
                "answer_de": "Das Meeting ist am Mittwoch.",
                "answer_ru": "Встреча в среду."
            }
        ]
    },

    # 11. предлоги места
    {
        "id": 11,
        "level": "A1",
        "title": "Предлоги места: in, auf, unter, neben и другие",
        "description": (
            "Предлоги места показывают, где находится предмет.\n\n"
            "in в, внутри\n"
            "auf на горизонтальной поверхности\n"
            "unter под\n"
            "neben рядом\n"
            "vor перед\n"
            "hinter за"
        ),
        "examples": [
            {"de": "Das Buch liegt auf dem Tisch.", "ru": "Книга лежит на столе."},
            {"de": "Die Katze sitzt unter dem Stuhl.", "ru": "Кошка сидит под стулом."},
            {"de": "Die Kinder spielen im Garten.", "ru": "Дети играют в саду."},
            {"de": "Die Lampe steht neben dem Bett.", "ru": "Лампа стоит рядом с кроватью."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильный предлог места.",
                "question_de": "Das Buch liegt ___ dem Tisch.",
                "options": ["in", "auf", "unter", "neben"],
                "correct": 1,
                "answer_de": "Das Buch liegt auf dem Tisch.",
                "answer_ru": "Книга лежит на столе."
            },
            {
                "prompt": "Выбери правильный предлог места.",
                "question_de": "Die Katze sitzt ___ dem Stuhl.",
                "options": ["auf", "unter", "neben", "hinter"],
                "correct": 1,
                "answer_de": "Die Katze sitzt unter dem Stuhl.",
                "answer_ru": "Кошка сидит под стулом."
            },
            {
                "prompt": "Выбери правильный предлог места.",
                "question_de": "Die Lampe steht ___ dem Bett.",
                "options": ["neben", "unter", "vor", "hinter"],
                "correct": 0,
                "answer_de": "Die Lampe steht neben dem Bett.",
                "answer_ru": "Лампа стоит рядом с кроватью."
            },
            {
                "prompt": "Выбери правильный предлог места.",
                "question_de": "Die Kinder spielen ___ Garten.",
                "options": ["auf dem", "im", "unter dem", "neben dem"],
                "correct": 1,
                "answer_de": "Die Kinder spielen im Garten.",
                "answer_ru": "Дети играют в саду."
            },
            {
                "prompt": "Выбери правильный предлог места.",
                "question_de": "Das Auto steht ___ dem Haus.",
                "options": ["in", "unter", "vor", "hinter"],
                "correct": 2,
                "answer_de": "Das Auto steht vor dem Haus.",
                "answer_ru": "Машина стоит перед домом."
            }
        ]
    },

    # 12. модальный глагол können
    {
        "id": 12,
        "level": "A1",
        "title": "Модальный глагол können",
        "description": (
            "Модальные глаголы выражают возможность, обязанность, желание. "
            "На уровне A1 часто используют глагол \"können\" уметь, мочь.\n\n"
            "Формы \"können\":\n"
            "ich kann\n"
            "du kannst\n"
            "er/sie/es kann\n"
            "wir können\n"
            "ihr könnt\n"
            "sie/Sie können\n\n"
            "В предложении модальный глагол на втором месте, смысловой глагол в инфинитиве в конце."
        ),
        "examples": [
            {"de": "Ich kann Deutsch sprechen.", "ru": "Я могу говорить по-немецки."},
            {"de": "Du kannst gut kochen.", "ru": "Ты хорошо умеешь готовить."},
            {"de": "Wir können heute nicht kommen.", "ru": "Мы не можем сегодня прийти."},
            {"de": "Sie kann sehr gut singen.", "ru": "Она очень хорошо поет."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильную форму и порядок слов.",
                "question_de": "Я могу плавать.",
                "options": [
                    "Ich kann schwimmen.",
                    "Ich schwimmen kann.",
                    "Kann ich schwimmen.",
                    "Ich kann schwimme."
                ],
                "correct": 0,
                "answer_de": "Ich kann schwimmen.",
                "answer_ru": "Я могу плавать."
            },
            {
                "prompt": "Выбери правильную форму и порядок слов.",
                "question_de": "Ты можешь помочь?",
                "options": [
                    "Kannst du helfen?",
                    "Du kannst helfen?",
                    "Du helfen kannst?",
                    "Kann du helfen?"
                ],
                "correct": 0,
                "answer_de": "Kannst du helfen?",
                "answer_ru": "Ты можешь помочь?"
            },
            {
                "prompt": "Выбери правильное предложение.",
                "question_de": "Он может сегодня прийти.",
                "options": [
                    "Er kann heute kommen.",
                    "Er kann kommen сегодня.",
                    "Heute er kann kommen.",
                    "Er heute kann kommen."
                ],
                "correct": 0,
                "answer_de": "Er kann heute kommen.",
                "answer_ru": "Он может сегодня прийти."
            },
            {
                "prompt": "Выбери правильную форму и порядок слов.",
                "question_de": "Мы не можем работать.",
                "options": [
                    "Wir können nicht arbeiten.",
                    "Wir können arbeiten nicht.",
                    "Wir nicht können arbeiten.",
                    "Können wir не arbeiten."
                ],
                "correct": 0,
                "answer_de": "Wir können nicht arbeiten.",
                "answer_ru": "Мы не можем работать."
            },
            {
                "prompt": "Выбери правильную форму и порядок слов.",
                "question_de": "Они могут играть в футбол.",
                "options": [
                    "Sie kann Fußball spielen.",
                    "Sie können Fußball spielen.",
                    "Sie können spielen Fußball.",
                    "Können sie Fußball spielen."
                ],
                "correct": 1,
                "answer_de": "Sie können Fußball spielen.",
                "answer_ru": "Они могут играть в футбол."
            }
        ]
    },

    # 13. отделяемые приставки
    {
        "id": 13,
        "level": "A1",
        "title": "Отделяемые приставки: aufstehen, einkaufen и другие",
        "description": (
            "У многих глаголов в немецком есть отделяемая приставка: auf, an, ein, mit и другие.\n"
            "В обычном предложении приставка уходит в конец, а глагол на втором месте.\n\n"
            "Beispiele:\n"
            "Ich stehe um 7 Uhr auf.\n"
            "Wir kaufen im Supermarkt ein."
        ),
        "examples": [
            {"de": "Ich stehe früh auf.", "ru": "Я рано встаю."},
            {"de": "Er ruft seine Mutter an.", "ru": "Он звонит своей маме."},
            {"de": "Wir kaufen am Samstag ein.", "ru": "Мы делаем покупки в субботу."},
            {"de": "Sie bringt das Kind mit.", "ru": "Она приводит с собой ребенка."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильный порядок слов с отделяемой приставкой.",
                "question_de": "Я встаю в 6 часов.",
                "options": [
                    "Ich stehe um 6 Uhr auf.",
                    "Ich aufstehe um 6 Uhr.",
                    "Ich stehe auf um 6 Uhr.",
                    "Um 6 Uhr ich stehe auf."
                ],
                "correct": 0,
                "answer_de": "Ich stehe um 6 Uhr auf.",
                "answer_ru": "Я встаю в 6 часов."
            },
            {
                "prompt": "Выбери правильное предложение.",
                "question_de": "Он звонит другу.",
                "options": [
                    "Er ruft den Freund an.",
                    "Er anruft den Freund.",
                    "Er ruft an den Freund.",
                    "Ruft er den Freund an."
                ],
                "correct": 0,
                "answer_de": "Er ruft den Freund ан.",
                "answer_ru": "Он звонит другу."
            },
            {
                "prompt": "Выбери правильное предложение.",
                "question_de": "Мы делаем покупки в субботу.",
                "options": [
                    "Wir kaufen am Samstag ein.",
                    "Wir einkaufen am Samstag.",
                    "Wir kaufen ein am Samstag.",
                    "Am Samstag wir kaufen ein."
                ],
                "correct": 0,
                "answer_de": "Wir kaufen am Samstag ein.",
                "answer_ru": "Мы делаем покупки в субботу."
            },
            {
                "prompt": "Выбери правильный порядок слов.",
                "question_de": "Она берет ребенка с собой.",
                "options": [
                    "Sie nimmt das Kind mit.",
                    "Sie mitnimmt das Kind.",
                    "Sie nimmt mit das Kind.",
                    "Mit nimmt sie das Kind."
                ],
                "correct": 0,
                "answer_de": "Sie nimmt das Kind mit.",
                "answer_ru": "Она берет ребенка с собой."
            },
            {
                "prompt": "Выбери правильное предложение.",
                "question_de": "Ты открываешь окно.",
                "options": [
                    "Du machst das Fenster auf.",
                    "Du aufmachst das Fenster.",
                    "Du machst auf das Fenster.",
                    "Machst du das Fenster auf."
                ],
                "correct": 0,
                "answer_de": "Du machst das Fenster auf.",
                "answer_ru": "Ты открываешь окно."
            }
        ]
    },

    # 14. множественное число существительных
    {
        "id": 14,
        "level": "A1",
        "title": "Множественное число существительных",
        "description": (
            "У существительных в немецком есть формы единственного и множественного числа. "
            "Общего правила нет, формы нужно запоминать вместе со словом.\n\n"
            "Частые окончания: -e, -er, -en, -s.\n"
            "Иногда изменяется корневая гласная: das Buch – die Bücher."
        ),
        "examples": [
            {"de": "Der Tisch – die Tische.", "ru": "Стол – столы."},
            {"de": "Die Frau – die Frauen.", "ru": "Женщина – женщины."},
            {"de": "Das Kind – die Kinder.", "ru": "Ребенок – дети."},
            {"de": "Das Buch – die Bücher.", "ru": "Книга – книги."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильную форму множественного числа.",
                "question_de": "der Tisch",
                "options": ["die Tischs", "die Tische", "die Tisch", "die Tischern"],
                "correct": 1,
                "answer_de": "die Tische",
                "answer_ru": "столы"
            },
            {
                "prompt": "Выбери правильную форму множественного числа.",
                "question_de": "die Frau",
                "options": ["die Fraus", "die Frau", "die Frauen", "die Frauenen"],
                "correct": 2,
                "answer_de": "die Frauen",
                "answer_ru": "женщины"
            },
            {
                "prompt": "Выбери правильную форму множественного числа.",
                "question_de": "das Kind",
                "options": ["die Kinder", "die Kinds", "die Kinden", "die Kinderen"],
                "correct": 0,
                "answer_de": "die Kinder",
                "answer_ru": "дети"
            },
            {
                "prompt": "Выбери правильную форму множественного числа.",
                "question_de": "das Buch",
                "options": ["die Bucher", "die Bücher", "die Buchs", "die Büchern"],
                "correct": 1,
                "answer_de": "die Bücher",
                "answer_ru": "книги"
            },
            {
                "prompt": "Выбери правильную форму множественного числа.",
                "question_de": "die Lampe",
                "options": ["die Lampes", "die Lampen", "die Lampe", "die Lämpen"],
                "correct": 1,
                "answer_de": "die Lampen",
                "answer_ru": "лампы"
            }
        ]
    },

    # 15. конструкция es gibt
    {
        "id": 15,
        "level": "A1",
        "title": "Конструкция es gibt",
        "description": (
            "Конструкция \"es gibt\" означает \"есть, имеется\" и используется, чтобы сказать, что что-то существует.\n\n"
            "В единственном и множественном числе форма одинаковая: "
            "es gibt ein Haus, es gibt viele Häuser.\n"
            "Часто используется с Akkusativ."
        ),
        "examples": [
            {"de": "Es gibt einen Park in der Stadt.", "ru": "В городе есть парк."},
            {"de": "Es gibt viele Restaurants hier.", "ru": "Здесь много ресторанов."},
            {"de": "Es gibt ein Problem.", "ru": "Есть проблема."},
            {"de": "Es gibt keinen Aufzug.", "ru": "Лифта нет."}
        ],
        "questions": [
            {
                "prompt": "Выбери правильное предложение с es gibt.",
                "question_de": "В городе есть парк.",
                "options": [
                    "Es gibt einen Park in der Stadt.",
                    "Es ist einen Park in der Stadt.",
                    "Es hat einen Park in der Stadt.",
                    "Es sind einen Park in der Stadt."
                ],
                "correct": 0,
                "answer_de": "Es gibt einen Park in der Stadt.",
                "answer_ru": "В городе есть парк."
            },
            {
                "prompt": "Выбери правильное предложение с es gibt.",
                "question_de": "Здесь есть много кафе.",
                "options": [
                    "Es gibt viele Cafés hier.",
                    "Es sind viele Cafés здесь.",
                    "Es hat viele Cafés здесь.",
                    "Es gibt viel Café hier."
                ],
                "correct": 0,
                "answer_de": "Es gibt viele Cafés hier.",
                "answer_ru": "Здесь есть много кафе."
            },
            {
                "prompt": "Выбери правильное предложение с es gibt.",
                "question_de": "Есть проблема.",
                "options": [
                    "Es gibt ein Problem.",
                    "Es ist ein Problem.",
                    "Es hat ein Problem.",
                    "Es gibt einen Problem."
                ],
                "correct": 0,
                "answer_de": "Es gibt ein Problem.",
                "answer_ru": "Есть проблема."
            },
            {
                "prompt": "Выбери правильное предложение с es gibt.",
                "question_de": "Нет лифта.",
                "options": [
                    "Es gibt kein Aufzug.",
                    "Es gibt keinen Aufzug.",
                    "Es gibt keine Aufzug.",
                    "Es gibt nicht Aufzug."
                ],
                "correct": 1,
                "answer_de": "Es gibt keinen Aufzug.",
                "answer_ru": "Лифта нет."
            },
            {
                "prompt": "Выбери правильное предложение с es gibt.",
                "question_de": "В доме есть три комнаты.",
                "options": [
                    "Es gibt drei Zimmer im Haus.",
                    "Es sind drei Zimmer im Haus.",
                    "Es hat drei Zimmer im Haus.",
                    "Es gibt drei Zimmer in dem Haus nicht."
                ],
                "correct": 0,
                "answer_de": "Es gibt drei Zimmer im Haus.",
                "answer_ru": "В доме есть три комнаты."
            }
        ]
    },
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
# ЗАГРУЗКА СЛОВ
# ==========================

def load_words(path: str = "words.json") -> None:
    """Загружаем слова из JSON и автоматически присваиваем темы."""
    global WORDS, WORDS_BY_TOPIC

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Файл {path} не найден. Положи words.json рядом с main.py")

    with file_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    WORDS = []
    WORDS_BY_TOPIC = defaultdict(list)

    for idx, raw in enumerate(data):
        ru = raw["ru"].lower()
        topic = classify_topic(ru)

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

    WORDS_BY_TOPIC[TOPIC_ALL] = list(range(len(WORDS)))
    print(f"Загружено слов: {len(WORDS)}")


def classify_topic(ru: str) -> str:
    """Очень грубое распределение слов по темам на основе русского перевода."""
    r = ru.lower()

    greet_kw = [
        "привет", "добрый день", "добрый вечер", "доброе утро",
        "доброй ночи", "до свидания", "как дела", "спасибо",
        "пожалуйста", "очень хорошо", "не очень хорошо", "извините",
        "мне жаль", "окей", "верно", "правильно", "да", "нет",
    ]
    if any(k in r for k in greet_kw):
        return TOPIC_GREETINGS

    personal_kw = [
        "имя", "фамилия", "адрес", "улица", "номер дома",
        "почтовый индекс", "место проживания", "номер телефона",
        "электронный адрес", "подпись", "возраст", "год рождения",
        "год", "семейное положение", "я есть", "меня зовут", "я из",
    ]
    if any(k in r for k in personal_kw):
        return TOPIC_PERSONAL

    family_kw = [
        "семья", "мать", "отец", "сын", "дочь", "бабушка",
        "дед", "дедушка", "внук", "внучка", "брат", "сестра",
        "тетя", "дядя", "подруга", "друг", "женат", "замужем",
        "разведен", "вдовец", "одинокий родитель",
    ]
    if any(k in r for k in family_kw):
        return TOPIC_FAMILY

    body_kw = [
        "голова", "лицо", "глаз", "бровь", "нос", "рот", "зуб",
        "зубы", "ухо", "волос", "волосы", "шея", "плечо", "рука",
        "кисть", "палец", "грудь", "спина", "живот", "нога",
        "стопа", "колено", "кость", "кровь", "печень", "легкое",
        "мышца", "здоровье", "здоровый", "больной", "усталый",
        "уставший", "больница", "простуда", "грипп", "температура",
        "таблетка", "лекарство", "мазь", "повязка",
    ]
    if any(k in r for k in body_kw):
        return TOPIC_BODY

    emo_kw = [
        "счастливый", "грустный", "злой", "спокойный", "нервный",
        "расслабленный", "гордый", "застенчивый", "дружелюбный",
        "готовый помочь", "вежливый", "невежливый", "странный",
        "смешной", "серьезный", "скучный", "захватывающий",
        "интересный", "важный", "честный", "ленивый", "трудолюбивый",
        "смелый", "трусливый", "умный", "глупый", "наглый",
        "терпеливый", "нетерпеливый", "симпатичный", "неприятный",
        "с чувством юмора", "успешный", "любопытный", "медленный",
        "быстрый", "сильный", "злость", "радость", "страх",
        "смелость", "сюрприз", "разочарование", "уважение",
        "сомнение", "надежда", "терпение",
    ]
    if any(k in r for k in emo_kw):
        return TOPIC_EMOTIONS

    jobs_kw = [
        "врач", "учитель", "инженер", "повар", "медбрат", "медсестра",
        "таксист", "продавец", "продавщица", "парикмахер", "певец",
        "певица", "официант", "актриса", "актер", "электронщик",
        "домохозяин", "домохозяйка", "полицейский", "студент",
        "студентка", "работа", "профессия", "начальник",
        "начальница", "офис", "фирма", "заявление на работу",
        "собеседование", "рабочее время", "перерыв",
        "зарплата", "оклад", "полный рабочий день",
        "неполный рабочий день", "команда", "совещание",
        "шеф повар", "владелец", "сотрудник", "контракт",
        "оптик", "пекарь", "мясник", "механик", "электрик",
        "маляр", "портной", "химчистка", "салон красоты",
    ]
    if any(k in r for k in jobs_kw):
        return TOPIC_JOBS

    school_kw = [
        "школа", "школьник", "школьница", "класс", "урок",
        "домашнее задание", "экзамен", "тест", "повторять",
        "объяснять", "понимать", "курс", "учиться", "занятие",
        "университет",
    ]
    if any(k in r for k in school_kw):
        return TOPIC_SCHOOL

    hobby_kw = [
        "спорт", "тренировка", "играть", "игрок", "велосипед",
        "команда", "музыка", "слушать", "танцевать", "печь",
        "фотографировать", "пианино", "рисовать", "шить", "плавать",
        "петь", "гитара", "видео", "хобби", "фильм", "серия", "сериал",
    ]
    if any(k in r for k in hobby_kw):
        return TOPIC_HOBBY

    color_kw = [
        "красный", "синий", "зеленый", "желтый", "черный", "белый",
        "серый", "коричневый", "оранжевый", "фиолетовый", "розовый",
        "ноль", "один", "два", "три", "четыре", "пять", "шесть",
        "семь", "восемь", "девять", "десять", "одиннадцать",
        "двенадцать", "двадцать", "тридцать", "сорок", "пятьдесят",
        "шестдесят", "семьдесят", "восемьдесят", "девяносто", "сто",
    ]
    if any(k in r for k in color_kw):
        return TOPIC_COLORS_NUM

    clothes_kw = [
        "рубашка", "штаны", "джинсы", "футболка", "свитер",
        "куртка", "пальто", "блузка", "юбка", "платье", "обувь",
        "ботинок", "носки", "сапоги", "ремень", "шляпа", "шапка",
        "шарф", "перчатки", "трусы", "лифчик", "костюм", "одежда",
        "мода", "ткань", "пуговица", "кнопка", "молния", "размер",
    ]
    if any(k in r for k in clothes_kw):
        return TOPIC_CLOTHES

    animals_kw = [
        "собака", "кошка", "птица", "лошадь", "корова", "свинья",
        "овца", "мышь", "медведь", "лев", "змея", "тигр", "заяц",
        "обезьяна", "верблюд", "волк", "лиса", "петух", "утка", "рыба",
    ]
    if any(k in r for k in animals_kw):
        return TOPIC_ANIMALS

    home_kw = [
        "дом", "квартира", "комната", "гостиная", "спальня",
        "кухня", "ванная", "туалет", "коридор", "балкон", "сад",
        "окно", "дверь", "стол", "стул", "кровать", "шкаф", "лампа",
        "ковер", "диван", "зеркало", "штора", "стена", "пол",
        "потолок", "душ", "ванна", "вход",
    ]
    if any(k in r for k in home_kw):
        return TOPIC_HOME

    tools_kw = [
        "пылесос", "метла", "ведро", "губка", "тряпка", "розетка",
        "лампочка", "микроволновка", "чайник электрический",
        "мусорный пакет", "мусорный бак", "мусор", "молоток", "гвоздь",
        "винт", "отвертка", "дрель", "пила", "плоскогубцы", "шланг",
        "инструмент", "сковорода", "кастрюля", "плита", "духовка",
    ]
    if any(k in r for k in tools_kw):
        return TOPIC_TOOLS

    it_kw = [
        "компьютер", "ноутбук", "мышь", "клавиатура", "экран",
        "монитор", "файл", "папка", "сохранять", "удалять",
        "пароль", "входить", "выходить", "программа", "приложение",
        "скачивать", "загружать", "принтер", "печатать", "интернет",
        "вай-фай",
    ]
    if any(k in r for k in it_kw):
        return TOPIC_IT

    city_kw = [
        "город", "деревня", "улица", "площадь", "парк", "мост",
        "вокзал", "аэропорт", "остановка", "метро",
        "городская электричка", "поезд", "автобус", "такси",
        "перекресток", "светофор", "аптека", "пекарня", "банк",
        "почта", "полиция", "детская площадка", "кинотеатр",
        "театр", "музей", "порт", "парковка", "рынок",
        "окрестность", "район", "туннель", "пляж",
    ]
    if any(k in r for k in city_kw):
        return TOPIC_CITY

    weather_kw = [
        "погода", "весна", "лето", "осень", "зима", "тепло", "холодно",
        "пасмурно", "идет дождь", "идет снег", "светит солнце",
        "градус", "температура", "снег", "дождь", "ветер",
        "туман", "небо", "облако", "радуга", "шторм", "лес", "река",
        "ручей", "холм", "луг", "поле", "скала", "остров", "море",
        "озеро", "природа", "земля", "климат",
    ]
    if any(k in r for k in weather_kw):
        return TOPIC_WEATHER

    food_kw = [
        "кофе", "чай", "молоко", "вода", "сок", "пиво", "хлеб",
        "булочка", "круассан", "яйцо", "яблоко", "груша", "фрукты",
        "мюсли", "йогурт", "торт", "колбаса", "сыр", "картошка",
        "ветчина", "салат", "помидор", "сливки", "банан", "супермаркет",
        "продукт питания", "свежий", "вкусный", "овощи", "мясо",
        "напиток", "десерт", "еда", "любимая еда", "рис", "шоколад",
        "мороженое", "суп", "ужин", "обед", "масло", "рыба", "счет",
        "брать", "покупать", "закупаться", "евро", "цент", "клиент",
        "клиентка", "пакет", "покупка", "банка", "бутылка", "стаканчик",
        "грамм", "килограмм", "литр", "продукт", "доставка", "заказ",
        "скидка", "сервис",
    ]
    if any(k in r for k in food_kw):
        return TOPIC_FOOD

    time_kw = [
        "понедельник", "вторник", "среда", "четверг", "пятница",
        "суббота", "воскресенье", "утро", "вечер", "ночь",
        "первая половина дня", "вторая половина дня", "полдень",
        "неделя", "месяц", "март", "апрель", "май", "июнь", "июль",
        "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
        "время", "который час", "сегодня", "завтра", "час",
    ]
    if any(k in r for k in time_kw):
        return TOPIC_TIME

    objects_kw = [
        "книга", "тетрадь", "бумага", "карандаш", "ручка", "линейка",
        "камера", "принтер", "телефон", "сумка", "рюкзак", "кошелек",
        "ключ", "клей", "ножницы", "зонт", "очки", "зажигалка",
        "газета", "чашка", "чемодан", "почтовая марка", "слово",
        "предложение", "текст", "ошибка", "вопрос", "ответ", "почта",
        "балкон", "вход",
    ]
    if any(k in r for k in objects_kw):
        return TOPIC_OBJECTS

    first_word = r.split()[0]
    if first_word.endswith("ть") or first_word.endswith("ться"):
        return TOPIC_VERBS

    abstract_kw = [
        "идея", "мечта", "желание", "возможность", "проблема",
        "решение", "будущее", "прошлое", "настоящее", "страница",
        "сторона", "начало", "конец", "середина", "причина", "опыт",
        "помощь", "цель",
    ]
    if any(k in r for k in abstract_kw):
        return TOPIC_ABSTRACT

    return TOPIC_DICT

# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ СЛОВ
# ==========================

def get_user_words(uid: int) -> List[int]:
    state = user_state[uid]
    topic = state["topic"]
    if topic not in WORDS_BY_TOPIC or topic == TOPIC_ALL:
        return WORDS_BY_TOPIC[TOPIC_ALL]
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
    """Строим клавиатуру с 4 вариантами ответа."""
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
    """Отправляем пользователю новое слово для тренировки."""
    state = user_state[user_id]
    if state["remaining"] is None:
        reset_progress(user_id)

    if not state["remaining"]:
        await bot.send_message(
            chat_id,
            "Ты уже прошел все слова в этой теме.\n"
            "Напиши /next чтобы начать новый круг или выбери другую тему через /themes.",
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
                    text="📘 Грамматика A1",
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

    # Закрытый доступ
    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer(
            "Этот бот с закрытым доступом.\n"
            "Напиши команду /access чтобы отправить запрос администратору."
        )
        return

    total_words = len(WORDS)
    used_topics = {w["topic"] for w in WORDS}
    total_topics = len(used_topics)

    text = (
        "🎓 *Willkommen. Добро пожаловать в бота по немецкому языку*\n\n"
        "Этот бот помогает учить немецкие слова и грамматику.\n\n"
        "📚 Что умеет бот:\n"
        "• Учить слова по темам\n"
        "• Давать тесты с 4 вариантами ответа\n"
        "• Показывать транскрипцию и перевод\n"
        "• Объяснять грамматику уровня A1\n"
        "• Давать практические упражнения по правилам\n\n"
        f"Сейчас в базе *{total_words}* слов.\n"
        f"Тем по словам: *{total_topics}*.\n\n"
        "⚙ Режимы тренировки слов:\n"
        "• 🇩🇪 → 🇷🇺 перевод немецкого слова\n"
        "• 🇷🇺 → 🇩🇪 перевод русского слова\n\n"
        "📌 Основные команды:\n"
        "• /next - следующее слово\n"
        "• /themes - выбрать тему слов\n"
        "• /mode - выбрать направление перевода\n"
        "• /grammar - грамматика уровня A1\n\n"
        "👇 Выбери, с чего начать:"
    )

    kb = build_main_menu_keyboard()
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

    # Сброс прогресса по словам, чтобы /next сразу работал
    reset_progress(uid)


@dp.message(Command("access"))
async def cmd_access(message: Message) -> None:
    uid = message.from_user.id

    if uid == ADMIN_ID or uid in allowed_users:
        await message.answer(
            "У тебя уже есть доступ к боту.\n"
            "Можешь пользоваться командами как обычно."
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
            "Подожди, пока он его одобрит."
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
    await message.answer("Выбери тему для изучения.", reply_markup=kb)


@dp.message(Command("mode"))
async def cmd_mode(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа. Напиши /access для запроса.")
        return

    kb = build_mode_keyboard()
    await message.answer("Выбери направление перевода.", reply_markup=kb)


@dp.message(Command("grammar"))
async def cmd_grammar(message: Message) -> None:
    uid = message.from_user.id

    if uid != ADMIN_ID and uid not in allowed_users:
        await message.answer("Нет доступа. Напиши /access для запроса.")
        return

    if not GRAMMAR_RULES:
        await message.answer(
            "Раздел грамматики пока не настроен.\n"
            "Добавь правила в список GRAMMAR_RULES в main.py."
        )
        return

    kb = build_grammar_keyboard()
    await message.answer("Выбери грамматическое правило уровня A1:", reply_markup=kb)

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

    try:
        await bot.send_message(
            user_id,
            "✅ Доступ одобрен.\n"
            "Теперь ты можешь пользоваться ботом.\n"
            "Напиши /start чтобы начать."
        )
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
        "Выбери правильный перевод.\n\n"
        "Чтобы получить следующее слово, можешь нажать на вариант ответа или команду /next."
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
            "Добавь правила в список GRAMMAR_RULES в main.py."
        )
        return

    kb = build_grammar_keyboard()
    await callback.message.answer("Выбери грамматическое правило уровня A1:", reply_markup=kb)


@dp.callback_query(F.data.startswith("mode|"))
async def cb_mode(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if uid != ADMIN_ID and uid not in allowed_users:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    _, mode = callback.data.split("|", maxsplit=1)
    user_state[uid]["mode"] = mode
    if mode == "de_ru":
        txt = "Режим установлен: 🇩🇪 → 🇷🇺."
    else:
        txt = "Режим установлен: 🇷🇺 → 🇩🇪."
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

    if is_correct:
        state["correct"] += 1
        if mode == "de_ru":
            text = f'✅ Правильно.\n{w["de"]} [{w["tr"]}] - {w["ru"]}'
        else:
            text = f'✅ Правильно.\n{w["ru"]} - {w["de"]} [{w["tr"]}]'
    else:
        state["wrong"] += 1
        if mode == "de_ru":
            text = f'❌ Неправильно.\nПравильный ответ:\n{w["de"]} [{w["tr"]}] - {w["ru"]}'
        else:
            text = f'❌ Неправильно.\nПравильный ответ:\n{w["ru"]} - {w["de"]} [{w["tr"]}]'

    finished_now = not state["remaining"]

    if finished_now:
        text += (
            "\n\nТы прошел все слова в этой теме.\n"
            f'✅ Правильных ответов: {state["correct"]}\n'
            f'❌ Ошибок: {state["wrong"]}\n\n'
            "Чтобы начать круг заново, набери /next или выбери другую тему через /themes."
        )

    try:
        await callback.message.edit_text(text)
    except Exception:
        await callback.message.answer(text)

    await callback.answer()

    if not finished_now:
        await send_new_word(uid, callback.message.chat.id)


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

    # Сбрасываем статистику по этому правилу
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
            f"❌ Ошибок: {total_wrong}\n\n"
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
