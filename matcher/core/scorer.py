"""Combined scoring: merge vector, fuzzy, and exact scores into a final rank."""

from __future__ import annotations

import logging

from shared.types import MatchCandidate, Software

logger = logging.getLogger(__name__)

# Weight distribution for the combined score
WEIGHT_VECTOR = 0.50
WEIGHT_FUZZY = 0.30
WEIGHT_EXACT = 0.20


class Scorer:
    """Combine multiple matching scores into a single combined score."""

    def __init__(
        self,
        weight_vector: float = WEIGHT_VECTOR,
        weight_fuzzy: float = WEIGHT_FUZZY,
        weight_exact: float = WEIGHT_EXACT,
    ) -> None:
        self._wv = weight_vector
        self._wf = weight_fuzzy
        self._we = weight_exact

    def compute_combined(
        self,
        vector_score: float,
        fuzzy_score: float,
        exact_score: float,
    ) -> float:
        """Compute a weighted combined score.

        All input scores are normalized to [0, 1] before combining.

        Args:
            vector_score: Cosine similarity [0.0, 1.0].
            fuzzy_score: RapidFuzz score [0.0, 100.0].
            exact_score: Exact match score [0.0, 100.0].

        Returns:
            Combined score in [0.0, 1.0].
        """
        # Normalize fuzzy and exact from [0, 100] to [0, 1]
        fuzzy_norm = fuzzy_score / 100.0
        exact_norm = exact_score / 100.0

        return (
            self._wv * vector_score
            + self._wf * fuzzy_norm
            + self._we * exact_norm
        )

    def build_candidates(
        self,
        software_list: list[Software],
        vector_scores: list[float],
        fuzzy_scores: list[float],
        exact_scores: list[float],
    ) -> list[MatchCandidate]:
        """Build MatchCandidate objects with combined scores, sorted by rank.

        Args:
            software_list: Candidate Software objects.
            vector_scores: Cosine similarity per candidate [0, 1].
            fuzzy_scores: Fuzzy scores per candidate [0, 100].
            exact_scores: Exact scores per candidate [0, 100].

        Returns:
            List of MatchCandidate, sorted by combined_score descending.
        """
        candidates: list[MatchCandidate] = []
        for sw, vs, fs, es in zip(
            software_list, vector_scores, fuzzy_scores, exact_scores, strict=True
        ):
            combined = self.compute_combined(vs, fs, es)
            candidates.append(
                MatchCandidate(
                    software=sw,
                    vector_score=vs,
                    fuzzy_score=fs,
                    exact_score=es,
                    combined_score=combined,
                )
            )

        candidates.sort(key=lambda c: c.combined_score, reverse=True)
        return candidates
