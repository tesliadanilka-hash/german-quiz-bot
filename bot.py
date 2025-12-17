import asyncio

from loader import create_bot, create_dispatcher
from routers import setup_routers

from services.access import load_allowed_users
from services.words_repo import load_words
from services.state import load_user_state
from services.grammar_repo import load_grammar_rules


async def main() -> None:
    bot = create_bot()
    dp = create_dispatcher()

    dp.include_router(setup_routers())

    load_allowed_users()
    load_words()
    load_user_state()
    load_grammar_rules()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
