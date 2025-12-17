# ai_client.py
import os
import json
import random
from typing import Optional, Dict, Any, List

from openai import OpenAI


# Один клиент на весь процесс
_client: Optional[OpenAI] = None

# Кэш викторин по rule_id
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
    """
    Создает и возвращает OpenAI-клиент.
    Если ключа нет или клиент не создается - вернет None.
    """
    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")

    # Безопасные логи: не печатаем кусок ключа
    print("AI_CLIENT: checking OPENAI_API_KEY")
    print(f"AI_CLIENT: key exists = {bool(api_key)}")

    if not api_key:
        print("AI_CLIENT: OPENAI_API_KEY NOT FOUND")
        return None

    try:
        _client = OpenAI(api_key=api_key)
        print("AI_CLIENT: OpenAI client initialized successfully")
        return _client
    except Exception as e:
        print(f"AI_CLIENT: failed to init OpenAI client: {e}")
        _client = None
        return None


def strip_html_tags(text: str) -> str:
    """
    Удаляет простые HTML-теги, которые могут быть в grammar.json
    """
    if not isinstance(text, str):
        return str(text)

    for tag in ("<b>", "</b>", "<i>", "</i>", "<u>", "</u>"):
        text = text.replace(tag, "")

    return text


def _extract_json_block(content: str) -> str:
    """
    Если модель вернула JSON в ``` ``` - аккуратно вытаскиваем.
    """
    if not content:
        return ""

    c = content.strip()

    if c.startswith("```"):
        # убираем первые ```
        c = c[3:].strip()
        # может быть ```json
        if c.lower().startswith("json"):
            c = c[4:].strip()
        # убираем завершающие ```
        if c.endswith("```"):
            c = c[:-3].strip()

    return c.strip()


async def check_text_with_ai(text: str) -> str:
    """
    Проверка немецкого текста на грамматику/правописание.
    Возвращает строку для отправки пользователю.
    """
    client = get_client()
    if client is None:
        return (
            "Проверка ИИ сейчас недоступна.\n"
            "Проверь переменную окружения OPENAI_API_KEY в Render."
        )

    text = (text or "").strip()
    if not text:
        return "Пустой текст. Напиши предложение на немецком."

    try:
        completion = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL_GRAMMAR", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0.2,
            max_tokens=800,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"AI_CLIENT: check_text_with_ai error: {e}")
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
        # Возвращаем копию, чтобы внешний код не портил кэш случайно
        return [dict(x) for x in cached]

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
            model=os.getenv("OPENAI_MODEL_QUIZ", "gpt-4.1-mini"),
            messages=[
                {"role": "system", "content": "Antworte immer NUR mit einem gueltigen JSON-Objekt."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            max_tokens=900,
        )

        content = (completion.choices[0].message.content or "").strip()
        content = _extract_json_block(content)

        data = json.loads(content)
    except Exception as e:
        print(f"AI_CLIENT: generate_quiz_for_rule error: {e}")
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
    return [dict(x) for x in clean]
