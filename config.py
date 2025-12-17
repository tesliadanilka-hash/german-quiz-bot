# config.py
import os
from pathlib import Path

# =========================
# БАЗОВЫЕ ПУТИ ПРОЕКТА
# =========================

# Папка, где лежит bot.py
BASE_DIR = Path(__file__).resolve().parent

# Папка с данными
DATA_DIR = BASE_DIR / "data"

# Файлы данных
WORDS_FILE = DATA_DIR / "words.json"
GRAMMAR_FILE = DATA_DIR / "grammar.json"
ALLOWED_USERS_FILE = DATA_DIR / "allowed_users.txt"
USER_STATE_FILE = DATA_DIR / "user_state.json"

# =========================
# НАСТРОЙКИ TELEGRAM
# =========================

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
)

if not TOKEN:
    raise RuntimeError(
        "Не найден токен бота.\n"
        "Добавь переменную окружения BOT_TOKEN в Render "
        "(или TELEGRAM_TOKEN / TELEGRAM_BOT_TOKEN / TOKEN)."
    )

# =========================
# НАСТРОЙКИ OPENAI
# =========================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================
# АДМИНИСТРАТОР
# =========================

ADMIN_ID = 5319848687  # ← замени на свой Telegram ID
