
from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from datetime import datetime
from typing import Any, ClassVar, Dict, Tuple


class Role:

    ADMIN: ClassVar[str] = "Admin"
    STAFF: ClassVar[str] = "Staff"
    ALL_ROLES: ClassVar[Tuple[str, str]] = (ADMIN, STAFF)

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return role in cls.ALL_ROLES


class User:

    user_id: str
    username: str
    password_hash: str
    salt: str
    role: str
    active: bool
    created_at: str

    def __init__(
        self,
        username: str,
        password_hash: str,
        salt: str,
        role: str = Role.STAFF,
        user_id: str | None = None,
        active: bool = True,
        created_at: str | None = None,
    ) -> None:
        self.user_id = user_id or str(uuid.uuid4())
        self.username = username
        self.password_hash = password_hash
        self.salt = salt
        self.role = role if Role.is_valid(role) else Role.STAFF
        self.active = active
        self.created_at = created_at or datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, username: str, plain_password: str, role: str = Role.STAFF) -> "User":
        salt = os.urandom(16).hex()
        password_hash = cls._hash_password(plain_password, salt)
        return cls(username=username, password_hash=password_hash, salt=salt, role=role)

    def verify_password(self, plain_password: str) -> bool:
        candidate = self._hash_password(plain_password, self.salt)
        return hmac.compare_digest(candidate, self.password_hash)

    def set_password(self, new_plain_password: str) -> None:
        self.salt = os.urandom(16).hex()
        self.password_hash = self._hash_password(new_plain_password, self.salt)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "role": self.role,
            "active": self.active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            username=str(data["username"]),
            password_hash=str(data["password_hash"]),
            salt=str(data["salt"]),
            role=str(data.get("role", Role.STAFF)),
            user_id=data.get("user_id"),
            active=bool(data.get("active", True)),
            created_at=data.get("created_at"),
        )

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
