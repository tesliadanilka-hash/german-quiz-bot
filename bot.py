import asyncio
import json
import random
from typing import List, Dict

from aiogram import Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ВСТАВЬ СВОЙ ТОКЕН СЮДА
TOKEN = "8583421204:AAHB_2Y8RjDQHDQLcqDLJkYfiP6oBqq3SyE"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Загружаем слова из внешнего файла words.json
# Формат записи:
# {"de": "...", "tr": "...", "ru": "..."}
with open("words.json", "r", encoding="utf-8") as f:
    WORDS: List[Dict[str, str]] = json.load(f)

TOTAL_WORDS = len(WORDS)

# Темы - названия и список немецких слов, которые к ним относятся
TOPIC_WORDS_RAW: Dict[str, List[str]] = {
    "greetings": [
        "Hallo", "Guten Tag", "Guten Abend", "Guten Morgen", "Gute Nacht",
        "Tschüs", "Auf Wiedersehen", "Wie geht’s?", "Wie geht’s dir?",
        "Wie geht’s Ihnen?", "Sehr gut", "Gut", "Nicht so gut", "Danke",
        "Wie bitte?", "Noch einmal, bitte", "Genau", "Stimmt", "Okay",
        "Bitte", "Tut mir leid", "Ja", "Nein", "Auch"
    ],
    "personal_data_family": [
        "Ich bin", "Ich heiße", "Mein Name ist", "Das ist", "Wer", "Was",
        "Wo", "Woher", "Wie", "Ich komme aus", "Jetzt", "Hier", "Na klar",
        "Der Name", "Der Vorname", "Der Familienname", "Die Straße",
        "Die Hausnummer", "Die Adresse", "Die Postleitzahl", "Der Wohnort",
        "Die Telefonnummer", "Die Nummer", "Die E-Mail", "Die E-Mail-Adresse",
        "Die Unterschrift", "Die Familie", "Die Mutter", "Der Vater",
        "Der Sohn", "Die Tochter", "Die Geschwister", "Die Großeltern",
        "Der Großvater", "Die Großmutter", "Der Bruder", "Die Schwester",
        "Der Enkel", "Die Enkelин", "Der Mann", "Der Onkel", "Die Tante",
        "Der Cousin", "Die Cousine", "Der Freund", "Die Freundin",
        "Der Kollege", "Die Kollegin", "Verheiratet", "Ledig", "Geschieden",
        "Verwitwet", "Alleinerziehend", "Der Familienstand", "Das Alter",
        "Das Jahr"
    ],
    "jobs_professions": [
        "Der Arzt", "Die Ärztin", "Der Lehrer", "Die Lehrerin",
        "Der Ingenieur", "Die Ingenieurin", "Der Koch", "Die Köchin",
        "Der Krankenpfleger", "Die Krankenpflegerin", "Der Taxifahrer",
        "Die Taxifahrerin", "Der Verkäufer", "Die Verkäuferin",
        "Der Friseur", "Die Friseurin", "Der Sänger", "Die Sängerin",
        "Der Kellner", "Die Kellnerin", "Der Schauspieler",
        "Die Schauspielerin", "Der Elektroniker", "Die Elektronikerin",
        "Der Fotograf", "Die Fotografin", "Der Hausmann", "Die Hausfrau",
        "Der Polizist", "Die Polizistin", "Der Student", "Die Studentin"
    ],
    "school_things": [
        "Das Buch", "Das Heft", "Das Papier", "Der Bleistift",
        "Der Kugelschreiber", "Das Lineal", "Die Kamera", "Der Drucker",
        "Der Laptop", "Das Handy", "Die Tasche", "Der Rucksack",
        "Der Geldbeutel", "Der Schlüssel", "Der Kleber", "Die Schere",
        "Der Schirm", "Die Brille", "Das Feuerzeug", "Die Zeitung",
        "Die Tasse", "Der Koffer"
    ],
    "time_days": [
        "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
        "Samstag", "Sonntag", "Der Morgen", "Der Vormittag", "Der Mittag",
        "Der Nachmittag", "Der Abend", "Die Nacht", "Um", "Von ... bis ...",
        "Vor", "Nach", "Halb", "Das Viertel", "Kurz", "Spät",
        "Wie spät?"
    ],
    "food_shopping": [
        "Der Kaffee", "Der Tee", "Die Milch", "Das Wasser", "Der Saft",
        "Das Bier", "Das Brot", "Das Brötchen", "Das Croissant", "Das Ei",
        "Der Apfel", "Die Birne", "Das Obst", "Das Müsli", "Der Joghurt",
        "Der Kuchen", "Die Wurst", "Der Käse", "Der Einkauf", "Der Euro",
        "Der Cent", "Kostet", "Der Kunde", "Die Kundin", "Die Tüte",
        "Etwas", "Der Dank", "Die Dose", "Der Becher", "Die Flasche",
        "Das Gramm", "Das Kilo", "Das Kilogramm", "Der Liter",
        "Die Kartoffel", "Der Schinken", "Der Salat", "Die Tomate",
        "Die Sahne", "Die Banane", "Der Supermarkt", "Das Lebensmittel",
        "Frisch", "Lecker", "Das Gemüse", "Das Fleisch", "Das Getränk",
        "Der Nachtisch", "Das Essen", "Das Lieblingsessen", "Der Reis",
        "Die Schokolade", "Das Eis", "Die Suppe", "Das Abendessen",
        "Das Mittagessen", "Die Butter", "Der Fisch", "Die Rechnung",
        "Nehmen", "Mit", "Ohne", "Vegan", "Vegetarisch", "Kaufen",
        "Einkaufen"
    ],
    "city_places_weather": [
        "Das Krankenhaus", "Der Laden", "Das Restaurant", "Der Baum",
        "Die Blume", "Die Sonne", "Der Satz", "Der Text", "Der Fehler",
        "Die Frage", "Die Antwort", "Die Zeit", "Der Deutschkurs",
        "Die Briefmarke", "Geöffnet", "Geschlossen", "Zu Hause",
        "Im Moment", "Scheinen", "Bewölkt", "Regnen", "Vielleicht",
        "Warm", "Morgen", "Das Wetter", "Schneien", "Kalt", "Der Frühling",
        "Der Sommer", "Der Herbst", "Der Winter", "Das Grad", "Doch",
        "Es ist bewölkt", "Es regnet", "Es schneit", "Die Sonne scheint",
        "Es ist warm", "Es ist kalt", "Der März", "Der April", "Der Mai",
        "Der Juni", "Der Juli", "Der August", "Der September",
        "Der Oktober", "Der November", "Der Dezember", "Der Monat",
        "Die Temperatur"
    ],
    "home_daily": [
        "Die Wohnung", "Aufräumen", "Putzen", "Heute", "Rausgehen",
        "Bleiben", "Abholen", "Spazieren gehen", "Die Stunde",
        "Aufstehen", "Duschen", "Frühstücken", "Anrufen", "Der Tag",
        "Schlafen", "Dann", "Danach"
    ],
    "free_time_hobby": [
        "Die Hilfe", "Treffen", "Allein", "Das Internet",
        "Im Internet surfen", "Lesen", "Fernsehen", "Zuerst", "Schön",
        "Schlecht", "Die Woche", "Der Geburtstag", "Doof", "Geben",
        "Der Quatsch", "Sagen", "Glauben", "Hassen", "Lieben", "Wichtig",
        "Der Kurs", "Man", "Der Verein", "Spielen", "Das Training",
        "Schauen", "Zweimal", "Pro", "Die Serie", "Der Spieler",
        "Die Spielerin", "Der Trainer", "Die Trainerin", "Können",
        "Bald", "Die Mannschaft", "Die Musik", "Hören", "Tanzen",
        "Backen", "Fotografieren", "Das Klavier", "Malen", "Nähen",
        "Schwimmen", "Singen", "Die Gitarre", "Das Video", "Das Hobby",
        "Der Film", "Das Fahrrad", "Das Rad", "Rad fahren", "Fahren",
        "Das Auto", "Rechnen", "Das Spiel", "Gewinnen", "Trainieren",
        "Wollen", "Werden"
    ],
    "plans_travel": [
        "Der Urlaub", "Der Führerschein", "Reisen", "Heiraten", "Der Plan",
        "Die Freizeit", "Die Information", "Der Jugendliche",
        "Die Jugendliche", "Manchmal", "Online", "Viel", "Wenig", "Jed-"
    ],
    "verbs_basic": [
        "Sein", "Haben", "Wohnen", "Leben", "Sprechen", "Lernen",
        "Studieren", "Arbeiten", "Arbeitslos sein", "Essen", "Kochen",
        "Suchen", "Gehen", "Telefonieren", "Denken", "Machen",
        "Buchstabieren", "Mögen", "Möchten", "Brauchen"
    ]
}

