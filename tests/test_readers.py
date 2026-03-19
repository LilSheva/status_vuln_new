"""Tests for matcher.io.readers."""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import pytest

from matcher.io.readers import ReaderError, read_journal, read_ppts, read_tsu


def _create_xlsx(path: Path, headers: list[str], rows: list[list]) -> Path:
    """Helper: create a small .xlsx file."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(str(path))
    return path


def _create_csv(
    path: Path,
    headers: list[str],
    rows: list[list],
    delimiter: str = ",",
) -> Path:
    """Helper: create a small .csv file."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
    return path


# ---------------------------------------------------------------------------
# TSU reader tests — vendor+product combined in one column
# ---------------------------------------------------------------------------


class TestReadTSU:
    def test_read_xlsx_combined_vendor_product(self, tmp_path):
        """TSU has vendor+product combined in 'Продукт' column, separated by comma."""
        path = _create_xlsx(
            tmp_path / "tsu.xlsx",
            ["№", "CVE", "CVSS", "Продукт", "Источник"],
            [
                [1, "CVE-2025-001", "9.8 Critical", "Microsoft, Windows 10", "http://example.com"],
                [2, "CVE-2025-002", "7.5 High", "Apache, HTTP Server", "http://example.com"],
            ],
        )
        vulns = read_tsu(path)
        assert len(vulns) == 2
        assert vulns[0].cve_id == "CVE-2025-001"
        assert vulns[0].vendor == "Microsoft"
        assert vulns[0].product == "Windows 10"
        assert vulns[0].cvss == "9.8 Critical"

    def test_vendor_product_dash_separator(self, tmp_path):
        """Vendor and product separated by ' - '."""
        path = _create_xlsx(
            tmp_path / "tsu.xlsx",
            ["CVE", "Продукт"],
            [["CVE-1", "LinTorv - Ubuntu Kernel"]],
        )
        vulns = read_tsu(path)
        assert len(vulns) == 1
        assert vulns[0].vendor == "LinTorv"
        assert vulns[0].product == "Ubuntu Kernel"

    def test_no_vendor_separator(self, tmp_path):
        """When no separator, entire text becomes product."""
        path = _create_xlsx(
            tmp_path / "tsu.xlsx",
            ["CVE", "Продукт"],
            [["CVE-1", "SomeProductNoVendor"]],
        )
        vulns = read_tsu(path)
        assert len(vulns) == 1
        assert vulns[0].vendor == ""
        assert vulns[0].product == "SomeProductNoVendor"

    def test_read_csv(self, tmp_path):
        path = _create_csv(
            tmp_path / "tsu.csv",
            ["CVE", "Продукт"],
            [["CVE-2024-003", "Microsoft, Windows"]],
        )
        vulns = read_tsu(path)
        assert len(vulns) == 1
        assert vulns[0].vendor == "Microsoft"

    def test_skip_empty_product(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "tsu.xlsx",
            ["CVE", "Продукт"],
            [["CVE-1", "Apache, Server"], ["CVE-2", ""], ["CVE-3", "Nginx, Web"]],
        )
        vulns = read_tsu(path)
        assert len(vulns) == 2

    def test_missing_product_column_raises(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "tsu.xlsx",
            ["CVE", "SomethingElse"],
            [["CVE-1", "data"]],
        )
        with pytest.raises(ReaderError, match="Cannot find product column"):
            read_tsu(path)

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(ReaderError, match="File not found"):
            read_tsu(tmp_path / "nonexistent.xlsx")

    def test_unsupported_format_raises(self, tmp_path):
        path = tmp_path / "tsu.json"
        path.write_text("{}")
        with pytest.raises(ReaderError, match="Unsupported file format"):
            read_tsu(path)

    def test_empty_file_raises(self, tmp_path):
        path = _create_xlsx(tmp_path / "tsu.xlsx", ["Продукт"], [])
        with pytest.raises(ReaderError, match="no data rows"):
            read_tsu(path)

    def test_raw_text_contains_vendor_and_product(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "tsu.xlsx",
            ["CVE", "Продукт"],
            [["CVE-1", "Oracle, Database 19c"]],
        )
        vulns = read_tsu(path)
        assert "Oracle" in vulns[0].raw_text
        assert "Database 19c" in vulns[0].raw_text


# ---------------------------------------------------------------------------
# PPTS reader tests — vendor and name in separate columns
# ---------------------------------------------------------------------------


