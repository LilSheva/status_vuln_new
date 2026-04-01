"""Readers for TSU (ТСУ), PPTS (ППТС), and Journal files."""

from __future__ import annotations

import csv
import logging
import re
from pathlib import Path

import openpyxl

from shared.types import JournalEntry, PptsColumnMapping, Software, Vulnerability

logger = logging.getLogger(__name__)


class ReaderError(Exception):
    """Raised when a file cannot be read or parsed."""


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _clean_header(text: str) -> str:
    """Normalize a header cell: strip HTML tags, whitespace, lowercase."""
    text = re.sub(r"<[^>]+>", " ", text)  # remove <br> and other HTML
    text = re.sub(r"\(столбец\s+[A-Z]+\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_column(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    """Find column index by matching cleaned header against candidate keywords."""
    for idx, raw_header in enumerate(headers):
        cleaned = _clean_header(raw_header).lower()
        for key in candidates:
            if key in cleaned:
                return idx
    return None


def _cell_str(cell) -> str:
    """Convert a cell value to a stripped string."""
    if cell is None:
        return ""
    return str(cell).strip()


def _read_excel_rows(path: Path) -> list[list[str]]:
    """Read all rows from the first sheet of an Excel file."""
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    try:
        ws = wb.active
        if ws is None:
            raise ReaderError(f"No active sheet in {path.name}")
        rows: list[list[str]] = []
        for row in ws.iter_rows(values_only=True):
            rows.append([_cell_str(cell) for cell in row])
        return rows
    finally:
        wb.close()


def _read_csv_rows(path: Path) -> list[list[str]]:
    """Read all rows from a CSV file, auto-detecting delimiter."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            # Fallback to comma if sniffer fails
            dialect = "excel"  # type: ignore[assignment]
        reader = csv.reader(f, dialect)
        return [row for row in reader]


def _read_rows(path: Path) -> list[list[str]]:
    """Read rows from Excel or CSV based on file extension."""
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return _read_excel_rows(path)
    if suffix == ".csv":
        return _read_csv_rows(path)
    raise ReaderError(f"Unsupported file format: {suffix} (expected .xlsx, .xls, .csv)")


def _safe_get(row: list[str], idx: int | None) -> str:
    """Safely get a value from a row by index."""
    if idx is None or idx >= len(row):
        return ""
    return row[idx].strip()


# ---------------------------------------------------------------------------
# Vendor+Product splitting (TSU format: combined in one column)
# ---------------------------------------------------------------------------

_VENDOR_PRODUCT_SEPARATORS = re.compile(r"\s*(?:,\s+|\s+-\s+)\s*")


def _split_vendor_product(combined: str) -> tuple[str, str]:
    """Split a combined 'Vendor, Product' string; returns (vendor, product)."""
    if not combined:
        return "", ""

    parts = _VENDOR_PRODUCT_SEPARATORS.split(combined, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return "", combined.strip()


# ---------------------------------------------------------------------------
# TSU (ТСУ) reader — vulnerability list
# ---------------------------------------------------------------------------

_TSU_CVE_KEYS = ("cve",)
_TSU_CVSS_KEYS = ("cvss",)
_TSU_PRODUCT_KEYS = ("продукт", "product", "по", "название")
_TSU_SOURCE_KEYS = ("источник", "source", "ссылка", "url")


def read_tsu(path: str | Path) -> list[Vulnerability]:
    """Read a TSU file and return Vulnerability objects, auto-splitting vendor/product."""
    path = Path(path)
    if not path.exists():
        raise ReaderError(f"File not found: {path}")

    try:
        rows = _read_rows(path)
    except ReaderError:
        raise
    except Exception as exc:
        raise ReaderError(f"Failed to read {path.name}: {exc}") from exc

    if len(rows) < 2:
        raise ReaderError(f"File {path.name} has no data rows")

    headers = [str(h) for h in rows[0]]
    col_cve = _find_column(headers, _TSU_CVE_KEYS)
    col_cvss = _find_column(headers, _TSU_CVSS_KEYS)
    col_product = _find_column(headers, _TSU_PRODUCT_KEYS)
    col_source = _find_column(headers, _TSU_SOURCE_KEYS)

    if col_product is None:
        raise ReaderError(
            f"Cannot find product column in {path.name}. "
            f"Headers: {[_clean_header(h) for h in headers]}"
        )

    vulnerabilities: list[Vulnerability] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        combined_product = _safe_get(row, col_product)
        if not combined_product:
            logger.debug("Skipping row %d: empty product", row_idx)
            continue

        vendor, product = _split_vendor_product(combined_product)
        cve = _safe_get(row, col_cve)
        cvss = _safe_get(row, col_cvss)
        source_url = _safe_get(row, col_source)

        raw_text = " ".join(part for part in (vendor, product) if part)

        vulnerabilities.append(
            Vulnerability(
                cve_id=cve,
                vendor=vendor,
                product=product,
                version="",
                raw_text=raw_text,
                cvss=cvss,
                source_url=source_url,
            )
        )

    logger.info("Read %d vulnerabilities from %s", len(vulnerabilities), path.name)
    return vulnerabilities


# ---------------------------------------------------------------------------
# PPTS (ППТС) reader — software registry
# ---------------------------------------------------------------------------

_PPTS_ID_KEYS = ("id пптс", "id", "идентификатор")
_PPTS_NAME_KEYS = ("название птс", "название", "наименование", "name", "software")
_PPTS_VENDOR_KEYS = ("вендор", "vendor", "производитель", "разработчик")


def read_ppts_headers(path: str | Path) -> list[str]:
    """Read and return cleaned column headers from a PPTS file."""
    path = Path(path)
    if not path.exists():
        raise ReaderError(f"File not found: {path}")
    rows = _read_rows(path)
    if not rows:
        raise ReaderError(f"File {path.name} is empty")
    return [_clean_header(str(h)) for h in rows[0]]


def auto_detect_ppts_mapping(path: str | Path) -> PptsColumnMapping:
    """Auto-detect column mapping for a PPTS file."""
    path = Path(path)
    rows = _read_rows(path)
    if not rows:
        raise ReaderError(f"File {path.name} is empty")

    raw_headers = [str(h) for h in rows[0]]
    cleaned = [_clean_header(h) for h in raw_headers]

    return PptsColumnMapping(
        file_path=str(path),
        col_id=_find_column(raw_headers, _PPTS_ID_KEYS),
        col_name=_find_column(raw_headers, _PPTS_NAME_KEYS),
        col_vendor=_find_column(raw_headers, _PPTS_VENDOR_KEYS),
        headers=cleaned,
    )


def read_ppts(
    path: str | Path,
    source: str = "local_ppts",
    mapping: PptsColumnMapping | None = None,
) -> list[Software]:
    """Read a PPTS file and return Software objects (uses mapping or auto-detects columns)."""
    path = Path(path)
    if not path.exists():
        raise ReaderError(f"File not found: {path}")

    try:
        rows = _read_rows(path)
    except ReaderError:
        raise
    except Exception as exc:
        raise ReaderError(f"Failed to read {path.name}: {exc}") from exc

    if len(rows) < 2:
        raise ReaderError(f"File {path.name} has no data rows")

    if mapping is not None and mapping.col_name is not None:
        col_id = mapping.col_id
        col_name = mapping.col_name
        col_vendor = mapping.col_vendor
    else:
        headers = [str(h) for h in rows[0]]
        col_id = _find_column(headers, _PPTS_ID_KEYS)
        col_name = _find_column(headers, _PPTS_NAME_KEYS)
        col_vendor = _find_column(headers, _PPTS_VENDOR_KEYS)

    if col_name is None:
        raise ReaderError(
            f"Cannot find name column in {path.name}. "
            f"Headers: {[_clean_header(str(h)) for h in rows[0]]}"
        )

    software_list: list[Software] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        name = _safe_get(row, col_name)
        vendor = _safe_get(row, col_vendor)
        sw_id = _safe_get(row, col_id) or str(row_idx - 1)

        if not name and not vendor:
            logger.debug("Skipping row %d: empty name and vendor", row_idx)
            continue

        display_name = name if name else vendor

        software_list.append(
            Software(id=sw_id, name=display_name, vendor=vendor, source=source)
        )

    logger.info("Read %d software entries from %s", len(software_list), path.name)
    return software_list


# ---------------------------------------------------------------------------
# Journal reader — historical vulnerability analysis
# ---------------------------------------------------------------------------

# Journal columns are at fixed positions (A=0..J=9) per spec:
# A=Номер, B=Дата, C=Ответственный, D=Публикация, E=Статус,
# F=ID ППТС, G=CVE, H=CVSS, I=Продукт, J=Источник
_JOURNAL_COL_RESPONSIBLE = 2   # C
_JOURNAL_COL_STATUS = 4        # E
_JOURNAL_COL_PPTS_ID = 5       # F
_JOURNAL_COL_CVE = 6           # G
_JOURNAL_COL_PRODUCT = 8       # I

_JOURNAL_CVE_KEYS = ("cve",)
_JOURNAL_STATUS_KEYS = ("статус",)
_JOURNAL_PPTS_ID_KEYS = ("id пптс", "пптс")
_JOURNAL_RESPONSIBLE_KEYS = ("ответственный",)
_JOURNAL_PRODUCT_KEYS = ("продукт", "product")


def read_journal(path: str | Path) -> list[JournalEntry]:
    """Read a historical vulnerability journal file."""
    path = Path(path)
    if not path.exists():
        raise ReaderError(f"File not found: {path}")

    try:
        rows = _read_rows(path)
    except ReaderError:
        raise
    except Exception as exc:
        raise ReaderError(f"Failed to read {path.name}: {exc}") from exc

    if len(rows) < 2:
        raise ReaderError(f"File {path.name} has no data rows")

    headers = [str(h) for h in rows[0]]
    col_cve = _find_column(headers, _JOURNAL_CVE_KEYS)
    col_status = _find_column(headers, _JOURNAL_STATUS_KEYS)
    col_ppts = _find_column(headers, _JOURNAL_PPTS_ID_KEYS)
    col_resp = _find_column(headers, _JOURNAL_RESPONSIBLE_KEYS)
    col_product = _find_column(headers, _JOURNAL_PRODUCT_KEYS)

    # Fall back to fixed positions if header detection fails
    if col_cve is None:
        col_cve = _JOURNAL_COL_CVE
    if col_status is None:
        col_status = _JOURNAL_COL_STATUS
    if col_ppts is None:
        col_ppts = _JOURNAL_COL_PPTS_ID
    if col_resp is None:
        col_resp = _JOURNAL_COL_RESPONSIBLE
    if col_product is None:
        col_product = _JOURNAL_COL_PRODUCT

    entries: list[JournalEntry] = []
    for row_idx, row in enumerate(rows[1:], start=2):
        cve = _safe_get(row, col_cve)
        if not cve:
            continue

        status = _safe_get(row, col_status)
        ppts_id = _safe_get(row, col_ppts)
        responsible = _safe_get(row, col_resp)
        product = _safe_get(row, col_product)

        entries.append(
            JournalEntry(
                cve_id=cve,
                status=status,
                ppts_id=ppts_id,
                responsible=responsible,
                product=product,
            )
        )

    logger.info("Read %d journal entries from %s", len(entries), path.name)
    return entries
