from __future__ import annotations

from typing import Set
from config import ALLOWED_USERS_FILE

allowed_users: Set[int] = set()


def load_allowed_users() -> None:
    global allowed_users
    try:
        ids = []
        with open(ALLOWED_USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.append(int(line))
                except ValueError:
                    continue
        allowed_users = set(ids)
        print(f"Allowed users loaded: {len(allowed_users)}")
    except FileNotFoundError:
        allowed_users = set()
        print("allowed_users.txt not found. Starting with empty list.")


def save_allowed_users() -> None:
    with open(ALLOWED_USERS_FILE, "w", encoding="utf-8") as f:
        for uid in sorted(allowed_users):
            f.write(str(uid) + "\n")


def has_access(user_id: int, admin_id: int) -> bool:
    return user_id == admin_id or user_id in allowed_users


def add_allowed_user(user_id: int) -> None:
    allowed_users.add(user_id)
    save_allowed_users()
