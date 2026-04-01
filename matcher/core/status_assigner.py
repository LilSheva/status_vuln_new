"""Status assignment logic based on knowledge base rules and matching results."""

from __future__ import annotations

import logging
import re

from shared.constants import (
    MATCH_CONTAINS,
    MATCH_EXACT,
    MATCH_REGEX,
    MATCH_VECTOR,
    SOURCE_AUTO_NO_MATCH,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_MANUAL,
    STATUS_EMPTY,
    STATUS_NO,
)
from shared.types import (
    AnalysisResult,
    KnowledgeBaseRule,
    MatchCandidate,
    Software,
    Vulnerability,
)

logger = logging.getLogger(__name__)


class StatusAssigner:
    """Assign final statuses to vulnerabilities."""

    def check_knowledge_base(
        self,
        vuln: Vulnerability,
        rules: list[KnowledgeBaseRule],
    ) -> tuple[KnowledgeBaseRule | None, bool]:
        """Check a vulnerability against knowledge base rules.

        Args:
            vuln: The vulnerability to check.
            rules: Rules sorted by priority (exact -> contains -> regex -> vector).

        Returns:
            Tuple of (matched_rule, matched). If matched, the rule that matched.
        """
        for rule in rules:
            if self._rule_matches(vuln, rule):
                return rule, True
        return None, False

    def assign_status(
        self,
        vuln: Vulnerability,
        candidates: list[MatchCandidate],
        kb_rule: KnowledgeBaseRule | None = None,
    ) -> AnalysisResult:
        """Assign a final status to a vulnerability.

        Logic:
            1. If a knowledge base rule matched -> use its status.
            2. If no candidates at all -> STATUS_NO (auto).
            3. If candidates exist but no KB match -> STATUS_EMPTY (manual review).

        Args:
            vuln: The vulnerability.
            candidates: Ranked list of match candidates.
            kb_rule: Matched knowledge base rule (if any).

        Returns:
            AnalysisResult with the assigned status.
        """
        if kb_rule is not None:
            kb_candidate = MatchCandidate(
                software=Software(
                    id=kb_rule.ppts_id or "",
                    name=kb_rule.pattern,
                    vendor=kb_rule.vendor_pattern or "",
                    source="knowledge_base",
                ),
                vector_score=1.0,
                fuzzy_score=100.0,
                exact_score=100.0,
                combined_score=1.0,
            )
            return AnalysisResult(
                vulnerability=vuln,
                status=kb_rule.status,
                status_source=SOURCE_KNOWLEDGE_BASE,
                candidates=[kb_candidate],
                ppts_id=kb_rule.ppts_id,
            )

        if not candidates:
            return AnalysisResult(
                vulnerability=vuln,
                status=STATUS_NO,
                status_source=SOURCE_AUTO_NO_MATCH,
                candidates=[],
                ppts_id=None,
            )

        # Candidates exist but no definitive match -> manual review
        return AnalysisResult(
            vulnerability=vuln,
            status=STATUS_EMPTY,
            status_source=SOURCE_MANUAL,
            candidates=candidates,
            ppts_id=None,
        )

    def _rule_matches(self, vuln: Vulnerability, rule: KnowledgeBaseRule) -> bool:
        """Check if a single rule matches a vulnerability.

        A rule matches if BOTH vendor and product patterns match.
        An empty pattern means "match any" for that field.
        """
        # Check vendor pattern (empty = match any)
        if rule.vendor_pattern:
            if not self._pattern_matches(
                vuln.vendor, rule.vendor_pattern, rule.vendor_match_type, rule.id
            ):
                return False

        # Check product pattern (empty = match any)
        if rule.pattern:
            if not self._pattern_matches(
                vuln.product, rule.pattern, rule.match_type, rule.id
            ):
                # Also try against raw_text as fallback
                if not self._pattern_matches(
                    vuln.raw_text, rule.pattern, rule.match_type, rule.id
                ):
                    return False

        # At least one pattern must be non-empty
        if not rule.vendor_pattern and not rule.pattern:
            return False

        return True

    def _pattern_matches(
        self, text: str, pattern: str, match_type: str, rule_id: int | None
    ) -> bool:
        """Check if a pattern matches a text string."""
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        if match_type == MATCH_EXACT:
            return text_lower == pattern_lower

        if match_type == MATCH_CONTAINS:
            return pattern_lower in text_lower

        if match_type == MATCH_REGEX:
            try:
                return bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                logger.warning("Invalid regex in rule %s: %r", rule_id, pattern)
                return False

        if match_type == MATCH_VECTOR:
            return False

        return False
