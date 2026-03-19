"""XLSX report generation with 3 sheets."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

if TYPE_CHECKING:
    from pathlib import Path

    from openpyxl.worksheet.worksheet import Worksheet

    from shared.types import AnalysisResult, PipelineSettings

logger = logging.getLogger(__name__)

# --- Style constants ---
_HEADER_FONT = Font(name="Segoe UI", bold=True, size=11, color="FFFFFF")
_HEADER_FILL = PatternFill(start_color="4A5ABF", end_color="4A5ABF", fill_type="solid")
_HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
_THIN_BORDER = Border(
    left=Side(style="thin", color="D0D0E0"),
    right=Side(style="thin", color="D0D0E0"),
    top=Side(style="thin", color="D0D0E0"),
    bottom=Side(style="thin", color="D0D0E0"),
)

_STATUS_FILLS: dict[str, PatternFill] = {
    "ДА": PatternFill(start_color="D5F5E3", end_color="D5F5E3", fill_type="solid"),
    "НЕТ": PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid"),
    "ЛИНУКС": PatternFill(start_color="D4E6F1", end_color="D4E6F1", fill_type="solid"),
    "УСЛОВНО": PatternFill(start_color="FCF3CF", end_color="FCF3CF", fill_type="solid"),
}

_SCORE_FILLS = {
    "high": PatternFill(start_color="D5F5E3", end_color="D5F5E3", fill_type="solid"),
    "medium": PatternFill(start_color="FCF3CF", end_color="FCF3CF", fill_type="solid"),
    "low": PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid"),
}


def _style_header(ws: Worksheet, col_count: int) -> None:
    """Apply header styles to the first row."""
    for col in range(1, col_count + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT
        cell.border = _THIN_BORDER


def _auto_width(ws: Worksheet, col_count: int, max_width: int = 50) -> None:
    """Auto-fit column widths based on content."""
    for col in range(1, col_count + 1):
        max_len = 0
        for row in ws.iter_rows(min_col=col, max_col=col, values_only=False):
            for cell in row:
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
        adjusted = min(max_len + 4, max_width)
        ws.column_dimensions[get_column_letter(col)].width = max(adjusted, 10)


def _score_fill(score: float) -> PatternFill | None:
    """Return a color fill based on score value."""
    if score >= 0.7:
        return _SCORE_FILLS["high"]
    if score >= 0.4:
        return _SCORE_FILLS["medium"]
    if score > 0:
        return _SCORE_FILLS["low"]
    return None


# ---------------------------------------------------------------------------
# Sheet 1: Main table
# ---------------------------------------------------------------------------

_MAIN_HEADERS = [
    "CVE ID",
    "Вендор",
    "Продукт",
    "Статус",
    "Источник решения",
    "ППТС ID",
    "Ответственный",
    "Лучший кандидат",
    "Итоговый балл",
]


def _write_main_sheet(ws: Worksheet, results: list[AnalysisResult]) -> None:
    """Write the main results table (Sheet 1)."""
    ws.title = "Основная таблица"

    for col, header in enumerate(_MAIN_HEADERS, 1):
        ws.cell(row=1, column=col, value=header)
    _style_header(ws, len(_MAIN_HEADERS))

    source_names = {
        "journal": "Журнал проверок",
        "knowledge_base": "База знаний",
        "auto_no_match": "Автоматически (нет совпадений)",
        "manual": "Ручной разбор",
    }

    for row_idx, r in enumerate(results, 2):
        v = r.vulnerability
        ws.cell(row=row_idx, column=1, value=v.cve_id)
        ws.cell(row=row_idx, column=2, value=v.vendor)
        ws.cell(row=row_idx, column=3, value=v.product)

        status_cell = ws.cell(row=row_idx, column=4, value=r.status or "(пусто)")
        if r.status in _STATUS_FILLS:
            status_cell.fill = _STATUS_FILLS[r.status]
        status_cell.alignment = Alignment(horizontal="center")

        ws.cell(row=row_idx, column=5, value=source_names.get(r.status_source, r.status_source))
        ws.cell(row=row_idx, column=6, value=r.ppts_id or "")
        ws.cell(row=row_idx, column=7, value=r.responsible or "")

        if r.candidates:
            best = r.candidates[0]
            ws.cell(row=row_idx, column=8, value=best.software.name)
            score_cell = ws.cell(row=row_idx, column=9, value=round(best.combined_score, 4))
            fill = _score_fill(best.combined_score)
            if fill:
                score_cell.fill = fill
        else:
            ws.cell(row=row_idx, column=8, value="")
            ws.cell(row=row_idx, column=9, value="")

        for col in range(1, len(_MAIN_HEADERS) + 1):
            ws.cell(row=row_idx, column=col).border = _THIN_BORDER

    _auto_width(ws, len(_MAIN_HEADERS))
    ws.auto_filter.ref = ws.dimensions


# ---------------------------------------------------------------------------
# Sheet 2: Detailed analysis
# ---------------------------------------------------------------------------

_DETAIL_HEADERS = [
    "CVE ID",
    "Продукт (ТСУ)",
    "Кандидат (ППТС)",
    "ППТС ID",
    "Vector Score",
    "Fuzzy Score",
    "Exact Score",
    "Итоговый балл",
    "Ранг",
]


def _write_detail_sheet(ws: Worksheet, results: list[AnalysisResult]) -> None:
    """Write the detailed analysis sheet (Sheet 2) for entries needing manual review."""
    ws.title = "Детальный анализ"

    for col, header in enumerate(_DETAIL_HEADERS, 1):
        ws.cell(row=1, column=col, value=header)
    _style_header(ws, len(_DETAIL_HEADERS))

    row_idx = 2
    for r in results:
        if not r.candidates:
            continue

        for rank, c in enumerate(r.candidates, 1):
            ws.cell(row=row_idx, column=1, value=r.vulnerability.cve_id)
            ws.cell(row=row_idx, column=2, value=r.vulnerability.product)
            ws.cell(row=row_idx, column=3, value=c.software.name)
            ws.cell(row=row_idx, column=4, value=c.software.id)

            vs_cell = ws.cell(row=row_idx, column=5, value=round(c.vector_score, 4))
            fs_cell = ws.cell(row=row_idx, column=6, value=round(c.fuzzy_score, 2))
            es_cell = ws.cell(row=row_idx, column=7, value=round(c.exact_score, 2))
            cs_cell = ws.cell(row=row_idx, column=8, value=round(c.combined_score, 4))

            for cell in (vs_cell, cs_cell):
                fill = _score_fill(cell.value if cell.value else 0)
                if fill:
                    cell.fill = fill

            ws.cell(row=row_idx, column=9, value=rank)

            for col in range(1, len(_DETAIL_HEADERS) + 1):
                ws.cell(row=row_idx, column=col).border = _THIN_BORDER

            row_idx += 1

    _auto_width(ws, len(_DETAIL_HEADERS))
    if row_idx > 2:
        ws.auto_filter.ref = ws.dimensions


# ---------------------------------------------------------------------------
# Sheet 3: Reference
# ---------------------------------------------------------------------------


def _write_reference_sheet(ws: Worksheet, settings: PipelineSettings) -> None:
    """Write the reference/help sheet (Sheet 3)."""
    ws.title = "Справка"

    info = [
        ("Параметр", "Значение", "Описание"),
        ("Top-N", str(settings.top_n), "Количество кандидатов из векторного поиска"),
        ("Порог вектора", str(settings.vector_threshold), "Минимальный cosine similarity (0-1)"),
        ("Порог fuzzy", str(settings.fuzzy_threshold), "Минимальный fuzzy score (0-100)"),
        ("Транслитерация", settings.transliteration_direction, "Направление нормализации"),
        ("Мин. длина слова", str(settings.min_word_length), "Фильтр коротких слов для fuzzy"),
        ("База знаний", "Да" if settings.use_knowledge_base else "Нет", "Использование базы знаний"),
        ("", "", ""),
        ("Метрика", "Диапазон", "Описание"),
        ("Vector Score", "0.0 — 1.0", "Cosine similarity между эмбеддингами (sentence-transformers)"),
        ("Fuzzy Score", "0 — 100", "Лучший из token_sort_ratio, token_set_ratio, partial_ratio (RapidFuzz)"),
        ("Exact Score", "0 / 50 / 75 / 100", "100=точное совпадение, 75=подстрока, 50=все слова, 0=нет"),
        ("Итоговый балл", "0.0 — 1.0", "Взвешенная комбинация: 50% vector + 30% fuzzy + 20% exact"),
        ("", "", ""),
        ("Статус", "Источник", "Описание"),
        ("ДА", "Только БЗ", "ПО присутствует в инфраструктуре (назначается только через базу знаний)"),
        ("НЕТ", "Авто / БЗ", "ПО отсутствует в инфраструктуре"),
        ("ЛИНУКС", "БЗ", "Linux-специфичное ПО"),
        ("УСЛОВНО", "БЗ", "Требует дополнительной проверки"),
        ("(пусто)", "Авто", "Есть кандидаты, но уверенности недостаточно — требуется ручной разбор"),
    ]

    for row_idx, (a, b, c) in enumerate(info, 1):
        ws.cell(row=row_idx, column=1, value=a)
        ws.cell(row=row_idx, column=2, value=b)
        ws.cell(row=row_idx, column=3, value=c)

    # Style header rows
    for col in range(1, 4):
        cell = ws.cell(row=1, column=col)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT

    _auto_width(ws, 3, max_width=80)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_report(
    path: Path,
    results: list[AnalysisResult],
    settings: PipelineSettings,
) -> None:
    """Generate a full XLSX report with 3 sheets.

    Args:
        path: Output file path.
        results: Analysis results from the pipeline.
        settings: Pipeline settings used for this run.
    """
    wb = Workbook()

    ws_main = wb.active
    _write_main_sheet(ws_main, results)

    ws_detail = wb.create_sheet()
    _write_detail_sheet(ws_detail, results)

    ws_ref = wb.create_sheet()
    _write_reference_sheet(ws_ref, settings)

    wb.save(str(path))
    logger.info("Report saved to %s (%d results)", path, len(results))
