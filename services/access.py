from __future__ import annotations

from pathlib import Path
from typing import Set

from config import ALLOWED_USERS_FILE


allowed_users: Set[int] = set()


def load_allowed_users() -> None:
    global allowed_users
    path = Path(ALLOWED_USERS_FILE)

    if not path.exists():
        allowed_users = set()
        print("Allowed users file not found, starting with empty list.")
        return

    ids: Set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.add(int(line))
        except ValueError:
            continue

    allowed_users = ids
    print(f"Allowed users loaded: {len(allowed_users)}")


def save_allowed_users() -> None:
    path = Path(ALLOWED_USERS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = "\n".join(str(uid) for uid in sorted(allowed_users)) + ("\n" if allowed_users else "")
    path.write_text(content, encoding="utf-8")
    print(f"Allowed users saved: {len(allowed_users)}")


def has_access(user_id: int, admin_id: int) -> bool:
    if user_id == admin_id:
        return True
    return user_id in allowed_users


def add_allowed_user(user_id: int) -> None:
    allowed_users.add(int(user_id))
    save_allowed_users()
