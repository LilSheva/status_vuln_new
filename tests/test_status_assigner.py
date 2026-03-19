"""Tests for matcher.core.status_assigner."""

from __future__ import annotations

from matcher.core.status_assigner import StatusAssigner
from shared.constants import (
    SOURCE_AUTO_NO_MATCH,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_MANUAL,
    STATUS_EMPTY,
    STATUS_NO,
)
from shared.types import KnowledgeBaseRule, MatchCandidate, Software, Vulnerability


def _vuln(raw_text: str = "Apache HTTP Server 2.4") -> Vulnerability:
    return Vulnerability(
        cve_id="CVE-2024-001",
        vendor="Apache",
        product="HTTP Server",
        version="2.4",
        raw_text=raw_text,
    )


def _candidate(name: str = "Apache HTTP Server") -> MatchCandidate:
    sw = Software(id="1", name=name, vendor="", source="local_ppts")
    return MatchCandidate(software=sw, vector_score=0.8, fuzzy_score=90.0, exact_score=75.0, combined_score=0.8)


class TestStatusAssigner:
    def setup_method(self):
        self.assigner = StatusAssigner()

    # --- Knowledge base matching ---

    def test_exact_rule_match(self):
        rule = KnowledgeBaseRule(
            id=1, pattern="apache http server 2.4", match_type="exact", status="ДА"
        )
        matched_rule, matched = self.assigner.check_knowledge_base(_vuln(), [rule])
        assert matched is True
        assert matched_rule is rule

    def test_contains_rule_match(self):
        rule = KnowledgeBaseRule(
            id=2, pattern="apache", match_type="contains", status="НЕТ"
        )
        _, matched = self.assigner.check_knowledge_base(_vuln(), [rule])
        assert matched is True

    def test_regex_rule_match(self):
        rule = KnowledgeBaseRule(
            id=3, pattern=r"Apache.*Server", match_type="regex", status="ЛИНУКС"
        )
        _, matched = self.assigner.check_knowledge_base(_vuln(), [rule])
        assert matched is True

    def test_regex_invalid_pattern(self):
        rule = KnowledgeBaseRule(
            id=4, pattern=r"[invalid", match_type="regex", status="ДА"
        )
        _, matched = self.assigner.check_knowledge_base(_vuln(), [rule])
        assert matched is False

    def test_vector_rule_skipped(self):
        rule = KnowledgeBaseRule(
            id=5, pattern="apache", match_type="vector", status="ДА"
        )
        _, matched = self.assigner.check_knowledge_base(_vuln(), [rule])
        assert matched is False

    def test_no_rule_matches(self):
        rule = KnowledgeBaseRule(
            id=6, pattern="nginx", match_type="exact", status="ДА"
        )
        _, matched = self.assigner.check_knowledge_base(_vuln(), [rule])
        assert matched is False

    # --- Status assignment ---

    def test_kb_rule_assigns_status(self):
        rule = KnowledgeBaseRule(
            id=1, pattern="apache", match_type="contains", status="ДА", ppts_id="SW-001"
        )
        result = self.assigner.assign_status(_vuln(), [_candidate()], kb_rule=rule)
        assert result.status == "ДА"
        assert result.status_source == SOURCE_KNOWLEDGE_BASE
        assert result.ppts_id == "SW-001"

    def test_no_candidates_assigns_no(self):
        result = self.assigner.assign_status(_vuln(), [])
        assert result.status == STATUS_NO
        assert result.status_source == SOURCE_AUTO_NO_MATCH

    def test_candidates_without_kb_assigns_empty(self):
        result = self.assigner.assign_status(_vuln(), [_candidate()])
        assert result.status == STATUS_EMPTY
        assert result.status_source == SOURCE_MANUAL
        assert len(result.candidates) == 1

    def test_first_matching_rule_wins(self):
        rules = [
            KnowledgeBaseRule(id=1, pattern="nginx", match_type="exact", status="НЕТ"),
            KnowledgeBaseRule(id=2, pattern="apache", match_type="contains", status="ДА"),
            KnowledgeBaseRule(id=3, pattern="http", match_type="contains", status="ЛИНУКС"),
        ]
        matched_rule, matched = self.assigner.check_knowledge_base(_vuln(), rules)
        assert matched is True
        assert matched_rule.id == 2  # First match by order
        assert matched_rule.status == "ДА"