class TestReadPPTS:
    def test_read_xlsx_with_vendor(self, tmp_path):
        """PPTS has separate ID, Name, and Vendor columns."""
        path = _create_xlsx(
            tmp_path / "ppts.xlsx",
            ["ID ППТС", "Название ПТС", "Вендор продукта"],
            [
                ["SUPO-1001", "Kaspersky Endpoint Security", "Лаборатория Касперского"],
                ["SUPO-1002", "Nginx", "Nginx Inc"],
            ],
        )
        software = read_ppts(path, source="general_ppts")
        assert len(software) == 2
        assert software[0].id == "SUPO-1001"
        assert software[0].name == "Kaspersky Endpoint Security"
        assert software[0].vendor == "Лаборатория Касперского"
        assert software[0].source == "general_ppts"

    def test_html_in_headers(self, tmp_path):
        """Real files have HTML <br> in headers."""
        path = _create_xlsx(
            tmp_path / "ppts.xlsx",
            ["(Столбец M)<br>ID ППТС", "(Столбец O)<br>Название ПТС", "(Столбец R)<br>Вендор продукта"],
            [["SUPO-1", "Product A", "Vendor A"]],
        )
        software = read_ppts(path)
        assert len(software) == 1
        assert software[0].id == "SUPO-1"
        assert software[0].name == "Product A"
        assert software[0].vendor == "Vendor A"

    def test_filler_columns_ignored(self, tmp_path):
        """PPTS files have many filler columns with numbers."""
        headers = ["Col1", "Col2", "Col3", "ID ППТС", "Col5", "Название ПТС", "Col7", "Вендор продукта"]
        path = _create_xlsx(
            tmp_path / "ppts.xlsx",
            headers,
            [[1, 2, 3, "SW-1", 5, "Apache", 7, "ASF"]],
        )
        software = read_ppts(path)
        assert len(software) == 1
        assert software[0].id == "SW-1"
        assert software[0].name == "Apache"

    def test_empty_name_uses_vendor(self, tmp_path):
        """When name is empty but vendor exists, entry is still created."""
        path = _create_xlsx(
            tmp_path / "ppts.xlsx",
            ["ID ППТС", "Название ПТС", "Вендор продукта"],
            [["SW-1", "", "Cisco Systems"]],
        )
        software = read_ppts(path)
        assert len(software) == 1
        assert software[0].name == "Cisco Systems"

    def test_skip_fully_empty_row(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "ppts.xlsx",
            ["ID ППТС", "Название ПТС", "Вендор продукта"],
            [["SW-1", "Good", "V"], ["SW-2", "", ""], ["SW-3", "Also", "V"]],
        )
        software = read_ppts(path)
        assert len(software) == 2

    def test_read_csv(self, tmp_path):
        path = _create_csv(
            tmp_path / "ppts.csv",
            ["ID ППТС", "Название ПТС", "Вендор"],
            [["1", "PostgreSQL 14", "PG"]],
        )
        software = read_ppts(path, source="general_ppts")
        assert len(software) == 1
        assert software[0].vendor == "PG"

    def test_missing_name_column_raises(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "ppts.xlsx",
            ["ID", "SomethingWeird"],
            [["1", "data"]],
        )
        with pytest.raises(ReaderError, match="Cannot find name column"):
            read_ppts(path)


# ---------------------------------------------------------------------------
# Journal reader tests
# ---------------------------------------------------------------------------


class TestReadJournal:
    def test_read_journal(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "journal.xlsx",
            ["Номер", "Дата", "Ответственный", "Публикация", "Статус", "ID ППТС", "CVE", "CVSS", "Продукт", "Источник"],
            [
                [3783, "2025-10-15", "Шейчук Я.И.", "БДУ ФСТЭК", "ДА", "COM-7303", "CVE-2021-25743", "5.0", "Google Inc, Kubernetes", ""],
                [3782, "2025-10-15", "Иванов А.А.", "БДУ ФСТЭК", "НЕТ", "", "CVE-2024-12345", "7.5", "Apache, Tomcat", ""],
            ],
        )
        entries = read_journal(path)
        assert len(entries) == 2
        assert entries[0].cve_id == "CVE-2021-25743"
        assert entries[0].status == "ДА"
        assert entries[0].ppts_id == "COM-7303"
        assert entries[0].responsible == "Шейчук Я.И."
        assert entries[1].status == "НЕТ"

    def test_skip_empty_cve(self, tmp_path):
        path = _create_xlsx(
            tmp_path / "journal.xlsx",
            ["Номер", "Дата", "Ответственный", "Публикация", "Статус", "ID ППТС", "CVE", "CVSS", "Продукт", "Источник"],
            [
                [1, "", "A", "", "ДА", "X", "CVE-1", "", "", ""],
                [2, "", "B", "", "НЕТ", "", "", "", "", ""],
            ],
        )
        entries = read_journal(path)
        assert len(entries) == 1

    def test_multiline_ppts_id(self, tmp_path):
        """Journal can have multiple PPTS IDs separated by newlines."""
        path = _create_xlsx(
            tmp_path / "journal.xlsx",
            ["Номер", "Дата", "Ответственный", "Публикация", "Статус", "ID ППТС", "CVE", "CVSS", "Продукт", "Источник"],
            [
                [1, "", "A", "", "ДА", "COM-1\nCOM-2\nCOM-3", "CVE-1", "", "", ""],
            ],
        )
        entries = read_journal(path)
        assert entries[0].ppts_id == "COM-1\nCOM-2\nCOM-3"

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(ReaderError, match="File not found"):
            read_journal(tmp_path / "nope.xlsx")
