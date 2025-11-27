import asyncio
import json
import os
import random
from typing import Dict, List, Any, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =====================================================================
# 1. НАСТРОЙКА БОТА
# =====================================================================

# Лучше храни токен в переменной окружения TELEGRAM_TOKEN
TOKEN = os.getenv("TELEGRAM_TOKEN", "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =====================================================================
# 2. ЗАГРУЗКА ВСЕХ СЛОВ ИЗ words.json
# =====================================================================

WORDS: List[Dict[str, Any]] = []          # список всех слов
TOPICS: Dict[str, List[Dict[str, Any]]] = {}  # тема → список слов


def detect_topic(word: Dict[str, str]) -> str:
    """
    Пытаемся угадать тему по переводу и немецкому слову.
    Если в слове уже есть поле 'topic', оно имеет приоритет.
    """
    if "topic" in word:
        return word["topic"]

    ru = word.get("ru", "").lower()
    de = word.get("de", "").lower()

    # Приветствия и базовые фразы
    if any(x in ru for x in ["привет", "пока", "здравствуйте", "добрый", "как дела", "спасибо", "извините"]):
        return "Приветствия и фразы"

    # Семья
    if any(x in ru for x in ["мать", "отец", "папа", "мама", "сын", "дочь", "брат", "сестра", "семья", "дед", "бабушк"]):
        return "Семья и люди"

    # Время и даты
    if any(x in ru for x in ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье",
                             "день", "ночь", "утро", "вечер", "месяц", "год", "время", "час"]):
        return "Время и даты"

    # Еда и напитки
    if any(x in ru for x in ["еда", "пить", "кофе", "чай", "мясо", "рыба", "сыр", "хлеб", "суп", "фрук", "овощ",
                             "яблоко", "банан", "сок", "пиво", "вода", "торт", "колбаса", "масло", "молоко", "завтрак", "обед", "ужин"]):
        return "Еда и напитки"

    # Магазин и покупки
    if any(x in ru for x in ["магазин", "покупка", "клиент", "супермаркет", "стоить", "счет", "скидка", "цена"]):
        return "Покупки и деньги"

    # Дом и квартира
    if any(x in ru for x in ["квартира", "дом", "комната", "кухня", "ванная", "кровать", "стол", "стул",
                             "шкаф", "окно", "дверь", "сад", "балкон"]):
        return "Дом и квартира"

    # Город и транспорт
    if any(x in ru for x in ["город", "деревня", "улица", "площадь", "вокзал", "остановка", "аэропорт",
                             "автобус", "поезд", "метро", "машина", "велосипед", "такси", "дорога"]):
        return "Город и транспорт"

    # Тело и здоровье
    if any(x in ru for x in ["голова", "рука", "нога", "спина", "живот", "боль", "врач", "больница", "таблет",
                             "здоровье", "простуда", "температура", "лекарство"]):
        return "Тело и здоровье"

    # Профессии и работа
    if any(x in ru for x in ["учитель", "врач", "инженер", "таксист", "повар", "продавец", "полицейский",
                             "работать", "работа", "фирма", "офис", "зарплата"]):
        return "Профессии и работа"

    # Хобби и спорт
    if any(x in ru for x in ["спорт", "музыка", "танцевать", "играть", "тренировка", "хобби", "кино",
                             "фильм", "сериал", "велосипед", "фото", "фотографировать"]):
        return "Хобби и спорт"

    # Погода и природа
    if any(x in ru for x in ["погода", "дождь", "снег", "ветер", "тепло", "холодно", "пасмурно", "солнце",
                             "дерево", "цветок", "лес", "река", "море", "гора"]):
        return "Погода и природа"

    # Прилагательные и характеристики
    if any(x in ru for x in ["глупый", "умный", "добрый", "злой", "важный", "красивый", "плохой",
                             "хороший", "смешной", "серьезный", "быстрый", "медленный"]):
        return "Прилагательные"

    # Абстрактные слова
    if any(x in ru for x in ["идея", "мечта", "желание", "возможность", "проблема", "решение", "опыт",
                             "цель", "прошлое", "будущее", "надежда", "страх"]):
        return "Абстрактные слова"

    # Всё остальное
    return "Общий словарь"


def load_words():
    global WORDS, TOPICS
    with open("words.json", "r", encoding="utf-8") as f:
        WORDS = json.load(f)

    TOPICS = {}
    for w in WORDS:
        topic = detect_topic(w)
        w["topic"] = topic
        TOPICS.setdefault(topic, []).append(w)


