import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

def pick_file(data_path: Path, root_path: Path) -> Path:
    if data_path.exists() and data_path.stat().st_size > 0:
        return data_path
    if root_path.exists() and root_path.stat().st_size > 0:
        return root_path
    return data_path

WORDS_FILE = pick_file(DATA_DIR / "words.json", BASE_DIR / "words.json")
GRAMMAR_FILE = pick_file(DATA_DIR / "grammar.json", BASE_DIR / "grammar.json")
ALLOWED_USERS_FILE = pick_file(DATA_DIR / "allowed_users.txt", BASE_DIR / "allowed_users.txt")
USER_STATE_FILE = pick_file(DATA_DIR / "user_state.json", BASE_DIR / "user_state.json")

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TOKEN")
)

if not TOKEN:
    raise RuntimeError(
        "Не найден токен бота. Проверь переменную окружения BOT_TOKEN "
        "(или TELEGRAM_TOKEN / TELEGRAM_BOT_TOKEN / TOKEN)."
    )

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = 5319848687
