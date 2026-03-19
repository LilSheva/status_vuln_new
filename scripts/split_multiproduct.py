"""Split multi-product entries into separate rows.

Handles cases where a single TSU row contains multiple products
separated by common delimiters: semicolons, " и ", " / ", commas
(only when not inside version strings).

Example:
    "Apache HTTP Server; Nginx" -> two separate entries
    "Microsoft Word и Excel"    -> two separate entries
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Patterns that indicate multiple products in a single field
_SPLIT_PATTERN = re.compile(
    r"\s*(?:;|\s+и\s+|\s*/\s*)\s*",
    re.IGNORECASE,
)


def process(entries: list[dict]) -> list[dict]:
    """Split entries with multiple products into separate entries."""
    result: list[dict] = []

    for entry in entries:
        product = entry.get("product", "").strip()
        if not product:
            result.append(entry)
            continue

        parts = _SPLIT_PATTERN.split(product)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) <= 1:
            result.append(entry)
            continue

        logger.debug("Splitting multi-product: %r -> %d parts", product, len(parts))
        for part in parts:
            new_entry = dict(entry)
            new_entry["product"] = part
            new_entry["raw_text"] = " ".join(
                s for s in (entry.get("vendor", ""), part, entry.get("version", "")) if s
            )
            result.append(new_entry)

    if len(result) != len(entries):
        logger.info(
            "split_multiproduct: %d entries -> %d entries", len(entries), len(result)
        )

    return result
