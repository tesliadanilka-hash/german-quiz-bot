import json
from typing import Dict, Any, List, Optional

from openai import OpenAI
from config import OPENAI_API_KEY
from services.grammar_repo import strip_html_tags

client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

AI_SYSTEM_PROMPT = (
    "Ты преподаватель немецкого языка. "
    "Твоя задача - проверять грамматику и правописание немецких предложений.\n"
    "Всегда отвечай строго в таком формате:\n\n"
    "Исправленный вариант:\n"
    "{здесь напиши исправленный вариант всего текста целиком}\n\n"
    "Ошибки:\n"
    "1) {кратко опиши первую ошибку, укажи фрагмент и как правильно}\n"
    "2) {вторая ошибка, если есть}\n"
    "Если ошибок нет, напиши:\n"
    "Исправленный вариант:\n"
    "{исходный текст}\n\n"
    "Ошибки:\n"
    "Ошибок не найдено. Предложение грамматически корректно."
)

def is_available() -> bool:
    return client is not None

async def check_text_with_ai(text: str) -> str:
    if client is None:
        return "Проверка предложений сейчас недоступна.\nОбратись к администратору."

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Ошибка при проверке предложения:", e)
        return "Произошла ошибка при проверке. Попробуй еще раз позже."

async def generate_quiz_for_rule(rule: Dict[str, Any], quiz_cache: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Генерируем 5 вопросов по конкретному правилу через OpenAI.
    Кэш передается снаружи, чтобы хранить его в router.
    """
    if client is None:
        print("Нет OPENAI_API_KEY, викторина по грамматике недоступна.")
        return []

    rule_id = str(rule.get("id", ""))
    if not rule_id:
        return []

    cached = quiz_cache.get(rule_id)
    if cached:
        return cached

    title = strip_html_tags(rule.get("title", ""))
    explanation = strip_html_tags(rule.get("explanation", ""))

    user_prompt = (
        "Du bist ein professioneller Lehrer fuer Deutsch als Fremdsprache.\n"
        "Erstelle 5 kurze Uebungsaufgaben, die AUSSCHLIESSLICH dieses Grammatikthema pruefen.\n"
        "Benutze KEINE anderen Grammatikstrukturen, die nicht zu diesem Thema gehoeren.\n\n"
        "WICHTIG:\n"
        "- Schreibe ALLES nur auf Deutsch.\n"
        "- Keine Erklaerungen, kein Englisch, keine anderen Sprachen.\n"
        "- Feld \"question\" enthaelt nur den Beispielsatz oder Satz mit Luecke, ohne Arbeitsanweisungen.\n"
        "- Jede Aufgabe hat GENAU 4 Antwortoptionen.\n"
        "- Es gibt GENAU EINE richtige Antwort (correct_index).\n\n"
        "Antwortformat: ein einziges JSON-Objekt:\n"
        "{ \"questions\": [ {\"question\":\"...\",\"options\":[\"1\",\"2\",\"3\",\"4\"],\"correct_index\":0} ] }\n\n"
        "Schreibe nur JSON. Keine HTML-Tags.\n\n"
        f"Grammatikthema (Titel): {title}\n\n"
        f"Erklaerung des Themas:\n{explanation}\n"
    )

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "Du bist ein strenger JSON-Generator. Antworte nur mit JSON."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            max_tokens=700,
        )
        content = completion.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.strip().lstrip("```").rstrip("```").strip()
            if content.lower().startswith("json"):
                content = content[4:].lstrip()

        data = json.loads(content)
    except Exception as e:
        print("Ошибка при генерации викторины:", e)
        return []

    questions = data.get("questions", [])
    clean: List[Dict[str, Any]] = []

    for q in questions:
        if not isinstance(q, dict):
            continue
        opts = q.get("options", [])
        if not isinstance(opts, list) or len(opts) != 4:
            continue
        if not isinstance(q.get("correct_index", 0), int):
            continue

        clean.append(
            {
                "question": strip_html_tags(q.get("question", "")),
                "options": [strip_html_tags(o) for o in opts],
                "correct_index": int(q["correct_index"]),
            }
        )

    clean = clean[:5]
    if clean:
        quiz_cache[rule_id] = clean
    return clean
