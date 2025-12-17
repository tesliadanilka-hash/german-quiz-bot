import json
from collections import defaultdict
from typing import Dict, Any
from config import USER_STATE_FILE

TOPIC_ALL = "ALL"

def _default_state() -> Dict[str, Any]:
    return {
        "mode": "de_ru",
        "topic": TOPIC_ALL,
        "correct": 0,
        "wrong": 0,
        "remaining": None,
        "check_mode": False,
        "topic_stats": {},
        "answer_mode": "choice",
        "waiting_text_answer": False,
        "current_word_id": None,
        "grammar_stats": {
            "total_correct": 0,
            "total_wrong": 0,
            "per_rule": {}
        },
    }

user_state: Dict[int, Dict[str, Any]] = defaultdict(_default_state)

def load_user_state() -> None:
    try:
        with USER_STATE_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        count = 0
        for uid_str, state in raw.items():
            try:
                uid = int(uid_str)
            except ValueError:
                continue
            base = user_state[uid]
            if isinstance(state, dict):
                base.update(state)
            user_state[uid] = base
            count += 1

        print(f"Загружено состояний пользователей: {count}")
    except FileNotFoundError:
        print("Файл user_state.json не найден, начинаем с пустого состояния.")
    except Exception as e:
        print("Ошибка при загрузке состояний пользователей:", e)

def save_user_state() -> None:
    try:
        USER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        raw = {str(uid): state for uid, state in user_state.items()}
        with USER_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        print(f"Состояние пользователей сохранено. Всего пользователей: {len(raw)}")
    except Exception as e:
        print("Ошибка при сохранении состояний пользователей:", e)
