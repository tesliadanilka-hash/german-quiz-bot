from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import TOKEN

def create_bot() -> Bot:
    return Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))

def create_dispatcher() -> Dispatcher:
    return Dispatcher()