# =====================================================================
# 3. СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЕЙ (ПРОСТОЙ ВАРИАНТ В ПАМЯТИ)
# =====================================================================

class Session:
    def __init__(self):
        self.mode: str = "de_ru"   # "de_ru", "ru_de", "mix"
        self.topic: Optional[str] = None  # None = все темы
        self.current_word: Optional[Dict[str, Any]] = None
        self.current_options: List[Dict[str, Any]] = []
        self.last_message_id: Optional[int] = None


SESSIONS: Dict[int, Session] = {}


def get_session(user_id: int) -> Session:
    if user_id not in SESSIONS:
        SESSIONS[user_id] = Session()
    return SESSIONS[user_id]


def get_words_for_topic(topic: Optional[str]) -> List[Dict[str, Any]]:
    if topic is None or topic == "ALL":
        return WORDS
    return TOPICS.get(topic, [])


# =====================================================================
# 4. КЛАВИАТУРЫ
# =====================================================================

def main_menu_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇩🇪 Немецкий → Русский", callback_data="mode:de_ru")
    kb.button(text="🇷🇺 Русский → Немецкий", callback_data="mode:ru_de")
    kb.button(text="🎲 Смешанный режим", callback_data="mode:mix")
    kb.button(text="📚 Выбрать тему", callback_data="choose_topic")
    kb.button(text="▶️ Начать квиз", callback_data="start_quiz")
    kb.adjust(1, 1, 1, 1, 1)
    return kb


def topics_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    topics_sorted = sorted(TOPICS.keys())
    kb.button(text="🌍 Все темы", callback_data="topic:ALL")
    for t in topics_sorted:
        kb.button(text=t, callback_data=f"topic:{t}")
    kb.adjust(1)
    return kb


def options_kb(session: Session, mode: str) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for idx, w in enumerate(session.current_options):
        if mode == "de_ru":
            text = w["ru"]
        else:
            # ru_de
            text = f'{w["de"]} [{w["tr"]}]'
        kb.button(text=text, callback_data=f"answer:{idx}")
    kb.adjust(1)
    return kb


# =====================================================================
# 5. ЛОГИКА ВОПРОСА
# =====================================================================

def pick_question(session: Session):
    # Определяем список слов под выбранную тему
    base_words = get_words_for_topic(session.topic)
    if len(base_words) < 4:
        base_words = WORDS

    correct = random.choice(base_words)

    # подбираем неверные варианты
    others = [w for w in base_words if w is not correct]
    if len(others) < 3:
        others = [w for w in WORDS if w is not correct]

    distractors = random.sample(others, k=3)
    options = distractors + [correct]
    random.shuffle(options)

    session.current_word = correct
    session.current_options = options


# =====================================================================
# 6. ХЕНДЛЕРЫ КОМАНД
# =====================================================================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    session = get_session(user_id)

    total_words = len(WORDS)
    total_topics = len(TOPICS)

    text = (
        "🇩🇪 *Добро пожаловать в бот для тренировки немецких слов!*\n\n"
        "Вот как он работает:\n"
        "• Бот показывает слово и 4 варианта ответа\n"
        "• 1 вариант правильный\n"
        "• Если ты ошибаешься, бот показывает правильный ответ полностью\n"
        "• Если отвечаешь верно, показывает ✅ и сразу даёт следующее слово\n\n"
        f"📚 В словаре сейчас: *{total_words}* слов\n"
        f"📂 Тем: *{total_topics}*\n\n"
        "Выбери режим и тему, потом нажми *▶️ Начать квиз*."
    )

    await message.answer(
        text,
        reply_markup=main_menu_kb().as_markup(),
        parse_mode="Markdown"
    )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "ℹ️ *Помощь по боту*\n\n"
        "1. Используй /start чтобы открыть меню\n"
        "2. Выбери режим:\n"
        "   • 🇩🇪 Немецкий → Русский\n"
        "   • 🇷🇺 Русский → Немецкий\n"
        "   • 🎲 Смешанный режим\n"
        "3. Выбери тему или оставь *Все темы*\n"
        "4. Нажми ▶️ Начать квиз\n\n"
        "При ошибке бот покажет правильный ответ\n"
        "При правильном ответе покажет ✅ и сразу новое слово."
    )
    await message.answer(text, parse_mode="Markdown")


# =====================================================================
# 7. ХЕНДЛЕРЫ КНОПОК МЕНЮ
# =====================================================================

