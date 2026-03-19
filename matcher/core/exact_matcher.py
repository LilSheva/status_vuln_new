"""Exact and substring matching."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ExactMatcher:
    """Perform exact and substring matching between strings."""

    def score(self, query: str, candidate: str) -> float:
        """Compute an exact/substring match score.

        Returns:
            - 100.0 for exact match (case-insensitive)
            - 75.0 if query is a substring of candidate
            - 75.0 if candidate is a substring of query
            - 50.0 if all significant words of query appear in candidate
            - 0.0 otherwise
        """
        if not query or not candidate:
            return 0.0

        q = query.strip().lower()
        c = candidate.strip().lower()

        if q == c:
            return 100.0

        if q in c or c in q:
            return 75.0

        q_words = set(q.split())
        c_words = set(c.split())
        if q_words and q_words.issubset(c_words):
            return 50.0

        return 0.0

    def score_candidates(
        self,
        query: str,
        candidate_names: list[str],
    ) -> list[float]:
        """Score a query against a list of candidate names.

        Args:
            query: The query text.
            candidate_names: List of candidate strings.

        Returns:
            List of scores (same order as candidate_names).
        """
        return [self.score(query, name) for name in candidate_names]
