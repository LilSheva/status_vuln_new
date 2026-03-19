"""Tests for matcher.core.scorer."""

from __future__ import annotations

from matcher.core.scorer import Scorer
from shared.types import Software


class TestScorer:
    def setup_method(self):
        self.scorer = Scorer()

    def test_perfect_scores(self):
        combined = self.scorer.compute_combined(1.0, 100.0, 100.0)
        assert combined == 1.0

    def test_zero_scores(self):
        combined = self.scorer.compute_combined(0.0, 0.0, 0.0)
        assert combined == 0.0

    def test_vector_weighted_more(self):
        # vector=1.0, fuzzy=0, exact=0 -> 0.5
        # vector=0, fuzzy=100, exact=0 -> 0.3
        score_v = self.scorer.compute_combined(1.0, 0.0, 0.0)
        score_f = self.scorer.compute_combined(0.0, 100.0, 0.0)
        assert score_v > score_f

    def test_build_candidates_sorted(self):
        sw_a = Software(id="1", name="A", vendor="", source="local_ppts")
        sw_b = Software(id="2", name="B", vendor="", source="local_ppts")
        sw_c = Software(id="3", name="C", vendor="", source="local_ppts")

        candidates = self.scorer.build_candidates(
            [sw_a, sw_b, sw_c],
            vector_scores=[0.3, 0.9, 0.5],
            fuzzy_scores=[50.0, 80.0, 90.0],
            exact_scores=[0.0, 100.0, 0.0],
        )
        assert len(candidates) == 3
        # B should be first (highest combined)
        assert candidates[0].software.name == "B"
        # Scores should be descending
        assert candidates[0].combined_score >= candidates[1].combined_score
        assert candidates[1].combined_score >= candidates[2].combined_score

    def test_build_candidates_preserves_individual_scores(self):
        sw = Software(id="1", name="Test", vendor="", source="local_ppts")
        candidates = self.scorer.build_candidates(
            [sw],
            vector_scores=[0.8],
            fuzzy_scores=[90.0],
            exact_scores=[75.0],
        )
        c = candidates[0]
        assert c.vector_score == 0.8
        assert c.fuzzy_score == 90.0
        assert c.exact_score == 75.0
        assert c.combined_score > 0