# Привязка тем к индексам в WORDS
TOPICS: Dict[str, List[int]] = {}
for topic_key, words_list in TOPIC_WORDS_RAW.items():
    indices = [
        i for i, w in enumerate(WORDS)
        if w.get("de") in words_list
    ]
    if indices:
        TOPICS[topic_key] = indices

# Названия тем для пользователя
TOPIC_TITLES: Dict[str, str] = {
    "greetings": "Приветствия и базовые фразы",
    "personal_data_family": "Личные данные и семья",
    "jobs_professions": "Профессии",
    "school_things": "Учеба и предметы",
    "time_days": "Дни недели и время",
    "food_shopping": "Еда и покупки",
    "city_places_weather": "Город, места и погода",
    "home_daily": "Дом и повседневность",
    "free_time_hobby": "Досуг и хобби",
    "plans_travel": "Планы и путешествия",
    "verbs_basic": "Базовые глаголы"
}

# Активная тема и режим для каждого чата
# режим: "de_ru" или "ru_de"
USER_TOPIC: Dict[int, str] = {}
USER_MODE: Dict[int, str] = {}  # по умолчанию de_ru


def get_indices_for_chat(chat_id: int) -> List[int]:
    """
    Возвращаем список индексов слов для этого чата.
    Если тема не выбрана, используем все слова.
    """
    topic_key = USER_TOPIC.get(chat_id)
    if topic_key and topic_key in TOPICS:
        return TOPICS[topic_key]
    return list(range(TOTAL_WORDS))


