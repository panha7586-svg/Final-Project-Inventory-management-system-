
from __future__ import annotations

from utils.validators import validate_password_strength


def test_password_strength_accepts_valid_password() -> None:
    assert validate_password_strength("Secure123") is True


def test_password_strength_rejects_short_password() -> None:
    assert validate_password_strength("Aa12345") is False


def test_password_strength_requires_uppercase() -> None:
    assert validate_password_strength("secure123") is False


def test_password_strength_requires_lowercase() -> None:
    assert validate_password_strength("SECURE123") is False


def test_password_strength_requires_digit() -> None:
    assert validate_password_strength("SecurePass") is False
