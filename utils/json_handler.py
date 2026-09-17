
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from config import settings
from logger import setup_logger

logger = setup_logger(settings.log_level)


def _full_path(filename: str, data_dir: Optional[Path] = None) -> Path:
    return (data_dir or settings.data_dir) / filename


def ensure_data_dir(data_dir: Optional[Path] = None) -> Path:
    directory = data_dir or settings.data_dir
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def load_json(
    filename: str,
    default: Any = None,
    data_dir: Optional[Path] = None,
) -> Any:
    directory = ensure_data_dir(data_dir)
    path = _full_path(filename, directory)
    if default is None:
        default = []

    if not path.exists():
        return default

    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return default
        return json.loads(content)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read '%s': %s. Using default data.", filename, exc)
        return default


def save_json(
    filename: str,
    data: Any,
    data_dir: Optional[Path] = None,
) -> bool:
    directory = ensure_data_dir(data_dir)
    path = _full_path(filename, directory)
    tmp_path: Optional[Path] = None

    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(directory),
            text=True,
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        return True
    except (OSError, TypeError, ValueError) as exc:
        logger.error("Could not save '%s': %s", filename, exc)
        return False
    finally:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                logger.debug("Could not remove temporary file '%s'.", tmp_path)
