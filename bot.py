# bot.py
import sys
import os
import asyncio

# ВАЖНО: добавляем папку проекта в sys.path ДО импортов routers/services/keyboards
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from loader import create_bot, create_dispatcher
from routers import setup_routers

from services.access import load_allowed_users
from services.words_repo import load_words
from services.state import load_user_state
from services.grammar_repo import load_grammar_rules


async def main() -> None:
    bot = create_bot()
    dp = create_dispatcher()

    # Подключаем routers
    dp.include_router(setup_routers())

    # Загружаем данные
    load_allowed_users()
    load_words()          # внутри words_repo пусть по умолчанию читает data/words.json
    load_user_state()     # внутри state.py пусть по умолчанию читает data/user_state.json
    load_grammar_rules()  # внутри grammar_repo пусть по умолчанию читает data/grammar.json

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
