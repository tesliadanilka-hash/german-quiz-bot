from aiogram import Router

from .common import router as common_router
from .start import router as start_router
from .access import router as access_router
from .words import router as words_router
from .grammar import router as grammar_router
from .check import router as check_router
from .stats import router as stats_router


def setup_routers() -> Router:
    root = Router()

    # Общие кнопки (главное меню, назад)
    root.include_router(common_router)

    # Старт и доступ
    root.include_router(start_router)
    root.include_router(access_router)

    # Основная логика
    root.include_router(words_router)
    root.include_router(grammar_router)
    root.include_router(check_router)
    root.include_router(stats_router)

    return root