def get_mode_for_chat(chat_id: int) -> str:
    """
    Возвращаем режим для этого чата.
    """
    return USER_MODE.get(chat_id, "de_ru")


def make_question(mode: str, indices_pool: List[int]):
    """
    Выбираем одно слово и 3 неправильных варианта из заданного списка индексов.
    mode:
      "de_ru" - показываем немецкое слово, варианты на русском
      "ru_de" - показываем русское слово, варианты на немецком
    """
    if not indices_pool:
        indices_pool = list(range(TOTAL_WORDS))

    correct_idx = random.choice(indices_pool)
    correct_word = WORDS[correct_idx]

    other_indices = [i for i in indices_pool if i != correct_idx]

    # Если в теме меньше 4 слов, добираем из общего списка
    if len(other_indices) < 3:
        extra = [i for i in range(TOTAL_WORDS)
                 if i != correct_idx and i not in other_indices]
        need = 3 - len(other_indices)
        other_indices.extend(random.sample(extra, k=need))

    wrong_indices = random.sample(other_indices, k=3)

    option_indices = wrong_indices + [correct_idx]
    random.shuffle(option_indices)

    options = [WORDS[i] for i in option_indices]

    if mode == "de_ru":
        question_text = (
            f"🇩🇪 {correct_word['de']} [{correct_word['tr']}]\n"
            "Выбери правильный перевод на русский:"
        )
    else:
        question_text = (
            f"🇷🇺 {correct_word['ru']}\n"
            "Выбери правильный перевод на немецкий:"
        )

    return question_text, options, correct_idx, option_indices


async def send_new_word(message: Message):
    """
    Отправляем новое слово с 4 вариантами.
    """
    chat_id = message.chat.id
    indices_pool = get_indices_for_chat(chat_id)
    mode = get_mode_for_chat(chat_id)

    question_text, options, correct_idx, option_indices = make_question(mode, indices_pool)

    builder = InlineKeyboardBuilder()

    for idx_global, opt in zip(option_indices, options):
        if mode == "de_ru":
            btn_text = opt["ru"]
        else:
            btn_text = f"{opt['de']} [{opt['tr']}]"

        cb_data = f"answer:{correct_idx}:{idx_global}"
        builder.button(text=btn_text, callback_data=cb_data)

    builder.adjust(2, 2)

    await message.answer(question_text, reply_markup=builder.as_markup())


