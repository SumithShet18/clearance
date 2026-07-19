"""
Workspace password: env CLEARANCE_PASSWORD OR SQLite hash (set in UI).

Solves Render cases where env vars never reach the container —
user can set a password from the open app once.
"""

from __future__ import annotations

import hashlib
import secrets

from app.config import settings

# In-memory cache of DB password hash (sha256 hex); loaded at startup / setup
_db_password_hash: str = ""


def hash_password(password: str) -> str:
    # salt from session_secret so hashes aren't portable across installs
    salt = (settings.session_secret or "clearance").encode("utf-8")
    return hashlib.sha256(salt + password.encode("utf-8")).hexdigest()


def set_db_password_hash(value: str | None) -> None:
    global _db_password_hash
    _db_password_hash = (value or "").strip()


def get_db_password_hash() -> str:
    return _db_password_hash


def env_password() -> str:
    return settings.effective_password


def auth_enabled() -> bool:
    """True if env password or workspace DB password is configured."""
    return bool(env_password()) or bool(_db_password_hash)


def verify_password(password: str) -> bool:
    expected_env = env_password()
    if expected_env:
        try:
            return secrets.compare_digest(
                password.encode("utf-8"), expected_env.encode("utf-8")
            )
        except (TypeError, ValueError):
            return False
    if _db_password_hash:
        try:
            return secrets.compare_digest(hash_password(password), _db_password_hash)
        except (TypeError, ValueError):
            return False
    # open access
    return True


def password_source() -> str:
    if env_password():
        return "env"
    if _db_password_hash:
        return "database"
    return "none"
