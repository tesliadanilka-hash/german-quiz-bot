# services/access.py
from pathlib import Path
from typing import Set

from config import ADMIN_ID, ALLOWED_USERS_FILE

allowed_users: Set[int] = set()


def load_allowed_users() -> None:
    global allowed_users

    path = Path(ALLOWED_USERS_FILE)
    if not path.exists():
        allowed_users = set()
        print("allowed_users.txt not found, starting empty.")
        return

    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.append(int(line))
        except ValueError:
            continue

    allowed_users = set(ids)
    print(f"Allowed users loaded: {len(allowed_users)}")


def save_allowed_users() -> None:
    path = Path(ALLOWED_USERS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)

    text = "\n".join(str(uid) for uid in sorted(allowed_users))
    if text:
        text += "\n"

    path.write_text(text, encoding="utf-8")


def add_allowed_user(user_id: int) -> None:
    allowed_users.add(int(user_id))
    save_allowed_users()


def has_access(user_id: int) -> bool:
    user_id = int(user_id)
    return user_id == int(ADMIN_ID) or user_id in allowed_users
