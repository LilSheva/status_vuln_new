"""Pipeline orchestrator: runs the full vulnerability analysis workflow."""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from shared.constants import SOURCE_JOURNAL, STATUS_REPEAT
from shared.db.repository import bulk_get_active_rules, get_enabled_scripts, increment_match_count
from shared.types import (
    AnalysisResult,
    JournalEntry,
    PipelineSettings,
    ScriptConfig,
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

    import numpy as np
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class ProgressCallback(Protocol):
    """Protocol for reporting pipeline progress."""

    def __call__(self, stage: str, current: int, total: int) -> None: ...


def _noop_progress(stage: str, current: int, total: int) -> None:
    """Default no-op progress callback."""


class Pipeline:
    """Orchestrate the full vulnerability matching pipeline."""

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
        """Run the full analysis pipeline on vulnerabilities against software list."""
        total = len(vulnerabilities)
        logger.info(
            "Pipeline started: %d vulnerabilities, %d software entries, %d journal entries",
            total,
            len(software_list),
            len(journal_entries) if journal_entries else 0,
        )

        journal_index: dict[str, list[JournalEntry]] = {}
        if journal_entries:
            self._progress("Загрузка журналов", 0, 1)
            for entry in journal_entries:
                cve = entry.cve_id.strip().upper()
                if cve:
                    journal_index.setdefault(cve, []).append(entry)
            self._progress("Загрузка журналов", 1, 1)
            logger.info("Journal index: %d unique CVEs", len(journal_index))
            for cve_key in list(journal_index)[:10]:
                logger.debug("  journal CVE: %r (%d entries)", cve_key, len(journal_index[cve_key]))

        self._progress("Препроцессинг", 0, total)
        vulns = self._run_preprocessing(vulnerabilities)

        kb_rules = []
        if self._settings.use_knowledge_base and self._settings.kb_path:
            self._progress("Проверка по базе знаний", 0, total)
            kb_rules = self._load_kb_rules()

        self._progress("Построение векторного индекса", 0, 1)
        index_embeddings, _ = self._vectorizer.build_index(software_list)
        self._progress("Построение векторного индекса", 1, 1)

        results: list[AnalysisResult] = []
        for i, vuln in enumerate(vulns):
            self._progress("Анализ уязвимостей", i, total)
            result = self._process_single(
                vuln, software_list, index_embeddings, kb_rules, journal_index
            )
            results.append(result)

        self._progress("Анализ уязвимостей", total, total)

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
        """Run preprocessing scripts (from KB config or auto-discovered)."""
        if not self._settings.use_preprocessing:
            return vulnerabilities

        configs: list[ScriptConfig] = []

        if self._settings.use_knowledge_base and self._settings.kb_path:
            try:
                from shared.db.models import get_connection

                conn = get_connection(self._settings.kb_path)
                configs = get_enabled_scripts(conn)
                conn.close()
            except Exception:
                logger.exception("Failed to load script configs from KB")

        if not configs:
            scripts_dir = Path(self._settings.scripts_dir)
            if scripts_dir.is_dir():
                for py_file in sorted(scripts_dir.glob("*.py")):
                    if py_file.name.startswith("_"):
                        continue
                    configs.append(
                        ScriptConfig(
                            script_path=str(py_file),
                            condition="",
                            priority=0,
                            enabled=True,
                        )
                    )
                if configs:
                    logger.info(
                        "Auto-discovered %d preprocessing scripts from %s",
                        len(configs),
                        scripts_dir,
                    )

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

    def _apply_journal(
        self, result: AnalysisResult, journal_hits: list[JournalEntry]
    ) -> AnalysisResult:
        """Override result with ПОВТОР if journal matches exist."""
        if journal_hits:
            result.status = STATUS_REPEAT
            result.status_source = SOURCE_JOURNAL
            result.ppts_id = None
            result.journal_matches = journal_hits
        return result

    def _process_single(
        self,
        vuln: Vulnerability,
        software_list: list[Software],
        index_embeddings: NDArray[np.float32],
        kb_rules: list,
        journal_index: dict[str, list[JournalEntry]],
    ) -> AnalysisResult:
        """Process a single vulnerability through the full matching pipeline."""

        if vuln.cve_id and not re.match(r"CVE-\d{4}-\d{4,}", vuln.cve_id):
            logger.info(
                "CVE не найден в базе. Возможно, это 0-day... или опечатка: %s",
                vuln.cve_id,
            )

        cve_key = vuln.cve_id.strip().upper() if vuln.cve_id else ""
        journal_hits = journal_index.get(cve_key, []) if journal_index and cve_key else []

        # Journal hit without recheck → return immediately
        if journal_hits and not self._settings.journal_recheck:
            return AnalysisResult(
                vulnerability=vuln,
                status=STATUS_REPEAT,
                status_source=SOURCE_JOURNAL,
                candidates=[],
                ppts_id=None,
                responsible=None,
                journal_matches=journal_hits,
            )

        # KB check
        if kb_rules:
            matched_rule, matched = self._status_assigner.check_knowledge_base(
                vuln, kb_rules
            )
            if matched and matched_rule is not None:
                if self._kb_conn is not None and matched_rule.id is not None:
                    increment_match_count(self._kb_conn, matched_rule.id)
                result = self._status_assigner.assign_status(vuln, [], kb_rule=matched_rule)
                return self._apply_journal(result, journal_hits)

        # Vector search (all top-N, threshold checked separately)
        all_vector_results = self._vectorizer.search(
            vuln.raw_text,
            index_embeddings,
            software_list,
            top_n=self._settings.top_n,
            threshold=0.0,
        )

        if not all_vector_results or not any(
            s >= self._settings.vector_threshold for _, s in all_vector_results
        ):
            result = self._status_assigner.assign_status(vuln, [])
            return self._apply_journal(result, journal_hits)

        candidate_sw = [sw for sw, _ in all_vector_results]
        vector_scores = [score for _, score in all_vector_results]

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

        candidates = self._scorer.build_candidates(
            candidate_sw, vector_scores, fuzzy_scores, exact_scores
        )

        result = self._status_assigner.assign_status(vuln, candidates)
        return self._apply_journal(result, journal_hits)
