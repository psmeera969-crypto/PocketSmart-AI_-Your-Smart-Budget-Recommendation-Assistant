"""
Lightweight JSON-file "database".

For a learning/demo project like PocketSmart AI this avoids the
overhead of standing up a real database while still giving genuine
persistence across restarts. Swap this module for a real DB
(SQLAlchemy + Postgres/SQLite) later without touching route code -
every function here keeps the same signature you'd expect from a
repository/DAO layer.
"""
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import settings

_lock = threading.Lock()


def _read_json(path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------
def get_user(username: str) -> Optional[Dict[str, Any]]:
    with _lock:
        users = _read_json(settings.USERS_FILE)
    return users.get(username.lower())


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    with _lock:
        users = _read_json(settings.USERS_FILE)
    for user in users.values():
        if user.get("email", "").lower() == email.lower():
            return user
    return None


def create_user(username: str, email: str, full_name: str, hashed_password: str) -> Dict[str, Any]:
    with _lock:
        users = _read_json(settings.USERS_FILE)
        key = username.lower()
        if key in users:
            raise ValueError("Username already exists")
        user = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "hashed_password": hashed_password,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "disabled": False,
        }
        users[key] = user
        _write_json(settings.USERS_FILE, users)
        return user


# ------------------------------------------------------------------
# Recommendation history
# ------------------------------------------------------------------
def add_history_entry(username: str, category: str, user_input: dict, result: dict) -> Dict[str, Any]:
    with _lock:
        history = _read_json(settings.HISTORY_FILE)
        key = username.lower()
        entries: List[dict] = history.get(key, [])
        entry = {
            "id": str(uuid.uuid4()),
            "category": category,
            "input": user_input,
            "result": result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        entries.insert(0, entry)  # newest first
        history[key] = entries[:50]  # keep history bounded
        _write_json(settings.HISTORY_FILE, history)
        return entry


def get_history(username: str) -> List[Dict[str, Any]]:
    with _lock:
        history = _read_json(settings.HISTORY_FILE)
    return history.get(username.lower(), [])


def get_history_entry(username: str, entry_id: str) -> Optional[Dict[str, Any]]:
    for entry in get_history(username):
        if entry["id"] == entry_id:
            return entry
    return None
