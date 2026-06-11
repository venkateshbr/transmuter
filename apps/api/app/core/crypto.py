from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet | None:
    if not settings.encryption_key:
        return None
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.encryption_key.encode()).digest())
    return Fernet(key)


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _fernet()
    if not fernet:
        raise ValueError("ENCRYPTION_KEY is required before storing integration tokens.")
    return fernet.encrypt(value.encode()).decode()


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    fernet = _fernet()
    if not fernet:
        return None
    try:
        return fernet.decrypt(value.encode()).decode()
    except InvalidToken:
        return None