@dp.callback_query(F.data.startswith("mode:"))
async def cb_set_mode(callback: CallbackQuery):
    user_id = callback.from_user.id
    session = get_session(user_id)

    mode = callback.data.split(":", 1)[1]
    session.mode = mode

    if mode == "de_ru":
        text = "Режим: 🇩🇪 Немецкий → 🇷🇺 Русский"
    elif mode == "ru_de":
        text = "Режим: 🇷🇺 Русский → 🇩🇪 Немецкий"
    else:
        text = "Режим: 🎲 Смешанный (оба направления)"

    await callback.answer("Режим обновлён")
    await callback.message.edit_reply_markup(main_menu_kb().as_markup())
    await callback.message.answer(text)


@dp.callback_query(F.data == "choose_topic")
async def cb_choose_topic(callback: CallbackQuery):
    await callback.message.answer(
        "📚 Выбери тему для тренировки:",
        reply_markup=topics_kb().as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("topic:"))
async def cb_set_topic(callback: CallbackQuery):
    user_id = callback.from_user.id
    session = get_session(user_id)

    topic_key = callback.data.split(":", 1)[1]
    if topic_key == "ALL":
        session.topic = None
        text = "Тема: 🌍 Все темы"
    else:
        session.topic = topic_key
        text = f"Тема: {topic_key}"

    await callback.answer("Тема обновлена")
    await callback.message.answer(text)


@dp.callback_query(F.data == "start_quiz")
async def cb_start_quiz(callback: CallbackQuery):
    user_id = callback.from_user.id
    session = get_session(user_id)

    await callback.answer()

    await send_new_question(callback.message, session)


# =====================================================================
# 8. ПОКАЗ ВОПРОСА
# =====================================================================

async def send_new_question(message: Message, session: Session):
    if session.mode == "mix":
        actual_mode = random.choice(["de_ru", "ru_de"])
    else:
        actual_mode = session.mode

    pick_question(session)

    w = session.current_word

    if actual_mode == "de_ru":
        question_text = (
            "🇩🇪 → 🇷🇺\n\n"
            f"Тема: *{w['topic']}*\n"
            f"Слово: *{w['de']}* [{w['tr']}]\n\n"
            "Выбери правильный перевод:"
        )
    else:
        question_text = (
            "🇷🇺 → 🇩🇪\n\n"
            f"Тема: *{w['topic']}*\n"
            f"Слово: *{w['ru']}*\n\n"
            "Выбери правильный перевод:"
        )

    kb = options_kb(session, actual_mode)

    sent = await message.answer(
        question_text,
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

    session.last_message_id = sent.message_id
    # сохраняем фактическое направление для проверки ответа
    session.last_mode = actual_mode  # динамично добавляем поле


# =====================================================================
# 9. ОБРАБОТКА ОТВЕТА ПОЛЬЗОВАТЕЛЯ
# =====================================================================

@dp.callback_query(F.data.startswith("answer:"))
async def cb_answer(callback: CallbackQuery):
    user_id = callback.from_user.id
    session = get_session(user_id)

    # какой вариант выбрали
    try:
        idx = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Ошибка ответа", show_alert=True)
        return

    if not session.current_word or not session.current_options:
        await callback.answer("Вопрос не найден. Нажми /start", show_alert=True)
        return

    chosen = session.current_options[idx]
    correct = session.current_word

    mode = getattr(session, "last_mode", session.mode)

    is_correct = False
    if mode == "de_ru":
        # правильный ответ по русскому переводу
        is_correct = (chosen["ru"] == correct["ru"])
    else:
        # ru_de: правильный по немецкому слову
        is_correct = (chosen["de"] == correct["de"])

    # Убираем клавиатуру у старого вопроса
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if is_correct:
        # Показываем галочку, как ты просил
        await callback.message.answer("✅ Правильно! Следующее слово:")
    else:
        # Показываем полный правильный ответ
        if mode == "de_ru":
            text = (
                "❌ Неправильно.\n\n"
                f"Правильный ответ:\n"
                f"🇩🇪 *{correct['de']}* [{correct['tr']}]\n"
                f"🇷🇺 *{correct['ru']}*"
            )
        else:
            text = (
                "❌ Неправильно.\n\n"
                f"Правильный ответ:\n"
                f"🇷🇺 *{correct['ru']}*\n"
                f"🇩🇪 *{correct['de']}* [{correct['tr']}]"
            )
        await callback.message.answer(text, parse_mode="Markdown")

    await callback.answer()

    # Сразу отправляем новый вопрос
    await send_new_question(callback.message, session)


# =====================================================================
# 10. ЗАПУСК БОТА (LONG POLLING)
# =====================================================================

async def main():
    load_words()
    print(f"Loaded {len(WORDS)} words in {len(TOPICS)} topics.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
