"""Tests for matcher.core.preprocessor."""

from __future__ import annotations

import textwrap

from matcher.core.preprocessor import Preprocessor, _evaluate_condition
from shared.types import ScriptConfig


def _write_script(tmp_path, name: str, code: str):
    """Helper: write a plugin script to tmp_path."""
    path = tmp_path / name
    path.write_text(textwrap.dedent(code), encoding="utf-8")
    return path


class TestEvaluateCondition:
    def test_empty_condition_always_true(self):
        assert _evaluate_condition("", {"vendor": "anything"}) is True

    def test_contains_match(self):
        entry = {"vendor": "Microsoft Corporation", "product": "Windows"}
        assert _evaluate_condition("vendor contains microsoft", entry) is True

    def test_contains_no_match(self):
        entry = {"vendor": "Apache", "product": "HTTP Server"}
        assert _evaluate_condition("vendor contains microsoft", entry) is False

    def test_equals_match(self):
        entry = {"vendor": "apache", "product": "tomcat"}
        assert _evaluate_condition("vendor equals apache", entry) is True

    def test_startswith_match(self):
        entry = {"vendor": "Microsoft Corp", "product": "Word"}
        assert _evaluate_condition("vendor startswith microsoft", entry) is True

    def test_unknown_operator(self):
        assert _evaluate_condition("vendor like foo", {"vendor": "foo"}) is False

    def test_invalid_format(self):
        assert _evaluate_condition("badformat", {"vendor": "x"}) is False


class TestPreprocessor:
    def test_passthrough_no_scripts(self):
        pp = Preprocessor()
        entries = [{"vendor": "A", "product": "B", "version": "1", "raw_text": "A B"}]
        result = pp.process(entries, [])
        assert result == entries

    def test_script_transforms_entries(self, tmp_path):
        _write_script(
            tmp_path,
            "upper.py",
            """
            def process(entries):
                for e in entries:
                    e["product"] = e["product"].upper()
                return entries
            """,
        )
        pp = Preprocessor(scripts_dir=tmp_path)
        config = ScriptConfig(
            script_path="upper.py", condition="", priority=1, enabled=True
        )
        entries = [{"vendor": "a", "product": "hello", "version": "", "raw_text": "a hello"}]
        result = pp.process(entries, [config])
        assert result[0]["product"] == "HELLO"

    def test_script_can_split_entries(self, tmp_path):
        _write_script(
            tmp_path,
            "split.py",
            """
            def process(entries):
                result = []
                for e in entries:
                    products = e["product"].split(",")
                    for p in products:
                        new_e = dict(e)
                        new_e["product"] = p.strip()
                        new_e["raw_text"] = p.strip()
                        result.append(new_e)
                return result
            """,
        )
        pp = Preprocessor(scripts_dir=tmp_path)
        config = ScriptConfig(
            script_path="split.py", condition="", priority=1, enabled=True
        )
        entries = [{"vendor": "V", "product": "A, B, C", "version": "", "raw_text": "A, B, C"}]
        result = pp.process(entries, [config])
        assert len(result) == 3
        assert [e["product"] for e in result] == ["A", "B", "C"]

    def test_condition_filters_entries(self, tmp_path):
        _write_script(
            tmp_path,
            "tag.py",
            """
            def process(entries):
                for e in entries:
                    e["product"] = "TAGGED_" + e["product"]
                return entries
            """,
        )
        pp = Preprocessor(scripts_dir=tmp_path)
        config = ScriptConfig(
            script_path="tag.py",
            condition="vendor contains microsoft",
            priority=1,
            enabled=True,
        )
        entries = [
            {"vendor": "Microsoft", "product": "Word", "version": "", "raw_text": ""},
            {"vendor": "Apache", "product": "Tomcat", "version": "", "raw_text": ""},
        ]
        result = pp.process(entries, [config])
        products = {e["product"] for e in result}
        assert "TAGGED_Word" in products
        assert "Tomcat" in products  # Not tagged — condition didn't match

    def test_disabled_script_skipped(self, tmp_path):
        _write_script(
            tmp_path,
            "fail.py",
            """
            def process(entries):
                raise RuntimeError("should not run")
            """,
        )
        pp = Preprocessor(scripts_dir=tmp_path)
        config = ScriptConfig(
            script_path="fail.py", condition="", priority=1, enabled=False
        )
        entries = [{"vendor": "", "product": "X", "version": "", "raw_text": "X"}]
        result = pp.process(entries, [config])
        assert result == entries

    def test_failing_script_keeps_originals(self, tmp_path):
        _write_script(
            tmp_path,
            "bad.py",
            """
            def process(entries):
                raise ValueError("boom")
            """,
        )
        pp = Preprocessor(scripts_dir=tmp_path)
        config = ScriptConfig(
            script_path="bad.py", condition="", priority=1, enabled=True
        )
        entries = [{"vendor": "", "product": "Safe", "version": "", "raw_text": "Safe"}]
        result = pp.process(entries, [config])
        assert len(result) == 1
        assert result[0]["product"] == "Safe"

    def test_missing_script_skipped(self):
        pp = Preprocessor(scripts_dir="/nonexistent")
        config = ScriptConfig(
            script_path="nope.py", condition="", priority=1, enabled=True
        )
        entries = [{"vendor": "", "product": "X", "version": "", "raw_text": "X"}]
        result = pp.process(entries, [config])
        assert result == entries
