import os
import json
import random
from typing import Optional, Dict, Any, List

from openai import OpenAI

_client: Optional[OpenAI] = None

# Кэш вопросов по rule_id, чтобы не дергать API каждый раз
QUIZ_CACHE: Dict[str, List[Dict[str, Any]]] = {}

AI_SYSTEM_PROMPT = (
    "Ты преподаватель немецкого языка. "
    "Твоя задача проверить грамматику и правописание немецкого текста.\n"
    "Всегда отвечай строго в таком формате:\n\n"
    "Исправленный вариант:\n"
    "{исправленный текст целиком}\n\n"
    "Ошибки:\n"
    "1) {кратко: что было не так, где, как правильно}\n"
    "2) {если есть}\n\n"
    "Если ошибок нет, напиши:\n"
    "Исправленный вариант:\n"
    "{исходный текст}\n\n"
    "Ошибки:\n"
    "Ошибок не найдено. Предложение грамматически корректно."
)


def get_client() -> Optional[OpenAI]:
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY set: {bool(api_key)}")  # <-- добавь это
    if api_key:
        print(f"OPENAI_API_KEY starts with: {api_key[:7]}")  # sk-xxxx

    if not api_key:
        return None

    _client = OpenAI(api_key=api_key)
    return _client



def strip_html_tags(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    for tag in ("<b>", "</b>", "<i>", "</i>", "<u>", "</u>"):
        text = text.replace(tag, "")
    return text


async def check_text_with_ai(text: str) -> str:
    client = get_client()
    if client is None:
        return (
            "Проверка ИИ сейчас недоступна.\n"
            "Проверь переменную окружения OPENAI_API_KEY в Render."
        )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception:
        return "Произошла ошибка при проверке. Попробуй еще раз позже."


async def generate_quiz_for_rule(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Генерирует 5 вопросов (4 варианта, 1 правильный) по конкретному правилу.
    Возвращает список:
    [{"question": str, "options": [str,str,str,str], "correct_index": int}, ...]
    """
    client = get_client()
    if client is None:
        return []

    rule_id = str(rule.get("id", "")).strip()
    if not rule_id:
        return []

    cached = QUIZ_CACHE.get(rule_id)
    if cached:
        return cached

    title = strip_html_tags(rule.get("title", ""))
    explanation = strip_html_tags(rule.get("explanation", ""))

    user_prompt = (
        "Du bist ein professioneller Lehrer fuer Deutsch als Fremdsprache.\n"
        "Erstelle 5 kurze Uebungsaufgaben, die AUSSCHLIESSLICH dieses Grammatikthema pruefen.\n\n"
        "WICHTIG:\n"
        "- Schreibe ALLES nur auf Deutsch.\n"
        "- Keine Erklaerungen, kein Text ausserhalb von JSON.\n"
        "- Feld \"question\" enthaelt nur den Satz oder Satz mit Luecke.\n"
        "- Jede Aufgabe hat GENAU 4 Antwortoptionen.\n"
        "- Es gibt GENAU EINE richtige Antwort (correct_index).\n\n"
        "Antwortformat: ein einziges JSON-Objekt:\n"
        "{\n"
        "  \"questions\": [\n"
        "    {\n"
        "      \"question\": \"...\",\n"
        "      \"options\": [\"A\",\"B\",\"C\",\"D\"],\n"
        "      \"correct_index\": 0\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Grammatikthema: {title}\n"
        f"Erklaerung:\n{explanation}\n"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Antworte immer NUR mit einem gueltigen JSON-Objekt.",
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            max_tokens=900,
        )
        content = (completion.choices[0].message.content or "").strip()

        # На всякий случай убираем ```json
        if content.startswith("```"):
            content = content.strip()
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            if content.lower().startswith("json"):
                content = content[4:].lstrip()

        data = json.loads(content)
    except Exception:
        return []

    questions = data.get("questions", [])
    clean: List[Dict[str, Any]] = []

    for q in questions:
        if not isinstance(q, dict):
            continue
        opts = q.get("options", [])
        if not isinstance(opts, list) or len(opts) != 4:
            continue
        ci = q.get("correct_index", None)
        if not isinstance(ci, int) or not (0 <= ci <= 3):
            continue

        clean.append(
            {
                "question": strip_html_tags(q.get("question", "")),
                "options": [strip_html_tags(o) for o in opts],
                "correct_index": int(ci),
            }
        )

    if not clean:
        return []

    random.shuffle(clean)
    clean = clean[:5]

    QUIZ_CACHE[rule_id] = clean
    return clean

