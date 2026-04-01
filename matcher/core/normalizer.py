"""Text normalization: transliteration between Cyrillic and Latin."""

from __future__ import annotations

import logging
import re

from transliterate import translit

logger = logging.getLogger(__name__)

# Common technical terms that should NOT be transliterated
_SKIP_PATTERNS = re.compile(
    r"\b(?:CVE-\d{4}-\d+|http[s]?://\S+|[A-Z]{2,}-\d+)\b",
    re.IGNORECASE,
)


def normalize_text(text: str, direction: str = "to_en") -> str:
    """Normalize text by transliterating to a single script (to_en or to_ru)."""
    if not text or not text.strip():
        return text

    text = text.strip().lower()

    if direction == "to_en":
        return _to_latin(text)
    if direction == "to_ru":
        return _to_cyrillic(text)

    logger.warning("Unknown transliteration direction: %r, defaulting to 'to_en'", direction)
    return _to_latin(text)


def _to_latin(text: str) -> str:
    """Transliterate Cyrillic characters to Latin."""
    if not _has_cyrillic(text):
        return text
    try:
        return translit(text, "ru", reversed=True)
    except Exception:
        logger.debug("Transliteration to Latin failed for: %r", text)
        return text


def _to_cyrillic(text: str) -> str:
    """Transliterate Latin characters to Cyrillic."""
    if not _has_latin(text):
        return text
    try:
        return translit(text, "ru")
    except Exception:
        logger.debug("Transliteration to Cyrillic failed for: %r", text)
        return text


def _has_cyrillic(text: str) -> bool:
    """Check if text contains any Cyrillic characters."""
    return bool(re.search(r"[а-яёА-ЯЁ]", text))


def _has_latin(text: str) -> bool:
    """Check if text contains any Latin characters."""
    return bool(re.search(r"[a-zA-Z]", text))
