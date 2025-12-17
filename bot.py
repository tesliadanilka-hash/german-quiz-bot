import asyncio
import logging

from loader import create_bot, create_dispatcher
from routers import setup_routers

from services.access import load_allowed_users
from services.words_repo import load_words
from services.state import load_user_state
from services.grammar_repo import load_grammar_rules


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bot")


async def main() -> None:
    bot = create_bot()
    dp = create_dispatcher()

    # Подключаем роутеры
    dp.include_router(setup_routers())

    # Загружаем данные до старта polling
    try:
        load_allowed_users()
        logger.info("Allowed users loaded.")
    except Exception:
        logger.exception("Failed to load allowed users.")

    try:
        load_words()
        logger.info("Words loaded.")
    except Exception:
        logger.exception("Failed to load words.")

    try:
        load_user_state()
        logger.info("User state loaded.")
    except Exception:
        logger.exception("Failed to load user state.")

    try:
        load_grammar_rules()
        logger.info("Grammar rules loaded.")
    except Exception:
        logger.exception("Failed to load grammar rules.")

    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
