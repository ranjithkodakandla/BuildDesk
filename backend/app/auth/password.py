"""
Password Hashing Utilities
===========================
Provides bcrypt-backed password hashing and verification.
Never stores or returns plaintext passwords.
"""
from passlib.context import CryptContext

# bcrypt is the only active scheme; auto-migrate is a safety net for future upgrades
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Return True if plaintext matches the stored bcrypt hash."""
    return _pwd_context.verify(plaintext, hashed)
