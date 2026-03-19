"""Tests for matcher.core.vectorizer.

Note: These tests require sentence-transformers and a model download.
They are marked with pytest.mark.slow and can be skipped in CI
with: pytest -m "not slow"
"""

from __future__ import annotations

import pytest

from shared.types import Software

# Try importing — skip all tests if dependencies missing
try:
    from matcher.core.vectorizer import Vectorizer

    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

pytestmark = pytest.mark.skipif(not HAS_DEPS, reason="sentence-transformers not installed")


@pytest.fixture(scope="module")
def vectorizer():
    """Shared vectorizer instance (model loading is expensive)."""
    return Vectorizer()


@pytest.fixture(scope="module")
def sample_software():
    return [
        Software(id="1", name="Apache HTTP Server", vendor="Apache", source="local_ppts"),
        Software(id="2", name="Nginx Web Server", vendor="Nginx", source="local_ppts"),
        Software(id="3", name="MySQL Database", vendor="Oracle", source="local_ppts"),
        Software(id="4", name="PostgreSQL", vendor="", source="local_ppts"),
        Software(id="5", name="Microsoft Windows 10", vendor="Microsoft", source="local_ppts"),
    ]


@pytest.fixture(scope="module")
def index(vectorizer, sample_software):
    embeddings, names = vectorizer.build_index(sample_software)
    return embeddings


class TestVectorizer:
    def test_encode_returns_correct_shape(self, vectorizer):
        embs = vectorizer.encode(["hello world", "test"])
        assert embs.shape[0] == 2
        assert embs.shape[1] > 0

    def test_build_index(self, vectorizer, sample_software, index):
        assert index.shape[0] == len(sample_software)

    def test_search_finds_similar(self, vectorizer, sample_software, index):
        results = vectorizer.search(
            "Apache HTTP", index, sample_software, top_n=3, threshold=0.3
        )
        assert len(results) > 0
        # Apache HTTP Server should be the top result
        top_name = results[0][0].name
        assert "Apache" in top_name

    def test_search_high_threshold_returns_empty(self, vectorizer, sample_software, index):
        results = vectorizer.search(
            "something completely unrelated xyz123",
            index,
            sample_software,
            top_n=3,
            threshold=0.99,
        )
        # Very high threshold — likely no results
        assert len(results) <= 1

    def test_search_respects_top_n(self, vectorizer, sample_software, index):
        results = vectorizer.search(
            "server", index, sample_software, top_n=2, threshold=0.1
        )
        assert len(results) <= 2

    def test_batch_search(self, vectorizer, sample_software, index):
        queries = ["Apache HTTP", "MySQL database", "Windows"]
        all_results = vectorizer.batch_search(
            queries, index, sample_software, top_n=2, threshold=0.3
        )
        assert len(all_results) == 3
        for results in all_results:
            assert len(results) <= 2

    def test_batch_search_empty(self, vectorizer, sample_software, index):
        results = vectorizer.batch_search([], index, sample_software)
        assert results == []
