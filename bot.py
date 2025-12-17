# bot.py
import sys
import os
import asyncio
import logging

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from loader import create_bot, create_dispatcher
from routers import setup_routers

from services.access import load_allowed_users
from services.words_repo import load_words
from services.state import load_user_state
from services.grammar_repo import load_grammar_rules


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = create_bot()
    dp = create_dispatcher()

    dp.include_router(setup_routers())

    load_allowed_users()
    load_words()
    load_user_state()
    load_grammar_rules()

    # ВАЖНО: если раньше был webhook, он может мешать polling
    await bot.delete_webhook(drop_pending_updates=True)

    me = await bot.get_me()
    logging.info(f"Started bot: @{me.username} (id={me.id})")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
