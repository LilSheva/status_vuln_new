"""Pipeline orchestrator: runs the full vulnerability analysis workflow."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING, Protocol

from shared.constants import SOURCE_JOURNAL
from shared.db.repository import bulk_get_active_rules, get_enabled_scripts, increment_match_count
from shared.types import (
    AnalysisResult,
    JournalEntry,
    MatchCandidate,
    PipelineSettings,
    Software,
    Vulnerability,
)

from .exact_matcher import ExactMatcher
from .fuzzy_matcher import FuzzyMatcher
from .normalizer import normalize_text
from .preprocessor import Preprocessor
from .scorer import Scorer
from .status_assigner import StatusAssigner
from .vectorizer import Vectorizer

if TYPE_CHECKING:
    from collections.abc import Callable

    import numpy as np
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for reporting pipeline progress."""

    def __call__(self, stage: str, current: int, total: int) -> None: ...


def _noop_progress(stage: str, current: int, total: int) -> None:
    """Default no-op progress callback."""


class Pipeline:
    """Orchestrate the full vulnerability matching pipeline.

    Stages:
        0. Journal check (if journal files provided — match by CVE)
        1. Preprocessing (plugin scripts)
        2. Knowledge base check (if enabled)
        3. Vector search (embeddings + cosine similarity)
        4. Normalization + Fuzzy matching
        5. Exact matching
        6. Combined scoring + Status assignment
    """

    def __init__(self, settings: PipelineSettings | None = None) -> None:
        self._settings = settings or PipelineSettings()
        self._preprocessor = Preprocessor()
        self._vectorizer = Vectorizer()
        self._fuzzy_matcher = FuzzyMatcher(
            threshold=self._settings.fuzzy_threshold,
            min_word_length=self._settings.min_word_length,
        )
        self._exact_matcher = ExactMatcher()
        self._scorer = Scorer()
        self._status_assigner = StatusAssigner()
        self._progress: ProgressCallback = _noop_progress
        self._kb_conn: sqlite3.Connection | None = None

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set a callback for progress reporting."""
        self._progress = callback

    def run(
        self,
        vulnerabilities: list[Vulnerability],
        software_list: list[Software],
        journal_entries: list[JournalEntry] | None = None,
    ) -> list[AnalysisResult]:
        """Run the full analysis pipeline.

        Args:
            vulnerabilities: Loaded vulnerability entries from TSU.
            software_list: Loaded software entries from PPTS.
            journal_entries: Historical journal entries for CVE lookup.

        Returns:
            List of AnalysisResult for each vulnerability.
        """
        total = len(vulnerabilities)
        logger.info(
            "Pipeline started: %d vulnerabilities, %d software entries, %d journal entries",
            total,
            len(software_list),
            len(journal_entries) if journal_entries else 0,
        )

        # --- Stage 0: Build journal index ---
        journal_index: dict[str, JournalEntry] = {}
        if journal_entries:
            self._progress("Загрузка журналов", 0, 1)
            for entry in journal_entries:
                cve = entry.cve_id.strip().upper()
                if cve:
                    # Keep the first occurrence (most recent journal loaded first)
                    if cve not in journal_index:
                        journal_index[cve] = entry
            self._progress("Загрузка журналов", 1, 1)
            logger.info("Journal index: %d unique CVEs", len(journal_index))

        # --- Stage 1: Preprocessing ---
        self._progress("Препроцессинг", 0, total)
        vulns = self._run_preprocessing(vulnerabilities)

        # --- Stage 2: Knowledge base ---
        kb_rules = []
        if self._settings.use_knowledge_base and self._settings.kb_path:
            self._progress("Проверка по базе знаний", 0, total)
            kb_rules = self._load_kb_rules()

        # --- Stage 3: Build vector index ---
        self._progress("Построение векторного индекса", 0, 1)
        index_embeddings, _ = self._vectorizer.build_index(software_list)
        self._progress("Построение векторного индекса", 1, 1)

        # --- Stage 4-6: Process each vulnerability ---
        results: list[AnalysisResult] = []
        for i, vuln in enumerate(vulns):
            self._progress("Анализ уязвимостей", i, total)
            result = self._process_single(
                vuln, software_list, index_embeddings, kb_rules, journal_index
            )
            results.append(result)

        self._progress("Анализ уязвимостей", total, total)

        # Close KB connection if opened
        if self._kb_conn is not None:
            self._kb_conn.close()
            self._kb_conn = None

        n_journal = sum(1 for r in results if r.status_source == SOURCE_JOURNAL)
        logger.info(
            "Pipeline complete: %d results (%d from journal, %d НЕТ, %d manual review)",
            len(results),
            n_journal,
            sum(1 for r in results if r.status == "НЕТ"),
            sum(1 for r in results if r.status == ""),
        )
        return results

    def _run_preprocessing(
        self, vulnerabilities: list[Vulnerability]
    ) -> list[Vulnerability]:
        """Run preprocessing scripts on vulnerabilities."""
        if not self._settings.use_knowledge_base or not self._settings.kb_path:
            return vulnerabilities

        try:
            from shared.db.models import get_connection

            conn = get_connection(self._settings.kb_path)
            configs = get_enabled_scripts(conn)
            conn.close()
        except Exception:
            logger.exception("Failed to load script configs")
            return vulnerabilities

        if not configs:
            return vulnerabilities

        entries = [
            {
                "cve_id": v.cve_id,
                "vendor": v.vendor,
                "product": v.product,
                "version": v.version,
                "raw_text": v.raw_text,
            }
            for v in vulnerabilities
        ]

        processed = self._preprocessor.process(entries, configs)

        return [
            Vulnerability(
                cve_id=e.get("cve_id", ""),
                vendor=e.get("vendor", ""),
                product=e.get("product", ""),
                version=e.get("version", ""),
                raw_text=e.get("raw_text", ""),
            )
            for e in processed
        ]

    def _load_kb_rules(self) -> list:
        """Load knowledge base rules from SQLite."""
        try:
            from shared.db.models import get_connection

            self._kb_conn = get_connection(self._settings.kb_path)
            rules = bulk_get_active_rules(self._kb_conn)
            logger.info("Loaded %d knowledge base rules", len(rules))
            return rules
        except Exception:
            logger.exception("Failed to load knowledge base")
            return []

    def _process_single(
        self,
        vuln: Vulnerability,
        software_list: list[Software],
        index_embeddings: NDArray[np.float32],
        kb_rules: list,
        journal_index: dict[str, JournalEntry],
    ) -> AnalysisResult:
        """Process a single vulnerability through the full matching pipeline."""

        # Step 0: Check journal by CVE
        if journal_index and vuln.cve_id:
            cve_key = vuln.cve_id.strip().upper()
            journal_hit = journal_index.get(cve_key)
            if journal_hit is not None and journal_hit.status:
                return AnalysisResult(
                    vulnerability=vuln,
                    status=journal_hit.status,
                    status_source=SOURCE_JOURNAL,
                    candidates=[],
                    ppts_id=journal_hit.ppts_id or None,
                    responsible=journal_hit.responsible or None,
                )

        # Step 1: Check knowledge base
        if kb_rules:
            matched_rule, matched = self._status_assigner.check_knowledge_base(
                vuln, kb_rules
            )
            if matched and matched_rule is not None:
                if self._kb_conn is not None and matched_rule.id is not None:
                    increment_match_count(self._kb_conn, matched_rule.id)
                return self._status_assigner.assign_status(
                    vuln, [], kb_rule=matched_rule
                )

        # Step 2: Vector search for top-N candidates
        vector_results = self._vectorizer.search(
            vuln.raw_text,
            index_embeddings,
            software_list,
            top_n=self._settings.top_n,
            threshold=self._settings.vector_threshold,
        )

        if not vector_results:
            return self._status_assigner.assign_status(vuln, [])

        # Step 3: Normalize + Fuzzy + Exact on candidates
        candidate_sw = [sw for sw, _ in vector_results]
        vector_scores = [score for _, score in vector_results]

        normalized_query = normalize_text(
            vuln.raw_text,
            direction=self._settings.transliteration_direction,
        )
        normalized_names = [
            normalize_text(sw.name, direction=self._settings.transliteration_direction)
            for sw in candidate_sw
        ]

        fuzzy_scores = self._fuzzy_matcher.score_candidates(
            normalized_query, normalized_names
        )
        exact_scores = self._exact_matcher.score_candidates(
            normalized_query, normalized_names
        )

        # Step 4: Combined scoring
        candidates = self._scorer.build_candidates(
            candidate_sw, vector_scores, fuzzy_scores, exact_scores
        )

        # Step 5: Status assignment
        return self._status_assigner.assign_status(vuln, candidates)
