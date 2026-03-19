"""Tests for matcher.core.normalizer."""

from __future__ import annotations

from matcher.core.normalizer import normalize_text


class TestNormalizeText:
    def test_cyrillic_to_latin(self):
        result = normalize_text("Апачи сервер", direction="to_en")
        # Should be transliterated and lowercased
        assert "a" in result.lower()
        # Should not contain Cyrillic anymore
        assert not any("\u0400" <= c <= "\u04FF" for c in result)

    def test_latin_stays_latin(self):
        result = normalize_text("Apache Server", direction="to_en")
        assert result == "apache server"

    def test_latin_to_cyrillic(self):
        result = normalize_text("Apache", direction="to_ru")
        # Should contain Cyrillic
        assert any("\u0400" <= c <= "\u04FF" for c in result)

    def test_cyrillic_stays_cyrillic(self):
        result = normalize_text("Сервер", direction="to_ru")
        assert "сервер" in result.lower()

    def test_empty_string(self):
        assert normalize_text("", direction="to_en") == ""

    def test_whitespace_only(self):
        assert normalize_text("   ", direction="to_en") == "   "

    def test_lowercased(self):
        result = normalize_text("APACHE", direction="to_en")
        assert result == "apache"

    def test_unknown_direction_defaults_to_en(self):
        result = normalize_text("test", direction="unknown")
        assert result == "test"
