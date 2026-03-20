"""
AES-256-GCM encryption/decryption for OAuth tokens.
All platform tokens (GA4, Meta, Google Ads) must be encrypted before storage.
See docs/reportpilot-auth-integration-deepdive.md for security architecture.
IMPORTANT: Never log tokens or encryption keys.
"""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import settings


def _get_key() -> bytes:
    """
    Decode the base64-encoded 32-byte key from environment.
    Raises ValueError if the key is missing or the wrong length.
    """
    raw = settings.TOKEN_ENCRYPTION_KEY
    if not raw:
        raise ValueError(
            "TOKEN_ENCRYPTION_KEY is not set. "
            "Run scripts/generate_encryption_key.py to create one."
        )
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError(
            f"TOKEN_ENCRYPTION_KEY must decode to exactly 32 bytes "
            f"(got {len(key)}). Re-generate with scripts/generate_encryption_key.py."
        )
    return key


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a plaintext token string using AES-256-GCM.

    Returns a base64-encoded string in the format:
        base64(nonce [12 bytes] || ciphertext+tag)

    This single opaque string is what gets stored in the database.
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce — unique per encryption
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Prepend nonce so we can recover it during decryption
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_token(encrypted: str) -> str:
    """
    Decrypt a token previously encrypted by encrypt_token().

    Raises:
        cryptography.exceptions.InvalidTag — if the ciphertext has been tampered with
        ValueError — if the key is misconfigured
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    raw = base64.b64decode(encrypted)
    nonce = raw[:12]
    ciphertext = raw[12:]
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
