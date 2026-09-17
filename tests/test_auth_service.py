
from __future__ import annotations

import pytest

from models.user import Role
from services.auth_service import AuthService


def test_create_user_and_login(test_settings) -> None:
    service = AuthService(test_settings)
    user = service.create_user("Alice", "Strong123", Role.STAFF)

    assert user.username == "Alice"
    assert user.role == Role.STAFF
    assert service.login("alice", "Strong123") is True
    assert service.current_user == user
    assert service.is_authenticated() is True


def test_weak_password_is_rejected(test_settings) -> None:
    service = AuthService(test_settings)
    with pytest.raises(ValueError, match="Weak password"):
        service.create_user("Alice", "weak", Role.STAFF)


def test_duplicate_username_is_rejected(test_settings) -> None:
    service = AuthService(test_settings)
    service.create_user("Alice", "Strong123", Role.STAFF)
    with pytest.raises(ValueError, match="already exists"):
        service.create_user("alice", "Strong456", Role.STAFF)


def test_invalid_login_and_deactivated_user(test_settings) -> None:
    service = AuthService(test_settings)
    service.create_user("Alice", "Strong123", Role.STAFF)

    assert service.login("Alice", "Wrong123") is False
    assert service.login("Missing", "Strong123") is False
    assert service.deactivate_user("Alice") is True
    assert service.login("Alice", "Strong123") is False


def test_change_password_requires_strength_and_updates_login(test_settings) -> None:
    service = AuthService(test_settings)
    service.create_user("Alice", "Strong123", Role.STAFF)

    with pytest.raises(ValueError, match="Weak password"):
        service.change_password("Alice", "bad")

    assert service.change_password("Alice", "NewStrong9") is True
    assert service.login("Alice", "Strong123") is False
    assert service.login("Alice", "NewStrong9") is True
