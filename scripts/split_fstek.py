"""Split FSTEK multi-product entries: 'vendor1 - product1, vendor2 - product2' -> separate rows."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _looks_like_fstek_multiproduct(text: str) -> bool:
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) < 2:
        return False
    return sum(1 for p in parts if " - " in p) >= 2


def process(entries: list[dict]) -> list[dict]:
    result = []
    for entry in entries:
        raw = entry.get("raw_text", "") or entry.get("product", "")
        if not _looks_like_fstek_multiproduct(raw):
            result.append(entry)
            continue
        segments = [s.strip() for s in raw.split(",") if s.strip()]
        for segment in segments:
            parts = segment.split(" - ", 2)
            new_entry = dict(entry)
            if len(parts) >= 2:
                new_entry["vendor"] = parts[0].strip()
                new_entry["product"] = parts[1].strip()
                new_entry["version"] = parts[2].strip() if len(parts) > 2 else ""
            else:
                new_entry["product"] = segment.strip()
            new_entry["raw_text"] = segment.strip()
            result.append(new_entry)
    if len(result) != len(entries):
        logger.info("split_fstek: %d -> %d entries", len(entries), len(result))
    return result
