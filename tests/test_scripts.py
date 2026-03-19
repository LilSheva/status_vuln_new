"""Tests for preprocessing plugin scripts."""

from __future__ import annotations

from scripts.clean_microsoft import process as clean_ms
from scripts.clean_versions import process as clean_ver
from scripts.split_multiproduct import process as split_multi


def _entry(vendor: str = "", product: str = "", version: str = "") -> dict:
    raw = " ".join(s for s in (vendor, product, version) if s)
    return {"vendor": vendor, "product": product, "version": version, "raw_text": raw}


# ---------------------------------------------------------------------------
# split_multiproduct
# ---------------------------------------------------------------------------


class TestSplitMultiproduct:
    def test_semicolon_split(self):
        entries = [_entry("V", "Apache HTTP Server; Nginx; Tomcat")]
        result = split_multi(entries)
        assert len(result) == 3
        products = [e["product"] for e in result]
        assert "Apache HTTP Server" in products
        assert "Nginx" in products
        assert "Tomcat" in products

    def test_and_split(self):
        entries = [_entry("Microsoft", "Word и Excel")]
        result = split_multi(entries)
        assert len(result) == 2
        assert result[0]["product"] == "Word"
        assert result[1]["product"] == "Excel"

    def test_slash_split(self):
        entries = [_entry("", "Apache / Nginx")]
        result = split_multi(entries)
        assert len(result) == 2

    def test_no_split_needed(self):
        entries = [_entry("Apache", "HTTP Server 2.4")]
        result = split_multi(entries)
        assert len(result) == 1
        assert result[0]["product"] == "HTTP Server 2.4"

    def test_empty_product_passthrough(self):
        entries = [_entry("V", "")]
        result = split_multi(entries)
        assert len(result) == 1

    def test_preserves_vendor(self):
        entries = [_entry("Microsoft", "Word; Excel")]
        result = split_multi(entries)
        assert all(e["vendor"] == "Microsoft" for e in result)

    def test_raw_text_updated(self):
        entries = [_entry("V", "A; B", "1.0")]
        result = split_multi(entries)
        assert "A" in result[0]["raw_text"]
        assert "B" in result[1]["raw_text"]


# ---------------------------------------------------------------------------
# clean_microsoft
# ---------------------------------------------------------------------------


class TestCleanMicrosoft:
    def test_removes_trademark(self):
        entries = [_entry("Microsoft", "Windows(R) Server")]
        result = clean_ms(entries)
        assert "(R)" not in result[0]["product"]

    def test_removes_tm(self):
        entries = [_entry("Microsoft", "Office(TM) 365")]
        result = clean_ms(entries)
        assert "(TM)" not in result[0]["product"]

    def test_removes_for_windows(self):
        entries = [_entry("", "SQL Server for Windows x64-based Systems")]
        result = clean_ms(entries)
        assert "for Windows" not in result[0]["product"]
        assert "SQL Server" in result[0]["product"]

    def test_removes_service_pack(self):
        entries = [_entry("", "Windows Vista Service Pack 2")]
        result = clean_ms(entries)
        assert "Service Pack" not in result[0]["product"]

    def test_removes_kb_update(self):
        entries = [_entry("", "Windows 10 Update KB5001234")]
        result = clean_ms(entries)
        assert "KB5001234" not in result[0]["product"]

    def test_removes_edition(self):
        entries = [_entry("", "Windows 10 Professional")]
        result = clean_ms(entries)
        assert "Professional" not in result[0]["product"]

    def test_no_change_non_microsoft(self):
        entries = [_entry("Apache", "HTTP Server")]
        result = clean_ms(entries)
        assert result[0]["product"] == "HTTP Server"

    def test_empty_product_safe(self):
        entries = [_entry("", "")]
        result = clean_ms(entries)
        assert result[0]["product"] == ""


# ---------------------------------------------------------------------------
# clean_versions
# ---------------------------------------------------------------------------


class TestCleanVersions:
    def test_removes_semver(self):
        entries = [_entry("", "Apache HTTP Server 2.4.51")]
        result = clean_ver(entries)
        assert "2.4.51" not in result[0]["product"]
        assert "Apache HTTP Server" in result[0]["product"]

    def test_removes_v_prefix(self):
        entries = [_entry("", "Nginx v1.21.3")]
        result = clean_ver(entries)
        assert "v1.21.3" not in result[0]["product"]
        assert "Nginx" in result[0]["product"]

    def test_removes_year(self):
        entries = [_entry("", "Microsoft Office 2024")]
        result = clean_ver(entries)
        assert "2024" not in result[0]["product"]

    def test_removes_version_keyword(self):
        entries = [_entry("", "Java version 17.0.1")]
        result = clean_ver(entries)
        assert "version" not in result[0]["product"].lower()

    def test_does_not_empty_product(self):
        entries = [_entry("", "2.4.51")]
        result = clean_ver(entries)
        # Should keep original if cleaning would produce empty string
        assert result[0]["product"] != ""

    def test_no_change_when_clean(self):
        entries = [_entry("", "PostgreSQL")]
        result = clean_ver(entries)
        assert result[0]["product"] == "PostgreSQL"

    def test_raw_text_updated(self):
        entries = [_entry("Apache", "Server 2.4", "2.4")]
        result = clean_ver(entries)
        assert "2.4" not in result[0]["product"]
