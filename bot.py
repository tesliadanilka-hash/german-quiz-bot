import asyncio
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple

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

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
)

ADMIN_ID = 5319848687

ALLOWED_USERS_FILE = "allowed_users.txt"
USER_STATE_FILE = "user_state.json"
WORDS_FILE = "words.json"
GRAMMAR_FILE = "grammar.json"

if not TOKEN:
    raise RuntimeError(
        "Не найден токен бота. Проверь, что в Render задана переменная BOT_TOKEN."
    )

from aiogram.client.default import DefaultBotProperties

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


# ==========================
# ХРАНИЛИЩЕ ДАННЫХ
# ==========================

allowed_users: List[int] = []
user_state: Dict[str, Any] = {}

WORDS_TOPICS: Dict[str, Dict[str, Any]] = {}
# ключ - topic_id (w0, w1, ...)

GRAMMAR_RULES: List[Dict[str, Any]] = []              # список всех правил
GRAMMAR_LEVELS: Dict[str, set] = defaultdict(set)     # {"A1": {"A1.1", "A1.2"}}
GRAMMAR_TOPICS: Dict[Tuple[str, str], List[int]] = defaultdict(list)
# ("A1", "A1.1") -> [rule_index, rule_index...]

GRAMMAR_TOPIC_ID: Dict[Tuple[str, str], str] = {}
GRAMMAR_TOPIC_FROM_ID: Dict[str, Tuple[str, str]] = {}

# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================


def load_allowed_users() -> None:
    global allowed_users
    allowed_users = []
    path = Path(ALLOWED_USERS_FILE)
    if not path.exists():
        print("allowed_users.txt не найден, создаю пустой файл.")
        path.write_text("", encoding="utf-8")
        return

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                allowed_users.append(int(line))
            except ValueError:
                print(f"Некорректный ID в allowed_users.txt: {line}")

    print(f"Загружено разрешенных пользователей: {len(allowed_users)}")


