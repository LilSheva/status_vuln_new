"""Clean Microsoft-specific noise (trademarks, editions, KB updates) from product names."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_PATTERNS_TO_REMOVE = [
    re.compile(r"\((?:R|TM|C|r|tm|c)\)", re.IGNORECASE),
    re.compile(r"\s+for\s+(?:windows|x64|x86|arm|64-bit|32-bit)[\w\s-]*", re.IGNORECASE),
    re.compile(r"\s+service\s+pack\s+\d*", re.IGNORECASE),
    re.compile(r"\s*(?:update\s+)?KB\d{6,}", re.IGNORECASE),
    re.compile(
        r"\s+(?:Enterprise|Professional|Pro|Home|Standard|Datacenter|Ultimate|Premium|Starter)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\s{2,}"),
]

_MS_PREFIX = re.compile(r"^Microsoft\s+", re.IGNORECASE)


def process(entries: list[dict]) -> list[dict]:
    """Clean Microsoft-specific noise from product names."""
    for entry in entries:
        product = entry.get("product", "")
        if not product:
            continue

        original = product
        for pat in _PATTERNS_TO_REMOVE:
            product = pat.sub(" ", product)

        product = product.strip()

        if product != original:
            logger.debug("Cleaned: %r -> %r", original, product)
            entry["product"] = product
            entry["raw_text"] = " ".join(
                s
                for s in (entry.get("vendor", ""), product, entry.get("version", ""))
                if s
            )

    return entries
