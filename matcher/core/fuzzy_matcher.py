"""Fuzzy string matching using RapidFuzz."""

from __future__ import annotations

import logging

from rapidfuzz import fuzz

from shared.constants import DEFAULT_FUZZY_THRESHOLD, DEFAULT_MIN_WORD_LENGTH

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """Compare strings using multiple RapidFuzz strategies."""

    def __init__(
        self,
        threshold: int = DEFAULT_FUZZY_THRESHOLD,
        min_word_length: int = DEFAULT_MIN_WORD_LENGTH,
    ) -> None:
        self._threshold = threshold
        self._min_word_length = min_word_length

    def score(self, text_a: str, text_b: str) -> float:
        """Compute best fuzzy similarity score using multiple RapidFuzz strategies."""
        if not text_a or not text_b:
            return 0.0

        a = self._prepare(text_a)
        b = self._prepare(text_b)

        if not a or not b:
            return 0.0

        token_sort = fuzz.token_sort_ratio(a, b)
        token_set = fuzz.token_set_ratio(a, b)
        partial = fuzz.partial_ratio(a, b)

        return max(token_sort, token_set, partial)

    def is_match(self, text_a: str, text_b: str) -> bool:
        """Check if two strings are a fuzzy match above the threshold."""
        return self.score(text_a, text_b) >= self._threshold

    def score_candidates(
        self,
        query: str,
        candidate_names: list[str],
    ) -> list[float]:
        """Score a query against a list of candidate names."""
        return [self.score(query, name) for name in candidate_names]

    def _prepare(self, text: str) -> str:
        """Prepare text for comparison: lowercase, filter short words."""
        words = text.lower().split()
        filtered = [w for w in words if len(w) >= self._min_word_length]
        return " ".join(filtered) if filtered else text.lower()
