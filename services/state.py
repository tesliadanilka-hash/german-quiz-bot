from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict

from config import USER_STATE_FILE

TOPIC_ALL = "ALL"

user_state: Dict[int, Dict[str, Any]] = defaultdict(
    lambda: {
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
        "grammar_stats": {"total_correct": 0, "total_wrong": 0, "per_rule": {}},
    }
)

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
        print(f"User states loaded: {count}")
    except FileNotFoundError:
        print("user_state.json not found. Starting empty.")
    except Exception as e:
        print("Failed to load user_state.json:", e)

def save_user_state() -> None:
    try:
        USER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        raw = {str(uid): state for uid, state in user_state.items()}
        with USER_STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Failed to save user_state.json:", e)