def save_user_state() -> None:
    try:
        with open(USER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(user_state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка сохранения состояния:", e)


def load_user_state() -> None:
    global user_state
    path = Path(USER_STATE_FILE)
    if not path.exists():
        user_state = {}
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            user_state = json.load(f)
    except Exception:
        user_state = {}


def load_words(path: str = WORDS_FILE) -> None:
    """
    Простая загрузка words.json.
    Ожидается формат: список объектов с ключами
    topic, level, subtopic, words.
    """
    global WORDS_TOPICS
    WORDS_TOPICS.clear()

    file_path = Path(path)
    if not file_path.exists():
        print(f"Файл {path} не найден, раздел слов будет отключен.")
        return

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Ошибка загрузки words.json:", e)
        return

    if not isinstance(data, list):
        print("words.json должен быть списком объектов.")
        return

    for idx, item in enumerate(data):
        topic_id = f"w{idx}"
        WORDS_TOPICS[topic_id] = item

    print(f"Загружено тем словаря: {len(WORDS_TOPICS)}")


def load_grammar(path: str = GRAMMAR_FILE) -> None:
    """
    Поддерживает формат grammar.json, который ты прислал:

    {
      "A1.1": [ {...}, {...} ],
      "A1.2": [ {...} ],
      "A2.1": [ {...} ],
      ...
    }
    """
    global GRAMMAR_RULES, GRAMMAR_LEVELS, GRAMMAR_TOPICS
    global GRAMMAR_TOPIC_ID, GRAMMAR_TOPIC_FROM_ID

    GRAMMAR_RULES.clear()
    GRAMMAR_LEVELS.clear()
    GRAMMAR_TOPICS.clear()
    GRAMMAR_TOPIC_ID.clear()
    GRAMMAR_TOPIC_FROM_ID.clear()

    file_path = Path(path)
    if not file_path.exists():
        print(f"Файл {path} не найден, раздел грамматики будет отключен.")
        return

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print("Ошибка загрузки grammar.json:", e)
        return

    if not isinstance(data, dict):
        print("grammar.json должен быть объектом { 'A1.1': [ ... ] }.")
        return

    rule_counter = 0

    for topic_key, rules in data.items():
        # topic_key типа "A1.1" -> level "A1"
        if "." in topic_key:
            level = topic_key.split(".", 1)[0]
        else:
            level = "A1"

        GRAMMAR_LEVELS[level].add(topic_key)

        if not isinstance(rules, list):
            continue

        for r in rules:
            rule = {
                "id": rule_counter,
                "code": r.get("id", f"rule{rule_counter}"),
                "level": level,
                "topic": topic_key,
                "title": r.get("title", "Без названия"),
                "description": r.get("explanation", "") or r.get("description", ""),
                "examples": r.get("examples", []),
                "exercises": r.get("exercises", []),
            }
            GRAMMAR_RULES.append(rule)
            GRAMMAR_TOPICS[(level, topic_key)].append(rule_counter)
            rule_counter += 1

    # Короткие ID для тем грамматики
    for i, key in enumerate(GRAMMAR_TOPICS.keys()):
        tid = f"g{i}"
        GRAMMAR_TOPIC_ID[key] = tid
        GRAMMAR_TOPIC_FROM_ID[tid] = key

    print(f"Загружено грамматических правил: {len(GRAMMAR_RULES)}")
    print(f"Уровней грамматики: {len(GRAMMAR_LEVELS)}, тем: {len(GRAMMAR_TOPICS)}")


def build_back_to_main_row() -> List[List[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="⬅ В главное меню", callback_data="back_main")]]


def check_access(user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    return user_id in allowed_users


# ==========================
# КЛАВИАТУРЫ
# ==========================


def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="📚 Слова по темам",
                callback_data="menu_words",
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
                text="ℹ О боте",
                callback_data="menu_about",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==========================
# ХЕНДЛЕРЫ
# ==========================


@dp.message(CommandStart())
async def cmd_start(message: Message):
    uid = message.from_user.id
    user_state[str(uid)] = {}
    save_user_state()

    text = (
        "🎓 Willkommen. Добро пожаловать в бота по немецкому языку.\n\n"
        "Этот бот помогает шаг за шагом улучшать твой немецкий через слова, темы и простые упражнения.\n\n"
        "Выбери раздел:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@dp.message(Command("reload"))
async def cmd_reload(message: Message):
    """Перезагрузка файлов words.json и grammar.json вручную."""
    if message.from_user.id != ADMIN_ID:
        return await message.answer("Команда доступна только админу.")

    load_words()
    load_grammar()
    await message.answer("Файлы words.json и grammar.json перезагружены.")


@dp.callback_query(F.data == "back_main")
async def cb_back_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "Главное меню. Выбери раздел:", reply_markup=main_menu_kb()
    )
    await callback.answer()


# --------- О БОТЕ ---------


@dp.callback_query(F.data == "menu_about")
async def cb_menu_about(callback: CallbackQuery):
    text = (
        "ℹ Небольшая справка.\n\n"
        "Бот помогает учить немецкий язык:\n"
        "• Слова по темам.\n"
        "• Грамматические правила с упражнениями.\n\n"
        "Файлы:\n"
        "• words.json - слова.\n"
        "• grammar.json - грамматика.\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=build_back_to_main_row())
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


# --------- СЛОВА (ПРОСТАЯ ВЕРСИЯ) ---------


@dp.callback_query(F.data == "menu_words")
async def cb_menu_words(callback: CallbackQuery):
    uid = callback.from_user.id
    if not check_access(uid):
        return await callback.answer("Нет доступа. Обратись к админу.", show_alert=True)

    if not WORDS_TOPICS:
        text = "Раздел слов пока не настроен. Убедись, что в файле words.json есть темы."
        kb = InlineKeyboardMarkup(inline_keyboard=build_back_to_main_row())
        await callback.message.edit_text(text, reply_markup=kb)
        return await callback.answer()

    buttons = []
    for topic_id, item in WORDS_TOPICS.items():
        title = item.get("topic", "Без темы")
        level = item.get("level", "")
        sub = item.get("subtopic", "")
        btn_text = f"{level} - {title}"
        if sub:
            btn_text += f" / {sub}"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=btn_text,
                    callback_data=f"w_topic|{topic_id}",
                )
            ]
        )

    buttons += build_back_to_main_row()
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выбери тему слов:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("w_topic|"))
async def cb_words_topic(callback: CallbackQuery):
    _, topic_id = callback.data.split("|")
    item = WORDS_TOPICS.get(topic_id)
    if not item:
        await callback.answer("Тема не найдена.", show_alert=True)
        return

    title = item.get("topic", "Без темы")
    level = item.get("level", "")
    sub = item.get("subtopic", "")
    words = item.get("words", [])

    text_lines = [f"📚 {title} ({level})"]
    if sub:
        text_lines.append(sub)
    text_lines.append("")
    if not words:
        text_lines.append("Пока нет слов в этой теме.")
    else:
        text_lines.append("Слова:")
        for w in words[:50]:
            if isinstance(w, dict):
                de = w.get("de") or w.get("word") or ""
                ru = w.get("ru") or w.get("translation") or ""
                text_lines.append(f"• {de} - {ru}")
            else:
                text_lines.append(f"• {w}")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ К темам слов", callback_data="menu_words")],
            *build_back_to_main_row(),
        ]
    )

    await callback.message.edit_text("\n".join(text_lines), reply_markup=kb)
    await callback.answer()


