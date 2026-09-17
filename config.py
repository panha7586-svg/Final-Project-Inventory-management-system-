from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:

    base_dir: Path
    data_dir: Path
    users_file: str = "users.json"
    products_file: str = "products.json"
    suppliers_file: str = "suppliers.json"
    transactions_file: str = "transactions.json"
    max_login_attempts: int = 5
    password_min_length: int = 8
    default_admin_username: str = "admin"
    default_admin_password: str = "Admin123!"
    low_stock_threshold: int = 10
    log_level: str = "INFO"

    @classmethod
    def from_environment(cls) -> "Settings":
        data_dir_value = os.getenv("INVENTORY_DATA_DIR", "data")
        data_dir = Path(data_dir_value)
        if not data_dir.is_absolute():
            data_dir = BASE_DIR / data_dir

        return cls(
            base_dir=BASE_DIR,
            data_dir=data_dir,
            users_file=os.getenv("USERS_FILE", "users.json"),
            products_file=os.getenv("PRODUCTS_FILE", "products.json"),
            suppliers_file=os.getenv("SUPPLIERS_FILE", "suppliers.json"),
            transactions_file=os.getenv("TRANSACTIONS_FILE", "transactions.json"),
            max_login_attempts=max(1, _env_int("MAX_LOGIN_ATTEMPTS", 5)),
            password_min_length=max(4, _env_int("PASSWORD_MIN_LENGTH", 8)),
            default_admin_username=os.getenv("DEFAULT_ADMIN_USERNAME", "admin"),
            default_admin_password=os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin123!"),
            low_stock_threshold=max(0, _env_int("LOW_STOCK_THRESHOLD", 10)),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


settings: Settings = Settings.from_environment()
