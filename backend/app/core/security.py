"""Cryptographic and Security Services: Argon2id, AES-256-GCM, HMAC Blind Index, JWT."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import os
import hmac
import hashlib
import base64
import uuid
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

# 1. Argon2id Password Hasher (m=64MB, t=3, p=4)
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hashes a password using Argon2id."""
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False


# 2. JWT Access Tokens with unique JTI
def create_access_token(
    subject: str,
    claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str, datetime]:
    """
    Creates a signed JWT access token.
    Returns: (token_str, jti, expires_at)
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if claims:
        to_encode.update(claims)

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt, jti, expire


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token signature and expiration."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=["HS256"],
        options={"require": ["exp", "sub", "jti"]},
    )


# 3. Dedicated Blind Index (HMAC-SHA256)
def compute_blind_index(value: str) -> str:
    """
    Computes deterministic HMAC-SHA256 hash using the dedicated BLIND_INDEX_SECRET_KEY.
    Used for exact candidate lookups without decrypting all database records.
    """
    normalized = value.strip().replace("-", "").replace(" ", "").upper()
    key_bytes = bytes.fromhex(settings.BLIND_INDEX_SECRET_KEY)
    return hmac.new(key_bytes, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


# 4. AES-256-GCM Field-Level Encryption & Decryption
def encrypt_sensitive_field(plaintext: str, key_version: str = "v1") -> str:
    """
    Encrypts sensitive text using AES-256-GCM with a random 12-byte IV.
    Format: enc:<key_version>:<base64_iv>:<base64_tag>:<base64_ciphertext>
    """
    key_bytes = bytes.fromhex(settings.DATA_ENCRYPTION_KEY)
    aesgcm = AESGCM(key_bytes)
    iv = os.urandom(12)
    # AESGCM.encrypt returns ciphertext + 16-byte tag appended
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
    ciphertext = ciphertext_and_tag[:-16]
    tag = ciphertext_and_tag[-16:]

    b64_iv = base64.b64encode(iv).decode("utf-8")
    b64_tag = base64.b64encode(tag).decode("utf-8")
    b64_ciph = base64.b64encode(ciphertext).decode("utf-8")

    return f"enc:{key_version}:{b64_iv}:{b64_tag}:{b64_ciph}"


def decrypt_sensitive_field(encrypted_str: str) -> str:
    """Decrypts AES-256-GCM formatted field."""
    parts = encrypted_str.split(":")
    if len(parts) != 5 or parts[0] != "enc":
        raise ValueError("Invalid encrypted field format.")

    key_version, b64_iv, b64_tag, b64_ciph = parts[1], parts[2], parts[3], parts[4]
    key_bytes = bytes.fromhex(settings.DATA_ENCRYPTION_KEY)
    aesgcm = AESGCM(key_bytes)

    iv = base64.b64decode(b64_iv)
    tag = base64.b64decode(b64_tag)
    ciphertext = base64.b64decode(b64_ciph)

    plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)
    return plaintext.decode("utf-8")

