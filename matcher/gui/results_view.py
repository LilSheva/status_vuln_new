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

from shared.constants import STATUS_CONDITIONAL, STATUS_EMPTY, STATUS_LINUX, STATUS_NO, STATUS_REPEAT, STATUS_YES
from shared.gui.marquee_header import MarqueeHeaderView

if TYPE_CHECKING:
    from shared.types import AnalysisResult

logger = logging.getLogger(__name__)

_STATUS_COLORS: dict[str, str] = {
    STATUS_YES: "#27ae60",
    STATUS_NO: "#e74c3c",
    STATUS_LINUX: "#2980b9",
    STATUS_CONDITIONAL: "#f39c12",
    STATUS_REPEAT: "#c0392b",
    STATUS_EMPTY: "#bdc3c7",
}

_COLUMNS = [
    "CVE ID",
    "Продукт",
    "Статус",
    "Источник",
    "ППТС ID",
    "Лучший кандидат",
    "Балл",
]

_COL_STATUS = 2
_COL_SOURCE = 3
_COL_PPTS_ID = 4

_ROLE_RESULT_IDX = Qt.ItemDataRole.UserRole + 100

_STATUS_OPTIONS: list[str] = [STATUS_EMPTY, STATUS_YES, STATUS_NO, STATUS_LINUX, STATUS_CONDITIONAL, STATUS_REPEAT]


class _EditDelegate(QStyledItemDelegate):
    """Combo box for Status, line edit for ППТС ID, read-only otherwise."""

    def createEditor(self, parent, option, index):  # noqa: ANN001
        if index.column() == _COL_STATUS:
            combo = QComboBox(parent)
            combo.addItems(["(пусто)" if not s else s for s in _STATUS_OPTIONS])
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
            value = _STATUS_OPTIONS[editor.currentIndex()]
            model.setData(index, value, Qt.ItemDataRole.UserRole)
        else:
            super().setModelData(editor, model, index)

    def paint(self, painter, option, index):  # noqa: ANN001
        super().paint(painter, option, index)
        if index.column() == _COL_STATUS:
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

        marquee_header = MarqueeHeaderView(Qt.Orientation.Horizontal, self._table)
        self._table.setHorizontalHeader(marquee_header)
        marquee_header.setStretchLastSection(True)
        marquee_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        marquee_header.setMinimumSectionSize(60)

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
            if getattr(vuln, "cvss", "") == "10.0":
                cve_item = self._table.item(row, 0)
                if cve_item is not None:
                    cve_item.setToolTip("F")
            product_display = f"{vuln.vendor} - {vuln.product}" if vuln.vendor else vuln.product
            self._set_cell(row, 1, product_display, row)

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

            if result.candidates:
                best = result.candidates[0]
                best_display = f"{best.software.vendor} - {best.software.name}" if best.software.vendor else best.software.name
                self._set_cell(row, 5, best_display, row)
                score_item = QTableWidgetItem(f"{best.combined_score:.3f}")
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                score_item.setData(Qt.ItemDataRole.UserRole, best.combined_score)
                score_item.setData(_ROLE_RESULT_IDX, row)
                self._table.setItem(row, 6, score_item)
            else:
                self._set_cell(row, 5, "", row)
                self._set_cell(row, 6, "", row)

        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.blockSignals(False)
        self._table.resizeColumnsToContents()
        logger.info("Displayed %d results", len(results))

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        """Sync AnalysisResult when user edits status or PPTS ID."""
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
                item.setText(value if value else "(пусто)")
                color = _STATUS_COLORS.get(value, _STATUS_COLORS[STATUS_EMPTY])
                item.setForeground(QBrush(QColor(color)))
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
