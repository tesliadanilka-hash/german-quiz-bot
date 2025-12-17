import os
from pathlib import Path

# Корень проекта (папка, где лежит bot.py)
BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"

WORDS_FILE = DATA_DIR / "words.json"
GRAMMAR_FILE = DATA_DIR / "grammar.json"
ALLOWED_USERS_FILE = DATA_DIR / "allowed_users.txt"
USER_STATE_FILE = DATA_DIR / "user_state.json"

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
)

if not TOKEN:
    raise RuntimeError(
        "Не найден токен бота. "
        "Проверь, что в Render есть переменная окружения BOT_TOKEN "
        "(или TELEGRAM_TOKEN / TELEGRAM_BOT_TOKEN / TOKEN)."
    )

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

ADMIN_ID = 5319848687  # ЗАМЕНИ НА СВОЙ TELEGRAM ID
