
from __future__ import annotations

import re
from typing import Optional, Sequence, Set

from config import settings
from logger import setup_logger

logger = setup_logger(settings.log_level)


class CancelInput(Exception):
    pass


def validate_password_strength(password: str) -> bool:
    if len(password) < settings.password_min_length:
        return False
    return bool(
        re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    )


def password_strength_message(password: str) -> str:
    missing: list[str] = []
    if len(password) < settings.password_min_length:
        missing.append(f"at least {settings.password_min_length} characters")
    if not re.search(r"[A-Z]", password):
        missing.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        missing.append("one lowercase letter")
    if not re.search(r"\d", password):
        missing.append("one digit")
    return ", ".join(missing)


def prompt_nonempty_str(label: str, allow_cancel: bool = True) -> str:
    while True:
        raw = input(f"{label}{' (or c to cancel)' if allow_cancel else ''}: ").strip()
        if allow_cancel and raw.lower() == "c":
            raise CancelInput()
        if raw:
            return raw
        logger.warning("This field cannot be empty. Please try again.")


def prompt_optional_str(label: str, default: str = "") -> str:
    raw = input(f"{label} [{default}]: ").strip()
    return raw if raw else default


def prompt_int(
    label: str,
    minimum: Optional[int] = None,
    allow_cancel: bool = True,
) -> int:
    while True:
        raw = input(f"{label}{' (or c to cancel)' if allow_cancel else ''}: ").strip()
        if allow_cancel and raw.lower() == "c":
            raise CancelInput()
        try:
            value = int(raw)
            if minimum is not None and value < minimum:
                logger.warning("Value must be >= %s.", minimum)
                continue
            return value
        except ValueError:
            logger.warning("Please enter a valid whole number.")


def prompt_float(
    label: str,
    minimum: Optional[float] = None,
    allow_cancel: bool = True,
) -> float:
    while True:
        raw = input(f"{label}{' (or c to cancel)' if allow_cancel else ''}: ").strip()
        if allow_cancel and raw.lower() == "c":
            raise CancelInput()
        try:
            value = float(raw)
            if minimum is not None and value < minimum:
                logger.warning("Value must be >= %s.", minimum)
                continue
            return value
        except ValueError:
            logger.warning("Please enter a valid number.")


def prompt_choice(label: str, choices: Sequence[str], allow_cancel: bool = True) -> str:
    lowered = {choice.lower(): choice for choice in choices}
    while True:
        raw = input(
            f"{label} ({'/'.join(choices)})"
            f"{' or c to cancel' if allow_cancel else ''}: "
        ).strip()
        if allow_cancel and raw.lower() == "c":
            raise CancelInput()
        if raw.lower() in lowered:
            return lowered[raw.lower()]
        logger.warning("Please choose one of: %s", ", ".join(choices))


def prompt_confirm(label: str) -> bool:
    while True:
        raw = input(f"{label} (y/n): ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        logger.warning("Please answer y or n.")


def prompt_menu_choice(label: str, valid_options: Set[str]) -> str:
    while True:
        raw = input(f"{label}: ").strip()
        if raw in valid_options:
            return raw
        logger.warning("Invalid choice. Please select a valid menu option.")
