"""Tests for the Knowledge Base — rule editor logic and rule tester matching."""

from __future__ import annotations

import re

import pytest

from shared.constants import MATCH_CONTAINS, MATCH_EXACT, MATCH_REGEX, MATCH_VECTOR
from shared.db.models import init_db
from shared.db.repository import (
    create_rule,
    delete_rule,
    get_rule_by_id,
    search_rules,
    update_rule,
)
from shared.types import KnowledgeBaseRule


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test_kb.db"
    connection = init_db(db_path)
    yield connection
    connection.close()


class TestKnowledgeBaseWorkflow:
    """End-to-end workflow tests simulating KB GUI operations."""

    def test_create_exact_rule(self, conn):
        rule = KnowledgeBaseRule(
            pattern="Apache HTTP Server",
            match_type=MATCH_EXACT,
            status="НЕТ",
            comment="Test exact rule",
        )
        rule_id = create_rule(conn, rule)
        fetched = get_rule_by_id(conn, rule_id)
        assert fetched.pattern == "Apache HTTP Server"
        assert fetched.match_type == MATCH_EXACT
        assert fetched.status == "НЕТ"

    def test_create_contains_rule(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(
                pattern="linux",
                match_type=MATCH_CONTAINS,
                status="ЛИНУКС",
            ),
        )
        fetched = get_rule_by_id(conn, rule_id)
        assert fetched.status == "ЛИНУКС"

    def test_create_regex_rule(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(
                pattern=r"Apache.*Server\s+\d+",
                match_type=MATCH_REGEX,
                status="ДА",
                ppts_id="SW-100",
            ),
        )
        fetched = get_rule_by_id(conn, rule_id)
        assert fetched.ppts_id == "SW-100"
        # Verify regex compiles
        assert re.compile(fetched.pattern)

    def test_create_vector_rule_with_threshold(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(
                pattern="apache http",
                match_type=MATCH_VECTOR,
                status="ДА",
                vector_threshold=0.85,
            ),
        )
        fetched = get_rule_by_id(conn, rule_id)
        assert fetched.vector_threshold == 0.85

    def test_edit_rule(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(pattern="old pattern", match_type=MATCH_EXACT, status="НЕТ"),
        )
        rule = get_rule_by_id(conn, rule_id)
        rule.pattern = "new pattern"
        rule.status = "ДА"
        rule.comment = "Updated via editor"
        update_rule(conn, rule)

        updated = get_rule_by_id(conn, rule_id)
        assert updated.pattern == "new pattern"
        assert updated.status == "ДА"
        assert updated.comment == "Updated via editor"

    def test_delete_rule(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(pattern="to delete", match_type=MATCH_EXACT, status="НЕТ"),
        )
        assert delete_rule(conn, rule_id) is True
        assert get_rule_by_id(conn, rule_id) is None

    def test_search_by_pattern(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="apache", match_type=MATCH_EXACT, status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="nginx", match_type=MATCH_EXACT, status="НЕТ"))
        create_rule(conn, KnowledgeBaseRule(pattern="apache tomcat", match_type=MATCH_CONTAINS, status="ДА"))

        results = search_rules(conn, pattern="apache")
        assert len(results) == 2

    def test_search_by_status_and_type(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="a", match_type=MATCH_EXACT, status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="b", match_type=MATCH_CONTAINS, status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="c", match_type=MATCH_EXACT, status="НЕТ"))

        results = search_rules(conn, match_type=MATCH_EXACT, status="ДА")
        assert len(results) == 1
        assert results[0].pattern == "a"


class TestRuleTesterLogic:
    """Test the matching logic used in rule_tester."""

    def _match(self, rule: KnowledgeBaseRule, text: str) -> bool:
        """Simulate rule_tester matching logic."""
        pattern = rule.pattern.lower()
        text_lower = text.lower()

        if rule.match_type == MATCH_EXACT:
            return text_lower == pattern
        if rule.match_type == MATCH_CONTAINS:
            return pattern in text_lower
        if rule.match_type == MATCH_REGEX:
            try:
                return bool(re.search(rule.pattern, text, re.IGNORECASE))
            except re.error:
                return False
        return False

    def test_exact_match(self):
        rule = KnowledgeBaseRule(pattern="Apache HTTP Server", match_type=MATCH_EXACT, status="ДА")
        assert self._match(rule, "apache http server") is True
        assert self._match(rule, "Apache HTTP Server") is True
        assert self._match(rule, "Apache HTTP Server 2.4") is False

    def test_contains_match(self):
        rule = KnowledgeBaseRule(pattern="linux", match_type=MATCH_CONTAINS, status="ЛИНУКС")
        assert self._match(rule, "Ubuntu Linux 22.04") is True
        assert self._match(rule, "Red Hat Enterprise Linux") is True
        assert self._match(rule, "Windows 10") is False

    def test_regex_match(self):
        rule = KnowledgeBaseRule(
            pattern=r"Apache.*Server\s+\d+\.\d+",
            match_type=MATCH_REGEX,
            status="ДА",
        )
        assert self._match(rule, "Apache HTTP Server 2.4") is True
        assert self._match(rule, "Apache Tomcat Server 9.0") is True
        assert self._match(rule, "Apache") is False

    def test_regex_invalid_pattern(self):
        rule = KnowledgeBaseRule(pattern=r"[invalid", match_type=MATCH_REGEX, status="ДА")
        assert self._match(rule, "anything") is False

    def test_vector_not_testable(self):
        rule = KnowledgeBaseRule(pattern="apache", match_type=MATCH_VECTOR, status="ДА")
        assert self._match(rule, "apache") is False