@dp.message(CommandStart())
async def cmd_start(message: Message):
    total = TOTAL_WORDS
    themes_count = len(TOPICS)

    text = (
        "🇩🇪 Привет! Это бот для изучения немецких слов.\n\n"
        "Как пользоваться:\n"
        "• Я показываю слово и 4 варианта перевода.\n"
        "• Нажми на кнопку с вариантом.\n"
        "• Если ответ неверный, я покажу правильный ответ и сразу дам новое слово.\n"
        "• Если ответ верный, карточка помечается галочкой, а ниже появляется новое слово.\n\n"
        f"Сейчас в базе {total} слов.\n"
        f"Тем: {themes_count}.\n\n"
        "Режимы:\n"
        "• 🇩🇪 → 🇷🇺 немецкое слово и варианты на русском.\n"
        "• 🇷🇺 → 🇩🇪 русское слово и варианты на немецком.\n\n"
        "Команды:\n"
        "/next - следующее слово\n"
        "/themes - выбрать тему слов\n"
        "/mode - выбрать направление перевода\n\n"
        "По умолчанию включен режим 🇩🇪 → 🇷🇺."
    )

    await message.answer(text)
    await send_new_word(message)


@dp.message(Command("next"))
async def cmd_next(message: Message):
    await send_new_word(message)


@dp.message(Command("themes"))
async def cmd_themes(message: Message):
    """
    Показываем список тем с кнопками.
    """
    builder = InlineKeyboardBuilder()
    for key, title in TOPIC_TITLES.items():
        cb_data = f"set_topic:{key}"
        builder.button(text=title, callback_data=cb_data)
    builder.adjust(1)

    await message.answer("Выбери тему для тренировки слов:", reply_markup=builder.as_markup())


@dp.message(Command("mode"))
async def cmd_mode(message: Message):
    """
    Показываем выбор режима перевода.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🇩🇪 слово → 🇷🇺 варианты", callback_data="set_mode:de_ru")
    builder.button(text="🇷🇺 слово → 🇩🇪 варианты", callback_data="set_mode:ru_de")
    builder.adjust(1)

    await message.answer("Выбери направление перевода:", reply_markup=builder.as_markup())


@dp.callback_query(lambda c: c.data and c.data.startswith("set_topic:"))
async def handle_set_topic(callback: CallbackQuery):
    """
    Устанавливаем тему по нажатию на кнопку.
    """
    data = callback.data.split(":", 1)
    if len(data) != 2:
        await callback.answer("Ошибка данных.")
    else:
        topic_key = data[1]
        chat_id = callback.message.chat.id
        USER_TOPIC[chat_id] = topic_key

        title = TOPIC_TITLES.get(topic_key, topic_key)
        await callback.answer("Тема выбрана")
        await callback.message.answer(
            f"Тема установлена: {title}.\nТеперь я даю слова только из этой темы."
        )
        await send_new_word(callback.message)


@dp.callback_query(lambda c: c.data and c.data.startswith("set_mode:"))
async def handle_set_mode(callback: CallbackQuery):
    """
    Устанавливаем режим перевода по нажатию на кнопку.
    """
    data = callback.data.split(":", 1)
    if len(data) != 2:
        await callback.answer("Ошибка данных.")
        return

    mode = data[1]
    chat_id = callback.message.chat.id
    USER_MODE[chat_id] = mode

    if mode == "de_ru":
        txt = "Режим установлен: 🇩🇪 слово → 🇷🇺 варианты."
    else:
        txt = "Режим установлен: 🇷🇺 слово → 🇩🇪 варианты."

    await callback.answer("Режим изменен")
    await callback.message.answer(txt)
    await send_new_word(callback.message)


@dp.callback_query(lambda c: c.data and c.data.startswith("answer:"))
async def handle_answer(callback: CallbackQuery):
    """
    Обработка ответа по кнопке.
    Формат callback_data: "answer:correct_idx:chosen_idx"
    """
    data = callback.data.split(":")
    if len(data) != 3:
        await callback.answer("Ошибка данных.")
        return

    correct_idx = int(data[1])
    chosen_idx = int(data[2])

    original_text = callback.message.text or ""

    # убираем кнопки у старого сообщения
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except:
        pass

    correct_word = WORDS[correct_idx]

    if chosen_idx == correct_idx:
        # помечаем старое сообщение галочкой и сохраняем вопрос
        try:
            new_text = "✅ Правильно\n" + original_text
            await callback.message.edit_text(new_text)
        except:
            pass

        await callback.answer("✅")
        await send_new_word(callback.message)
    else:
        # помечаем старое сообщение крестиком, показываем правильный ответ и новое слово
        try:
            new_text = "❌ Неправильно\n" + original_text
            await callback.message.edit_text(new_text)
        except:
            pass

        text = (
            "Правильный ответ:\n"
            f"🇩🇪 {correct_word['de']} [{correct_word['tr']}] - {correct_word['ru']}"
        )
        await callback.answer("Неправильно")
        await callback.message.answer(text)
        await send_new_word(callback.message)


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
