"""Application configuration for the Knowledge Base app."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".vuln-analyzer"
CONFIG_FILE = CONFIG_DIR / "kb_config.json"

_DEFAULTS = {
    "last_db_path": "",
    "window_width": 1100,
    "window_height": 700,
}


def load_config() -> dict:
    """Load KB config from file, or return defaults."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            merged = {**_DEFAULTS, **data}
            return merged
        except Exception:
            logger.exception("Failed to load KB config from %s", CONFIG_FILE)
    return dict(_DEFAULTS)


def save_config(config: dict) -> None:
    """Persist KB config to file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.exception("Failed to save KB config to %s", CONFIG_FILE)
