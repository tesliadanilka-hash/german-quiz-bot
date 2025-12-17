from __future__ import annotations

from typing import Set
from pathlib import Path

from config import ALLOWED_USERS_FILE

_allowed_users: Set[int] = set()


def load_allowed_users() -> Set[int]:
    """Загружает allowed_users.txt в память."""
    global _allowed_users
    _allowed_users = set()

    path = Path(ALLOWED_USERS_FILE)
    if not path.exists():
        print("Allowed users file not found, starting empty.")
        return _allowed_users

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

    return _allowed_users


def save_allowed_users() -> None:
    """Сохраняет текущий set в allowed_users.txt."""
    path = Path(ALLOWED_USERS_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(str(x) for x in sorted(_allowed_users)) + ("\n" if _allowed_users else ""), encoding="utf-8")
    except Exception as e:
        print("Failed to save allowed users:", e)


def has_access(user_id: int, admin_id: int) -> bool:
    """True если это админ или пользователь в списке."""
    if user_id == admin_id:
        return True
    return user_id in _allowed_users


def add_allowed_user(user_id: int) -> None:
    """Добавляет пользователя и сохраняет файл."""
    _allowed_users.add(int(user_id))
    save_allowed_users()


def remove_allowed_user(user_id: int) -> None:
    """Удаляет пользователя и сохраняет файл."""
    _allowed_users.discard(int(user_id))
    save_allowed_users()


def get_allowed_users() -> Set[int]:
    """Возвращает текущий set (без чтения файла)."""
    return set(_allowed_users)