# --------- ГРАММАТИКА ---------


@dp.callback_query(F.data == "menu_grammar")
async def cb_menu_grammar(callback: CallbackQuery):
    uid = callback.from_user.id
    if not check_access(uid):
        return await callback.answer("Нет доступа. Обратись к админу.", show_alert=True)

    if not GRAMMAR_RULES:
        text = (
            "Раздел грамматики пока не настроен. "
            "Убедись, что в файле grammar.json есть правила."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=build_back_to_main_row())
        await callback.message.edit_text(text, reply_markup=kb)
        return await callback.answer()

    buttons = []
    for lvl in sorted(GRAMMAR_LEVELS.keys()):
        count_topics = len(GRAMMAR_LEVELS[lvl])
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"Уровень {lvl} ({count_topics} тем)",
                    callback_data=f"g_lvl|{lvl}",
                )
            ]
        )

    buttons += build_back_to_main_row()
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выбери уровень грамматики:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("g_lvl|"))
async def cb_grammar_level(callback: CallbackQuery):
    uid = callback.from_user.id
    if not check_access(uid):
        return await callback.answer("Нет доступа.", show_alert=True)

    _, level = callback.data.split("|")
    topics = sorted(GRAMMAR_LEVELS[level])

    buttons = []
    for topic in topics:
        tid = GRAMMAR_TOPIC_ID[(level, topic)]
        rules_count = len(GRAMMAR_TOPICS[(level, topic)])
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{topic} ({rules_count} правил)",
                    callback_data=f"g_topic|{tid}",
                )
            ]
        )

    buttons += build_back_to_main_row()
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"Уровень {level}. Выбери тему:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("g_topic|"))
async def cb_grammar_topic(callback: CallbackQuery):
    uid = callback.from_user.id
    if not check_access(uid):
        return await callback.answer("Нет доступа.", show_alert=True)

    _, tid = callback.data.split("|")
    if tid not in GRAMMAR_TOPIC_FROM_ID:
        return await callback.answer("Тема не найдена.", show_alert=True)

    level, topic = GRAMMAR_TOPIC_FROM_ID[tid]
    rule_ids = GRAMMAR_TOPICS[(level, topic)]

    buttons = []
    for rid in rule_ids:
        rule = GRAMMAR_RULES[rid]
        buttons.append(
            [
                InlineKeyboardButton(
                    text=rule["title"],
                    callback_data=f"g_rule|{rid}",
                )
            ]
        )

    buttons += build_back_to_main_row()
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"Тема {topic}. Выбери правило:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("g_rule|"))
async def cb_grammar_rule(callback: CallbackQuery):
    uid = callback.from_user.id
    if not check_access(uid):
        return await callback.answer("Нет доступа.", show_alert=True)

    _, rid = callback.data.split("|")
    try:
        rid_int = int(rid)
    except ValueError:
        return await callback.answer("Ошибка идентификатора правила.", show_alert=True)

    if rid_int < 0 or rid_int >= len(GRAMMAR_RULES):
        return await callback.answer("Правило не найдено.", show_alert=True)

    rule = GRAMMAR_RULES[rid_int]

    text_parts = [f"📘 <b>{rule['title']}</b>", ""]

    if rule.get("description"):
        text_parts.append(rule["description"])
        text_parts.append("")

    if rule.get("examples"):
        text_parts.append("Примеры:")
        for ex in rule["examples"]:
            if isinstance(ex, dict):
                de = ex.get("de", "")
                ru = ex.get("ru", "")
                if de:
                    text_parts.append(f"• {de}")
                if ru:
                    text_parts.append(f"  {ru}")
            else:
                text_parts.append(f"• {ex}")
        text_parts.append("")

    if rule.get("exercises"):
        text_parts.append("📝 Упражнения:")
        for ex in rule["exercises"]:
            title = ex.get("title", "")
            if title:
                text_parts.append("")
                text_parts.append(title)
            for q in ex.get("questions", []):
                text_parts.append(q)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ К темам грамматики", callback_data="menu_grammar")],
            *build_back_to_main_row(),
        ]
    )

    await callback.message.edit_text("\n".join(text_parts), reply_markup=kb)
    await callback.answer()


# ==========================
# MAIN
# ==========================


async def main():
    load_allowed_users()
    load_user_state()
    load_words()
    load_grammar()

    print("Бот запущен.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

