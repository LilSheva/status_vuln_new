"""Application configuration and defaults for the Matcher app."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from shared.types import PipelineSettings, PptsColumnMapping

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".vuln-analyzer"
CONFIG_FILE = CONFIG_DIR / "matcher_config.json"
MAPPINGS_FILE = CONFIG_DIR / "ppts_mappings.json"
RESPONSIBLE_FILE = CONFIG_DIR / "responsible_persons.json"


def load_settings() -> PipelineSettings:
    """Load pipeline settings from the config file, or return defaults."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return PipelineSettings(**data)
        except Exception:
            logger.exception("Failed to load config from %s, using defaults", CONFIG_FILE)
    return PipelineSettings()


def save_settings(settings: PipelineSettings) -> None:
    """Persist pipeline settings to the config file."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Settings saved to %s", CONFIG_FILE)
    except Exception:
        logger.exception("Failed to save config to %s", CONFIG_FILE)


# ---------------------------------------------------------------------------
# PPTS column mappings persistence
# ---------------------------------------------------------------------------


def _mapping_to_dict(m: PptsColumnMapping) -> dict:
    return {
        "file_path": m.file_path,
        "col_id": m.col_id,
        "col_name": m.col_name,
        "col_vendor": m.col_vendor,
    }


def _dict_to_mapping(d: dict) -> PptsColumnMapping:
    return PptsColumnMapping(
        file_path=d.get("file_path", ""),
        col_id=d.get("col_id"),
        col_name=d.get("col_name"),
        col_vendor=d.get("col_vendor"),
    )


def load_responsible_data() -> dict[str, object]:
    """Load the saved list of responsible persons and last-used values."""
    if RESPONSIBLE_FILE.exists():
        try:
            return json.loads(RESPONSIBLE_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load responsible data from %s", RESPONSIBLE_FILE)
    return {"persons": [], "last_responsible": "", "last_publication": "БДУ ФСТЕК"}


def save_responsible_data(persons: list[str], last_responsible: str, last_publication: str) -> None:
    """Persist the list of responsible persons and last-used values."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "persons": persons,
            "last_responsible": last_responsible,
            "last_publication": last_publication,
        }
        RESPONSIBLE_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Responsible data saved to %s", RESPONSIBLE_FILE)
    except Exception:
        logger.exception("Failed to save responsible data to %s", RESPONSIBLE_FILE)


def load_ppts_mappings() -> dict[str, PptsColumnMapping]:
    """Load saved PPTS column mappings keyed by source ('local' / 'general')."""
    if MAPPINGS_FILE.exists():
        try:
            data = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
            return {key: _dict_to_mapping(val) for key, val in data.items()}
        except Exception:
            logger.exception("Failed to load PPTS mappings")
    return {}


def save_ppts_mappings(mappings: dict[str, PptsColumnMapping]) -> None:
    """Save PPTS column mappings."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {key: _mapping_to_dict(val) for key, val in mappings.items()}
        MAPPINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("PPTS mappings saved to %s", MAPPINGS_FILE)
    except Exception:
        logger.exception("Failed to save PPTS mappings")
