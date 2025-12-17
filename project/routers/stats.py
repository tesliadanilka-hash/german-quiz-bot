from typing import List
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from config import ADMIN_ID
from services.access import has_access
from services.state import user_state
from services.words_repo import WORDS_BY_TOPIC, pretty_topic_name
from services.state import TOPIC_ALL

router = Router()

def build_user_stats_text(uid: int) -> str:
    state = user_state[uid]

    current_topic = state.get("topic", TOPIC_ALL)
    pretty_name = pretty_topic_name(current_topic)
    correct = state.get("correct", 0)
    wrong = state.get("wrong", 0)
    total = correct + wrong

    if total > 0:
        accuracy = correct * 100 / total
        accuracy_str = f"{accuracy:.1f}%"
        if accuracy >= 90:
            comment = "🔥 Отличный результат. Ты очень хорошо знаешь эту тему."
        elif accuracy >= 75:
            comment = "✅ Хороший уровень. Можно переходить дальше, но периодически повторяй."
        elif accuracy >= 60:
            comment = "⚠️ Неплохо, но стоит еще потренироваться в этой теме."
        else:
            comment = "📌 Рекомендую пройти тему еще раз с самого начала."
    else:
        accuracy_str = "Нет данных"
        comment = (
            "Пока нет ответов в этом круге. "
            "Начни тренировку слов и затем снова открой статистику."
        )

    total_words_in_topic = len(WORDS_BY_TOPIC.get(current_topic, []))

    lines: List[str] = []
    lines.append("📊 Твоя статистика по тренировкам слов:\n")
    lines.append(f"Текущая тема: {pretty_name}")
    lines.append(f"Слов в этой подборке: {total_words_in_topic}")
    lines.append("")
    lines.append(f"✅ Правильных ответов: {correct}")
    lines.append(f"❌ Неправильных ответов: {wrong}")
    lines.append(f"🎯 Точность: {accuracy_str}")
    lines.append("")
    lines.append(comment)

    return "\n".join(lines)

@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    uid = message.from_user.id
    if not has_access(uid, ADMIN_ID):
        await message.answer("Нет доступа.")
        return
    await message.answer(build_user_stats_text(uid))

@router.callback_query(F.data == "menu_stats")
async def cb_menu_stats(callback: CallbackQuery) -> None:
    uid = callback.from_user.id
    if not has_access(uid, ADMIN_ID):
        await callback.answer("Нет доступа.", show_alert=True)
        return
    await callback.answer()
    await callback.message.answer(build_user_stats_text(uid))
