"""
Utility script — generate a random 32-byte AES-256 key encoded as base64.

Usage (run once, then paste output into backend/.env):
    python scripts/generate_encryption_key.py

Output example:
    TOKEN_ENCRYPTION_KEY=abc123...==

Keep this value secret. If you lose it, all stored tokens become unreadable.
"""
import base64
import os

key = os.urandom(32)
encoded = base64.b64encode(key).decode("utf-8")
print(f"TOKEN_ENCRYPTION_KEY={encoded}")
