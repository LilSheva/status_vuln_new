"""Results preview: table with analysis results."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QStyledItemDelegate,
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

_COL_STATUS = 3
_COL_SOURCE = 4
_COL_PPTS_ID = 5

# Stores original result index in each item so sorting doesn't break edits.
_ROLE_RESULT_IDX = Qt.ItemDataRole.UserRole + 100

_STATUS_OPTIONS: list[str] = [STATUS_EMPTY, STATUS_YES, STATUS_NO, STATUS_LINUX, STATUS_CONDITIONAL]


class _EditDelegate(QStyledItemDelegate):
    """Provides a combo box for the Status column and a line edit for ППТС ID.
    All other columns are read-only.
    """

    def createEditor(self, parent, option, index):  # noqa: ANN001
        if index.column() == _COL_STATUS:
            combo = QComboBox(parent)
            combo.addItems(["(пусто)" if not s else s for s in _STATUS_OPTIONS])
            # Open the dropdown automatically after the editor is placed.
            QTimer.singleShot(0, combo.showPopup)
            return combo
        if index.column() == _COL_PPTS_ID:
            return super().createEditor(parent, option, index)
        return None  # read-only

    def setEditorData(self, editor, index):  # noqa: ANN001
        if index.column() == _COL_STATUS:
            current = index.data(Qt.ItemDataRole.UserRole) or ""
            idx = _STATUS_OPTIONS.index(current) if current in _STATUS_OPTIONS else 0
            editor.setCurrentIndex(idx)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):  # noqa: ANN001
        if index.column() == _COL_STATUS:
            # Only update UserRole here; _on_item_changed handles display + color.
            value = _STATUS_OPTIONS[editor.currentIndex()]
            model.setData(index, value, Qt.ItemDataRole.UserRole)
        else:
            super().setModelData(editor, model, index)

    def paint(self, painter, option, index):  # noqa: ANN001
        super().paint(painter, option, index)
        if index.column() == _COL_STATUS:
            # Draw a small dropdown arrow indicator on the right edge of the cell.
            painter.save()
            painter.setPen(QColor("#888888"))
            painter.drawText(
                option.rect.adjusted(0, 0, -3, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "▾",
            )
            painter.restore()


class ResultsView(QWidget):
    """Table view for displaying analysis results with inline status/ППТС ID editing."""

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
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.setItemDelegate(_EditDelegate(self._table))

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(60)

        self._table.itemChanged.connect(self._on_item_changed)

        layout.addWidget(self._table)

    def set_results(self, results: list[AnalysisResult]) -> None:
        """Populate the table with analysis results."""
        self._results = results
        self._table.blockSignals(True)
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(results))

        for row, result in enumerate(results):
            vuln = result.vulnerability

            self._set_cell(row, 0, vuln.cve_id, row)
            self._set_cell(row, 1, vuln.vendor, row)
            self._set_cell(row, 2, vuln.product, row)

            # Status with color
            status_item = QTableWidgetItem(result.status or "(пусто)")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = _STATUS_COLORS.get(result.status, _STATUS_COLORS[STATUS_EMPTY])
            status_item.setForeground(QBrush(QColor(color)))
            status_item.setData(Qt.ItemDataRole.UserRole, result.status)
            status_item.setData(_ROLE_RESULT_IDX, row)
            self._table.setItem(row, _COL_STATUS, status_item)

            source_display = {
                "journal": "Журнал",
                "knowledge_base": "БЗ",
                "auto_no_match": "Авто",
                "manual": "Ручной",
            }.get(result.status_source, result.status_source)
            self._set_cell(row, _COL_SOURCE, source_display, row)

            self._set_cell(row, _COL_PPTS_ID, result.ppts_id or "", row)
            self._set_cell(row, 6, result.responsible or "", row)

            if result.candidates:
                best = result.candidates[0]
                self._set_cell(row, 7, best.software.name, row)
                score_item = QTableWidgetItem(f"{best.combined_score:.3f}")
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                score_item.setData(Qt.ItemDataRole.UserRole, best.combined_score)
                score_item.setData(_ROLE_RESULT_IDX, row)
                self._table.setItem(row, 8, score_item)
            else:
                self._set_cell(row, 7, "", row)
                self._set_cell(row, 8, "", row)

        self._table.setSortingEnabled(True)
        self._table.blockSignals(False)
        self._table.resizeColumnsToContents()
        logger.info("Displayed %d results", len(results))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Sync AnalysisResult when user edits status or ППТС ID."""
        col = item.column()
        if col not in (_COL_STATUS, _COL_PPTS_ID):
            return
        result_idx = item.data(_ROLE_RESULT_IDX)
        if result_idx is None or result_idx >= len(self._results):
            return

        self._table.blockSignals(True)
        try:
            if col == _COL_STATUS:
                value = item.data(Qt.ItemDataRole.UserRole) or ""
                self._results[result_idx].status = value
                self._results[result_idx].status_source = "manual"
                # Update display text and color
                item.setText(value if value else "(пусто)")
                color = _STATUS_COLORS.get(value, _STATUS_COLORS[STATUS_EMPTY])
                item.setForeground(QBrush(QColor(color)))
                # Update source cell in the same table row
                src_item = self._table.item(item.row(), _COL_SOURCE)
                if src_item:
                    src_item.setText("Ручной")
            elif col == _COL_PPTS_ID:
                value = item.text().strip()
                self._results[result_idx].ppts_id = value or None
        finally:
            self._table.blockSignals(False)

    def clear(self) -> None:
        """Remove all rows."""
        self._table.setRowCount(0)
        self._results = []

    def get_results(self) -> list[AnalysisResult]:
        """Return results with any manual edits applied."""
        return self._results

    def _set_cell(self, row: int, col: int, text: str, result_idx: int | None = None) -> None:
        item = QTableWidgetItem(text)
        if result_idx is not None:
            item.setData(_ROLE_RESULT_IDX, result_idx)
        self._table.setItem(row, col, item)
