"""CRUD operations for the knowledge base (rules and scripts_config)."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from shared.types import KnowledgeBaseRule, ScriptConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rules CRUD
# ---------------------------------------------------------------------------


def _row_to_rule(row: sqlite3.Row) -> KnowledgeBaseRule:
    """Convert a database row to a KnowledgeBaseRule."""
    return KnowledgeBaseRule(
        id=row["id"],
        pattern=row["pattern"],
        match_type=row["match_type"],
        vendor_pattern=row["vendor_pattern"] if "vendor_pattern" in row.keys() else "",
        vendor_match_type=row["vendor_match_type"] if "vendor_match_type" in row.keys() else "contains",
        status=row["status"],
        ppts_id=row["ppts_id"],
        vector_threshold=row["vector_threshold"],
        comment=row["comment"],
        created_at=row["created_at"],
        last_matched_at=row["last_matched_at"],
        match_count=row["match_count"],
    )


def get_all_rules(conn: sqlite3.Connection) -> list[KnowledgeBaseRule]:
    """Return all rules ordered by id."""
    cursor = conn.execute("SELECT * FROM rules ORDER BY id")
    return [_row_to_rule(row) for row in cursor.fetchall()]


def get_rule_by_id(conn: sqlite3.Connection, rule_id: int) -> KnowledgeBaseRule | None:
    """Return a single rule by id, or None."""
    cursor = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
    row = cursor.fetchone()
    return _row_to_rule(row) if row else None


def search_rules(
    conn: sqlite3.Connection,
    *,
    pattern: str | None = None,
    match_type: str | None = None,
    status: str | None = None,
) -> list[KnowledgeBaseRule]:
    """Search rules with optional filters."""
    clauses: list[str] = []
    params: list[str] = []

    if pattern is not None:
        clauses.append("(pattern LIKE ? OR vendor_pattern LIKE ?)")
        params.append(f"%{pattern}%")
        params.append(f"%{pattern}%")
    if match_type is not None:
        clauses.append("match_type = ?")
        params.append(match_type)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"SELECT * FROM rules{where} ORDER BY id"  # noqa: S608
    cursor = conn.execute(query, params)
    return [_row_to_rule(row) for row in cursor.fetchall()]


def create_rule(conn: sqlite3.Connection, rule: KnowledgeBaseRule) -> int:
    """Insert a new rule and return its id."""
    cursor = conn.execute(
        """
        INSERT INTO rules (pattern, match_type, vendor_pattern, vendor_match_type,
                           status, ppts_id, vector_threshold, comment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            rule.pattern,
            rule.match_type,
            rule.vendor_pattern,
            rule.vendor_match_type,
            rule.status,
            rule.ppts_id,
            rule.vector_threshold,
            rule.comment,
        ),
    )
    conn.commit()
    rule_id = cursor.lastrowid
    logger.info("Created rule id=%d pattern=%r", rule_id, rule.pattern)
    return rule_id  # type: ignore[return-value]


def update_rule(conn: sqlite3.Connection, rule: KnowledgeBaseRule) -> bool:
    """Update an existing rule. Returns True if a row was updated."""
    cursor = conn.execute(
        """
        UPDATE rules
        SET pattern = ?, match_type = ?, vendor_pattern = ?, vendor_match_type = ?,
            status = ?, ppts_id = ?, vector_threshold = ?, comment = ?
        WHERE id = ?
        """,
        (
            rule.pattern,
            rule.match_type,
            rule.vendor_pattern,
            rule.vendor_match_type,
            rule.status,
            rule.ppts_id,
            rule.vector_threshold,
            rule.comment,
            rule.id,
        ),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    if updated:
        logger.info("Updated rule id=%d", rule.id)
    return updated


def delete_rule(conn: sqlite3.Connection, rule_id: int) -> bool:
    """Delete a rule by id. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    if deleted:
        logger.info("Deleted rule id=%d", rule_id)
    return deleted


def increment_match_count(conn: sqlite3.Connection, rule_id: int) -> None:
    """Increment match_count and update last_matched_at for a rule."""
    conn.execute(
        """
        UPDATE rules
        SET match_count = match_count + 1,
            last_matched_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (rule_id,),
    )
    conn.commit()


def bulk_get_active_rules(
    conn: sqlite3.Connection,
) -> list[KnowledgeBaseRule]:
    """Return all rules ordered by match_type priority (exact first, vector last)."""
    cursor = conn.execute(
        """
        SELECT * FROM rules
        ORDER BY
            CASE match_type
                WHEN 'exact' THEN 1
                WHEN 'contains' THEN 2
                WHEN 'regex' THEN 3
                WHEN 'vector' THEN 4
            END,
            id
        """
    )
    return [_row_to_rule(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# ScriptsConfig CRUD
# ---------------------------------------------------------------------------


def _row_to_script_config(row: sqlite3.Row) -> ScriptConfig:
    """Convert a database row to a ScriptConfig."""
    return ScriptConfig(
        id=row["id"],
        script_path=row["script_path"],
        condition=row["condition"],
        priority=row["priority"],
        enabled=bool(row["enabled"]),
    )


def get_all_scripts(conn: sqlite3.Connection) -> list[ScriptConfig]:
    """Return all script configs ordered by priority."""
    cursor = conn.execute("SELECT * FROM scripts_config ORDER BY priority, id")
    return [_row_to_script_config(row) for row in cursor.fetchall()]


def get_enabled_scripts(conn: sqlite3.Connection) -> list[ScriptConfig]:
    """Return only enabled script configs ordered by priority."""
    cursor = conn.execute(
        "SELECT * FROM scripts_config WHERE enabled = 1 ORDER BY priority, id"
    )
    return [_row_to_script_config(row) for row in cursor.fetchall()]


def create_script_config(conn: sqlite3.Connection, config: ScriptConfig) -> int:
    """Insert a new script config and return its id."""
    cursor = conn.execute(
        """
        INSERT INTO scripts_config (script_path, condition, priority, enabled)
        VALUES (?, ?, ?, ?)
        """,
        (config.script_path, config.condition, config.priority, int(config.enabled)),
    )
    conn.commit()
    return cursor.lastrowid  # type: ignore[return-value]


def update_script_config(conn: sqlite3.Connection, config: ScriptConfig) -> bool:
    """Update an existing script config. Returns True if a row was updated."""
    cursor = conn.execute(
        """
        UPDATE scripts_config
        SET script_path = ?, condition = ?, priority = ?, enabled = ?
        WHERE id = ?
        """,
        (
            config.script_path,
            config.condition,
            config.priority,
            int(config.enabled),
            config.id,
        ),
    )
    conn.commit()
    return cursor.rowcount > 0


def delete_script_config(conn: sqlite3.Connection, config_id: int) -> bool:
    """Delete a script config by id. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM scripts_config WHERE id = ?", (config_id,))
    conn.commit()
    return cursor.rowcount > 0
