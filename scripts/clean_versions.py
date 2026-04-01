"""Remove version numbers and year markers from product names."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_VERSION_PATTERNS = [
    re.compile(r"\b[vV]?\d+(?:\.\d+){1,4}\b"),
    re.compile(r"\b20[12]\d\b"),
    re.compile(r"\bversion\b(?:\s+\S+)?", re.IGNORECASE),
    re.compile(r"\s{2,}"),
]


def process(entries: list[dict]) -> list[dict]:
    """Remove version numbers and years from product names."""
    for entry in entries:
        product = entry.get("product", "")
        if not product:
            continue

        original = product
        for pat in _VERSION_PATTERNS:
            product = pat.sub(" ", product)

        product = product.strip()

        if not product:
            product = original

        if product != original:
            logger.debug("Cleaned versions: %r -> %r", original, product)
            entry["product"] = product
            entry["raw_text"] = " ".join(
                s
                for s in (entry.get("vendor", ""), product, entry.get("version", ""))
                if s
            )

    return entries
