"""Tests for matcher.core.fuzzy_matcher."""

from __future__ import annotations

from matcher.core.fuzzy_matcher import FuzzyMatcher


class TestFuzzyMatcher:
    def setup_method(self):
        self.matcher = FuzzyMatcher(threshold=75, min_word_length=3)

    def test_identical_strings(self):
        score = self.matcher.score("Apache HTTP Server", "Apache HTTP Server")
        assert score == 100.0

    def test_similar_strings(self):
        score = self.matcher.score("Apache HTTP Server", "Apache Http Server 2.4")
        assert score > 70.0

    def test_different_strings(self):
        score = self.matcher.score("Apache HTTP Server", "MySQL Database")
        assert score < 50.0

    def test_empty_strings(self):
        assert self.matcher.score("", "something") == 0.0
        assert self.matcher.score("something", "") == 0.0
        assert self.matcher.score("", "") == 0.0

    def test_is_match_true(self):
        assert self.matcher.is_match("Apache HTTP Server", "Apache HTTP Server 2.4")

    def test_is_match_false(self):
        assert not self.matcher.is_match("Apache HTTP Server", "MySQL Database")

    def test_score_candidates(self):
        scores = self.matcher.score_candidates(
            "Apache HTTP",
            ["Apache HTTP Server", "Nginx Web Server", "Apache Tomcat"],
        )
        assert len(scores) == 3
        assert scores[0] > scores[1]  # Apache HTTP Server should score higher than Nginx

    def test_short_words_filtered(self):
        # "a" and "to" should be filtered out (< 3 chars)
        m = FuzzyMatcher(threshold=75, min_word_length=3)
        score = m.score("a to do something", "something else")
        assert score > 0  # "something" should still match

    def test_case_insensitive(self):
        score_a = self.matcher.score("APACHE", "apache")
        score_b = self.matcher.score("apache", "APACHE")
        assert score_a == score_b
        assert score_a == 100.0
