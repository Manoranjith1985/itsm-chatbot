import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def _get_private_key() -> str:
    if not settings.JWT_PRIVATE_KEY:
        raise RuntimeError("JWT_PRIVATE_KEY is not configured")
    return base64.b64decode(settings.JWT_PRIVATE_KEY).decode()


def _get_public_key() -> str:
    if not settings.JWT_PUBLIC_KEY:
        raise RuntimeError("JWT_PUBLIC_KEY is not configured")
    return base64.b64decode(settings.JWT_PUBLIC_KEY).decode()


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        _get_private_key(),
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        _get_private_key(),
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, _get_public_key(), algorithms=[settings.JWT_ALGORITHM])
        # Guard: ensure required claims exist
        if "sub" not in payload or "type" not in payload:
            return None
        return payload
    except (JWTError, Exception):
        return None


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        raise ValueError("Cannot encrypt an empty secret")
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    try:
        key = base64.b64decode(settings.ENCRYPTION_KEY)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext.encode(), None)
        return base64.b64encode(nonce + ct).decode()
    except Exception as e:
        raise RuntimeError(f"Encryption failed: {e}") from e


def decrypt_secret(ciphertext: str) -> str:
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    try:
        key = base64.b64decode(settings.ENCRYPTION_KEY)
        aesgcm = AESGCM(key)
        raw = base64.b64decode(ciphertext)
        nonce, ct = raw[:12], raw[12:]
        return aesgcm.decrypt(nonce, ct, None).decode()
    except Exception as e:
        raise RuntimeError(f"Decryption failed — token may be corrupted: {e}") from e
