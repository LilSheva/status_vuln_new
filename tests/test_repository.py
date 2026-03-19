"""Tests for shared.db.repository CRUD operations."""

from __future__ import annotations

import pytest

from shared.db.models import init_db
from shared.db.repository import (
    bulk_get_active_rules,
    create_rule,
    create_script_config,
    delete_rule,
    delete_script_config,
    get_all_rules,
    get_all_scripts,
    get_enabled_scripts,
    get_rule_by_id,
    increment_match_count,
    search_rules,
    update_rule,
    update_script_config,
)
from shared.types import KnowledgeBaseRule, ScriptConfig


@pytest.fixture
def conn(tmp_path):
    """Create a fresh in-memory-like temp database for each test."""
    db_path = tmp_path / "test.db"
    connection = init_db(db_path)
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Rules tests
# ---------------------------------------------------------------------------


class TestRulesCRUD:
    def test_create_and_get(self, conn):
        rule = KnowledgeBaseRule(
            pattern="apache http server",
            match_type="contains",
            status="ДА",
            comment="test rule",
        )
        rule_id = create_rule(conn, rule)
        assert rule_id is not None
        assert rule_id > 0

        fetched = get_rule_by_id(conn, rule_id)
        assert fetched is not None
        assert fetched.pattern == "apache http server"
        assert fetched.match_type == "contains"
        assert fetched.status == "ДА"
        assert fetched.comment == "test rule"
        assert fetched.match_count == 0

    def test_get_all_rules(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="a", match_type="exact", status="НЕТ"))
        create_rule(conn, KnowledgeBaseRule(pattern="b", match_type="exact", status="НЕТ"))
        rules = get_all_rules(conn)
        assert len(rules) == 2

    def test_update_rule(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(pattern="old", match_type="exact", status="НЕТ"),
        )
        rule = get_rule_by_id(conn, rule_id)
        rule.pattern = "new"
        rule.status = "ДА"
        assert update_rule(conn, rule) is True

        updated = get_rule_by_id(conn, rule_id)
        assert updated.pattern == "new"
        assert updated.status == "ДА"

    def test_delete_rule(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(pattern="to_delete", match_type="exact", status="НЕТ"),
        )
        assert delete_rule(conn, rule_id) is True
        assert get_rule_by_id(conn, rule_id) is None
        assert delete_rule(conn, 9999) is False

    def test_get_nonexistent_rule(self, conn):
        assert get_rule_by_id(conn, 9999) is None

    def test_search_by_pattern(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="apache http", match_type="exact", status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="nginx", match_type="exact", status="НЕТ"))
        results = search_rules(conn, pattern="apache")
        assert len(results) == 1
        assert results[0].pattern == "apache http"

    def test_search_by_status(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="a", match_type="exact", status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="b", match_type="exact", status="НЕТ"))
        create_rule(conn, KnowledgeBaseRule(pattern="c", match_type="exact", status="ДА"))
        results = search_rules(conn, status="ДА")
        assert len(results) == 2

    def test_search_by_match_type(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="a", match_type="exact", status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="b", match_type="regex", status="ДА"))
        results = search_rules(conn, match_type="regex")
        assert len(results) == 1

    def test_increment_match_count(self, conn):
        rule_id = create_rule(
            conn,
            KnowledgeBaseRule(pattern="test", match_type="exact", status="ДА"),
        )
        increment_match_count(conn, rule_id)
        increment_match_count(conn, rule_id)
        rule = get_rule_by_id(conn, rule_id)
        assert rule.match_count == 2
        assert rule.last_matched_at is not None

    def test_bulk_get_active_rules_ordering(self, conn):
        create_rule(conn, KnowledgeBaseRule(pattern="v", match_type="vector", status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="e", match_type="exact", status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="c", match_type="contains", status="ДА"))
        create_rule(conn, KnowledgeBaseRule(pattern="r", match_type="regex", status="ДА"))

        rules = bulk_get_active_rules(conn)
        types = [r.match_type for r in rules]
        assert types == ["exact", "contains", "regex", "vector"]


# ---------------------------------------------------------------------------
# ScriptsConfig tests
# ---------------------------------------------------------------------------


class TestScriptsConfigCRUD:
    def test_create_and_get(self, conn):
        config = ScriptConfig(
            script_path="scripts/clean_versions.py",
            condition="vendor contains microsoft",
            priority=10,
            enabled=True,
        )
        config_id = create_script_config(conn, config)
        assert config_id is not None

        scripts = get_all_scripts(conn)
        assert len(scripts) == 1
        assert scripts[0].script_path == "scripts/clean_versions.py"
        assert scripts[0].enabled is True

    def test_get_enabled_scripts(self, conn):
        create_script_config(conn, ScriptConfig(script_path="a.py", priority=1, enabled=True))
        create_script_config(conn, ScriptConfig(script_path="b.py", priority=2, enabled=False))
        create_script_config(conn, ScriptConfig(script_path="c.py", priority=3, enabled=True))

        enabled = get_enabled_scripts(conn)
        assert len(enabled) == 2
        assert all(s.enabled for s in enabled)

    def test_update_script_config(self, conn):
        config_id = create_script_config(
            conn,
            ScriptConfig(script_path="old.py", priority=1, enabled=True),
        )
        scripts = get_all_scripts(conn)
        script = scripts[0]
        script.script_path = "new.py"
        script.enabled = False
        assert update_script_config(conn, script) is True

        updated = get_all_scripts(conn)
        assert updated[0].script_path == "new.py"
        assert updated[0].enabled is False

    def test_delete_script_config(self, conn):
        config_id = create_script_config(
            conn,
            ScriptConfig(script_path="del.py", priority=1),
        )
        assert delete_script_config(conn, config_id) is True
        assert len(get_all_scripts(conn)) == 0

    def test_scripts_ordered_by_priority(self, conn):
        create_script_config(conn, ScriptConfig(script_path="c.py", priority=30))
        create_script_config(conn, ScriptConfig(script_path="a.py", priority=10))
        create_script_config(conn, ScriptConfig(script_path="b.py", priority=20))

        scripts = get_all_scripts(conn)
        priorities = [s.priority for s in scripts]
        assert priorities == [10, 20, 30]
