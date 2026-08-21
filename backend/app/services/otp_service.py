"""In-memory email OTP store (works on a single Railway instance)."""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.services.auth_service import hash_password, verify_password

_lock = threading.Lock()


@dataclass
class _OtpRecord:
    code_hash: str
    expires_at: datetime
    attempts: int = 0


_STORE: dict[str, _OtpRecord] = {}
_MAX_ATTEMPTS = 5


def generate_otp_code(length: int = 6) -> str:
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"


def save_otp(email: str, code: str) -> None:
    normalized = email.strip().lower()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_OTP_EXPIRE_MINUTES)
    with _lock:
        _STORE[normalized] = _OtpRecord(code_hash=hash_password(code), expires_at=expires)


def verify_otp(email: str, code: str) -> bool:
    normalized = email.strip().lower()
    with _lock:
        record = _STORE.get(normalized)
        if record is None:
            return False
        if datetime.now(timezone.utc) > record.expires_at:
            _STORE.pop(normalized, None)
            return False
        if record.attempts >= _MAX_ATTEMPTS:
            _STORE.pop(normalized, None)
            return False
        record.attempts += 1
        if not verify_password(code.strip(), record.code_hash):
            return False
        _STORE.pop(normalized, None)
        return True
