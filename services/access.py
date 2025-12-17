from __future__ import annotations

from pathlib import Path
from typing import Set

from config import ALLOWED_USERS_FILE, ADMIN_ID

# Храним пользователей в памяти
_allowed_users: Set[int] = set()


def load_allowed_users() -> None:
    """
    Загружает allowed_users.txt в память.
    Вызывается один раз при старте бота.
    """
    global _allowed_users
    _allowed_users = set()

    path = Path(ALLOWED_USERS_FILE)

    if not path.exists():
        print("allowed_users.txt not found. Starting with empty access list.")
        return

    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                _allowed_users.add(int(line))
            except ValueError:
                continue

        print(f"Allowed users loaded: {len(_allowed_users)}")

    except Exception as e:
        print("Failed to load allowed users:", e)


def save_allowed_users() -> None:
    """
    Сохраняет текущий список пользователей в файл.
    """
    try:
        path = Path(ALLOWED_USERS_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)

        content = "\n".join(str(uid) for uid in sorted(_allowed_users))
        if content:
            content += "\n"

        path.write_text(content, encoding="utf-8")

    except Exception as e:
        print("Failed to save allowed users:", e)


def has_access(user_id: int, admin_id: int | None = None) -> bool:
    """
    Проверка доступа.
    Админ всегда имеет доступ.
    """
    if admin_id is None:
        admin_id = ADMIN_ID

    if user_id == admin_id:
        return True

    return user_id in _allowed_users


def add_allowed_user(user_id: int) -> None:
    """
    Добавляет пользователя в доступ и сохраняет файл.
    """
    _allowed_users.add(int(user_id))
    save_allowed_users()


def remove_allowed_user(user_id: int) -> None:
    """
    Удаляет пользователя из доступа.
    """
    _allowed_users.discard(int(user_id))
    save_allowed_users()


def get_allowed_users() -> Set[int]:
    """
    Возвращает копию списка пользователей с доступом.
    """
    return set(_allowed_users)
