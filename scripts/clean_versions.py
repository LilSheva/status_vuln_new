"""Remove version numbers and year markers from product names.

Strips patterns like:
    - "2.4.51", "v1.21.3", "14.0"
    - "2024", "2023" (standalone years)
    - Trailing whitespace left after removal

This helps improve fuzzy and vector matching by focusing on
the product name rather than specific version strings.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_VERSION_PATTERNS = [
    # Semantic versions: v1.2.3, 2.4.51, 14.0.1
    re.compile(r"\b[vV]?\d+(?:\.\d+){1,4}\b"),
    # Standalone years: 2019, 2020, 2021, ..., 2030
    re.compile(r"\b20[12]\d\b"),
    # "version X.Y" or standalone "version" left after prior removals
    re.compile(r"\bversion\b(?:\s+\S+)?", re.IGNORECASE),
    # Cleanup repeated whitespace
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

        # Don't produce empty product names
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
