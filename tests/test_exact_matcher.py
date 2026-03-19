"""Tests for matcher.core.exact_matcher."""

from __future__ import annotations

from matcher.core.exact_matcher import ExactMatcher


class TestExactMatcher:
    def setup_method(self):
        self.matcher = ExactMatcher()

    def test_exact_match(self):
        assert self.matcher.score("Apache HTTP Server", "apache http server") == 100.0

    def test_query_substring_of_candidate(self):
        assert self.matcher.score("Apache", "Apache HTTP Server 2.4") == 75.0

    def test_candidate_substring_of_query(self):
        assert self.matcher.score("Apache HTTP Server 2.4", "Apache") == 75.0

    def test_all_words_present(self):
        assert self.matcher.score("Apache HTTP", "Apache HTTP Server") == 75.0  # substring

    def test_word_subset(self):
        # "Server Apache" has both words in "Apache HTTP Server" but not as substring
        score = self.matcher.score("Server Apache", "Apache HTTP Server")
        assert score == 50.0

    def test_no_match(self):
        assert self.matcher.score("PostgreSQL", "MySQL") == 0.0

    def test_empty_strings(self):
        assert self.matcher.score("", "something") == 0.0
        assert self.matcher.score("something", "") == 0.0

    def test_score_candidates(self):
        scores = self.matcher.score_candidates(
            "Apache",
            ["Apache HTTP Server", "Nginx", "Apache"],
        )
        assert scores == [75.0, 0.0, 100.0]
