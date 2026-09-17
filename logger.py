
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

_LOGGER_NAME = "inventory_app"


def setup_logger(log_level: str = "INFO", log_file: Optional[Path] = None) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = False

    if log_file is None:
        log_file = Path(__file__).resolve().parent / "app.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    # Avoid duplicated handlers when the application is reloaded or tested repeatedly.
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
    else:
        for handler in logger.handlers:
            handler.setLevel(level)

    return logger
