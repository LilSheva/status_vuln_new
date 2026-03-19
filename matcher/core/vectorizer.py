"""Vector search using sentence-transformers and cosine similarity."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from shared.constants import DEFAULT_TOP_N, DEFAULT_VECTOR_THRESHOLD, EMBEDDING_MODEL_NAME

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from shared.types import Software

logger = logging.getLogger(__name__)


class Vectorizer:
    """Encode texts with sentence-transformers and find nearest neighbors."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None

    def _ensure_model(self) -> SentenceTransformer:
        """Lazy-load the embedding model."""
        if self._model is None:
            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
            logger.info("Model loaded successfully")
        return self._model

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        """Encode a list of texts into embedding vectors.

        Args:
            texts: List of strings to encode.

        Returns:
            2D numpy array of shape (len(texts), embedding_dim).
        """
        model = self._ensure_model()
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return embeddings  # type: ignore[return-value]

    def build_index(self, software_list: list[Software]) -> tuple[NDArray[np.float32], list[str]]:
        """Build an embedding index from a list of Software entries.

        Args:
            software_list: List of Software objects.

        Returns:
            Tuple of (embeddings array, list of software names used for encoding).
        """
        names = [
            f"{sw.vendor} {sw.name}".strip() if sw.vendor else sw.name
            for sw in software_list
        ]
        logger.info("Encoding %d software entries...", len(names))
        embeddings = self.encode(names)
        logger.info("Index built: %d entries, %d dimensions", *embeddings.shape)
        return embeddings, names

    def search(
        self,
        query: str,
        index_embeddings: NDArray[np.float32],
        software_list: list[Software],
        top_n: int = DEFAULT_TOP_N,
        threshold: float = DEFAULT_VECTOR_THRESHOLD,
    ) -> list[tuple[Software, float]]:
        """Find top-N most similar software entries for a query.

        Args:
            query: Query text (vulnerability raw_text).
            index_embeddings: Pre-computed embeddings for software list.
            software_list: List of Software objects (same order as index).
            top_n: Number of top candidates to return.
            threshold: Minimum cosine similarity to include.

        Returns:
            List of (Software, score) tuples, sorted by score descending.
        """
        query_emb = self.encode([query])  # shape (1, dim)
        scores = cosine_similarity(query_emb, index_embeddings)[0]  # shape (n,)

        # Get top-N indices above threshold
        candidate_indices = np.where(scores >= threshold)[0]
        if len(candidate_indices) == 0:
            return []

        # Sort by score descending, take top_n
        sorted_idx = candidate_indices[np.argsort(scores[candidate_indices])[::-1]][:top_n]

        results: list[tuple[Software, float]] = []
        for idx in sorted_idx:
            results.append((software_list[idx], float(scores[idx])))

        return results

    def batch_search(
        self,
        queries: list[str],
        index_embeddings: NDArray[np.float32],
        software_list: list[Software],
        top_n: int = DEFAULT_TOP_N,
        threshold: float = DEFAULT_VECTOR_THRESHOLD,
    ) -> list[list[tuple[Software, float]]]:
        """Batch search: find top-N candidates for multiple queries at once.

        Args:
            queries: List of query texts.
            index_embeddings: Pre-computed embeddings for software list.
            software_list: List of Software objects.
            top_n: Number of top candidates per query.
            threshold: Minimum cosine similarity.

        Returns:
            List of result lists, one per query.
        """
        if not queries:
            return []

        query_embs = self.encode(queries)  # shape (q, dim)
        all_scores = cosine_similarity(query_embs, index_embeddings)  # shape (q, n)

        all_results: list[list[tuple[Software, float]]] = []
        for i in range(len(queries)):
            scores = all_scores[i]
            candidate_indices = np.where(scores >= threshold)[0]
            if len(candidate_indices) == 0:
                all_results.append([])
                continue

            sorted_idx = candidate_indices[np.argsort(scores[candidate_indices])[::-1]][:top_n]
            results = [(software_list[idx], float(scores[idx])) for idx in sorted_idx]
            all_results.append(results)

        return all_results
