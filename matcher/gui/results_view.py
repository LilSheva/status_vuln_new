"""Results preview: table with analysis results."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared.constants import STATUS_CONDITIONAL, STATUS_EMPTY, STATUS_LINUX, STATUS_NO, STATUS_YES

if TYPE_CHECKING:
    from shared.types import AnalysisResult

logger = logging.getLogger(__name__)

_STATUS_COLORS: dict[str, str] = {
    STATUS_YES: "#27ae60",
    STATUS_NO: "#e74c3c",
    STATUS_LINUX: "#2980b9",
    STATUS_CONDITIONAL: "#f39c12",
    STATUS_EMPTY: "#bdc3c7",
}

_COLUMNS = [
    "CVE ID",
    "Вендор",
    "Продукт",
    "Статус",
    "Источник",
    "ППТС ID",
    "Ответственный",
    "Лучший кандидат",
    "Балл",
]


class ResultsView(QWidget):
    """Table view for displaying analysis results."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._results: list[AnalysisResult] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setDefaultSectionSize(28)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(60)

        layout.addWidget(self._table)

    def set_results(self, results: list[AnalysisResult]) -> None:
        """Populate the table with analysis results."""
        self._results = results
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(results))

        for row, result in enumerate(results):
            vuln = result.vulnerability

            self._set_cell(row, 0, vuln.cve_id)
            self._set_cell(row, 1, vuln.vendor)
            self._set_cell(row, 2, vuln.product)

            # Status with color
            status_item = QTableWidgetItem(result.status or "(пусто)")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = _STATUS_COLORS.get(result.status, _STATUS_COLORS[STATUS_EMPTY])
            status_item.setForeground(QBrush(QColor(color)))
            status_item.setData(Qt.ItemDataRole.UserRole, result.status)
            self._table.setItem(row, 3, status_item)

            # Source
            source_display = {
                "journal": "Журнал",
                "knowledge_base": "БЗ",
                "auto_no_match": "Авто",
                "manual": "Ручной",
            }.get(result.status_source, result.status_source)
            self._set_cell(row, 4, source_display)

            self._set_cell(row, 5, result.ppts_id or "")
            self._set_cell(row, 6, result.responsible or "")

            # Best candidate
            if result.candidates:
                best = result.candidates[0]
                self._set_cell(row, 7, best.software.name)
                score_item = QTableWidgetItem(f"{best.combined_score:.3f}")
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                score_item.setData(Qt.ItemDataRole.UserRole, best.combined_score)
                self._table.setItem(row, 8, score_item)
            else:
                self._set_cell(row, 7, "")
                self._set_cell(row, 8, "")

        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()
        logger.info("Displayed %d results", len(results))

    def clear(self) -> None:
        """Remove all rows."""
        self._table.setRowCount(0)
        self._results = []

    def get_results(self) -> list[AnalysisResult]:
        """Return the currently displayed results."""
        return self._results

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        self._table.setItem(row, col, item)
