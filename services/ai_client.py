import os
import json
import random
import asyncio
from typing import Optional, Dict, Any, List

from openai import OpenAI

_client: Optional[OpenAI] = None
QUIZ_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_LOGGED_ONCE = False

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
    global _client, _LOGGED_ONCE

    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")

    if not _LOGGED_ONCE:
        print("AI_CLIENT: checking OPENAI_API_KEY")
        print(f"AI_CLIENT: key exists = {bool(api_key)}")
        _LOGGED_ONCE = True

    if not api_key:
        print("AI_CLIENT: OPENAI_API_KEY NOT FOUND")
        return None

    try:
        base_url = os.getenv("OPENAI_BASE_URL")
        if base_url:
            _client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            _client = OpenAI(api_key=api_key)
        print("AI_CLIENT: OpenAI client initialized successfully")
        return _client
    except Exception as e:
        print(f"AI_CLIENT: failed to init OpenAI client: {e}")
        _client = None
        return None


def strip_html_tags(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    for tag in ("<b>", "</b>", "<i>", "</i>", "<u>", "</u>"):
        text = text.replace(tag, "")
    return text


def _extract_json_block(content: str) -> str:
    if not content:
        return ""
    c = content.strip()
    if c.startswith("```"):
        c = c[3:].strip()
        if c.lower().startswith("json"):
            c = c[4:].strip()
        if c.endswith("```"):
            c = c[:-3].strip()
    return c.strip()


def _safe_json_loads(maybe_json: str) -> Optional[Dict[str, Any]]:
    if not maybe_json:
        return None
    s = maybe_json.strip()

    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    try:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            chunk = s[start:end + 1]
            obj = json.loads(chunk)
            return obj if isinstance(obj, dict) else None
    except Exception:
        return None

    return None


def _chat_completion_sync(messages: List[Dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
    client = get_client()
    if client is None:
        return ""

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (completion.choices[0].message.content or "").strip()


async def check_text_with_ai(text: str) -> str:
    client = get_client()
    if client is None:
        return (
            "Проверка ИИ сейчас недоступна.\n"
            "Проверь переменную окружения OPENAI_API_KEY в Render."
        )

    text = (text or "").strip()
    if not text:
        return "Пустой текст. Напиши предложение на немецком."

    model = os.getenv("OPENAI_MODEL_GRAMMAR", "gpt-4.1-mini")
    messages = [
        {"role": "system", "content": AI_SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    try:
        result = await asyncio.to_thread(_chat_completion_sync, messages, model, 0.2, 800)
        if not result:
            return "Не удалось получить ответ ИИ. Попробуй еще раз."
        return result
    except Exception as e:
        print(f"AI_CLIENT: check_text_with_ai error: {e}")
        return "Произошла ошибка при проверке. Попробуй еще раз позже."


async def generate_quiz_for_rule(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    client = get_client()
    if client is None:
        return []

    rule_id = str(rule.get("id", "")).strip()
    if not rule_id:
        return []

    cached = QUIZ_CACHE.get(rule_id)
    if cached:
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

    model = os.getenv("OPENAI_MODEL_QUIZ", "gpt-4.1-mini")
    messages = [
        {"role": "system", "content": "Antworte immer NUR mit einem gueltigen JSON-Objekt."},
        {"role": "user", "content": user_prompt},
    ]

    try:
        content = await asyncio.to_thread(_chat_completion_sync, messages, model, 0.35, 900)
        content = _extract_json_block(content)
        data = _safe_json_loads(content)
        if not data:
            return []
    except Exception as e:
        print(f"AI_CLIENT: generate_quiz_for_rule error: {e}")
        return []

    questions = data.get("questions", [])
    if not isinstance(questions, list):
        return []

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
