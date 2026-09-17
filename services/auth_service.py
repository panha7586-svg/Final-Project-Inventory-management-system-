
from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import Settings, settings
from logger import setup_logger
from models.user import Role, User
from utils.json_handler import load_json, save_json
from utils.validators import validate_password_strength

logger = setup_logger(settings.log_level)


class AuthService:

    def __init__(self, config: Optional[Settings] = None) -> None:
        self.config = config or settings
        self.users: list[User] = self._load_users()
        self.current_user: Optional[User] = None

    def _load_users(self) -> list[User]:
        raw = load_json(self.config.users_file, default=[], data_dir=self.config.data_dir)
        return [User.from_dict(item) for item in raw if isinstance(item, dict)]

    def _save_users(self) -> None:
        if not save_json(
            self.config.users_file,
            [user.to_dict() for user in self.users],
            data_dir=self.config.data_dir,
        ):
            raise OSError("Unable to save user data.")

    def login(self, username: str, password: str) -> bool:
        for user in self.users:
            if user.username.lower() == username.lower():
                if not user.active:
                    logger.warning("Login rejected for deactivated account '%s'.", username)
                    return False
                if user.verify_password(password):
                    self.current_user = user
                    logger.info("User '%s' logged in as %s.", user.username, user.role)
                    return True
                logger.warning("Incorrect password for user '%s'.", username)
                return False
        logger.warning("Login attempted with unknown username '%s'.", username)
        return False

    def logout(self) -> None:
        if self.current_user:
            logger.info("User '%s' logged out.", self.current_user.username)
        self.current_user = None

    def is_authenticated(self) -> bool:
        return self.current_user is not None

    def is_admin(self) -> bool:
        return bool(self.current_user and self.current_user.role == Role.ADMIN)

    def username_exists(self, username: str) -> bool:
        return any(user.username.lower() == username.lower() for user in self.users)

    def create_user(
        self,
        username: str,
        password: str,
        role: str = Role.STAFF,
    ) -> User:
        username = username.strip()
        if not username:
            raise ValueError("Username cannot be empty.")
        if self.username_exists(username):
            raise ValueError(f"A user with username '{username}' already exists.")
        if not Role.is_valid(role):
            raise ValueError(f"Invalid role '{role}'.")
        if len(password) < max(8, self.config.password_min_length) or not validate_password_strength(password):
            raise ValueError(
                "Weak password. Use at least "
                f"{self.config.password_min_length} characters with at least one uppercase "
                "letter, one lowercase letter, and one digit."
            )

        user = User.create(username=username, plain_password=password, role=role)
        self.users.append(user)
        self._save_users()
        logger.info("Created user '%s' with role %s.", username, role)
        return user

    def deactivate_user(self, username: str) -> bool:
        for user in self.users:
            if user.username.lower() == username.lower():
                user.active = False
                self._save_users()
                logger.info("Deactivated user '%s'.", user.username)
                return True
        return False

    def reactivate_user(self, username: str) -> bool:
        for user in self.users:
            if user.username.lower() == username.lower():
                user.active = True
                self._save_users()
                logger.info("Reactivated user '%s'.", user.username)
                return True
        return False

    def list_users(self) -> list[User]:
        return list(self.users)

    def change_password(self, username: str, new_password: str) -> bool:
        if len(new_password) < max(8, self.config.password_min_length) or not validate_password_strength(new_password):
            raise ValueError(
                "Weak password. Use at least "
                f"{self.config.password_min_length} characters with at least one uppercase "
                "letter, one lowercase letter, and one digit."
            )
        for user in self.users:
            if user.username.lower() == username.lower():
                user.set_password(new_password)
                self._save_users()
                logger.info("Password changed for user '%s'.", user.username)
                return True
        return False
