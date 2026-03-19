"""Rules table with search and filtering."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared.constants import ALL_MATCH_TYPES, ALL_STATUSES
from shared.db.repository import get_all_rules, search_rules

if TYPE_CHECKING:
    from shared.types import KnowledgeBaseRule

logger = logging.getLogger(__name__)

_COLUMNS = [
    "ID",
    "Вендор",
    "Тип В",
    "Продукт",
    "Тип П",
    "Статус",
    "ППТС ID",
    "Комментарий",
    "Срабатываний",
]

_STATUS_COLORS: dict[str, str] = {
    "ДА": "#27ae60",
    "НЕТ": "#e74c3c",
    "ЛИНУКС": "#2980b9",
    "УСЛОВНО": "#f39c12",
}


class RulesTable(QWidget):
    """Table displaying knowledge base rules with search and filter controls."""

    rule_selected = Signal(int)  # rule id
    rule_double_clicked = Signal(int)  # rule id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: sqlite3.Connection | None = None
        self._rules: list[KnowledgeBaseRule] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # --- Filter bar ---
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        filter_row.addWidget(QLabel("Поиск:"))
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Поиск по паттерну...")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._search_edit, 1)

        filter_row.addWidget(QLabel("Тип:"))
        self._type_filter = QComboBox()
        self._type_filter.addItem("Все", None)
        for mt in ALL_MATCH_TYPES:
            self._type_filter.addItem(mt, mt)
        self._type_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._type_filter)

        filter_row.addWidget(QLabel("Статус:"))
        self._status_filter = QComboBox()
        self._status_filter.addItem("Все", None)
        for st in ALL_STATUSES:
            self._status_filter.addItem(st, st)
        self._status_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._status_filter)

        layout.addLayout(filter_row)

        # --- Stats ---
        self._stats_label = QLabel("")
        self._stats_label.setObjectName("stats_label")
        layout.addWidget(self._stats_label)

        # --- Table ---
        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setDefaultSectionSize(28)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(50)

        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_double_click)

        layout.addWidget(self._table, 1)

    def set_connection(self, conn: sqlite3.Connection) -> None:
        """Set the database connection and refresh."""
        self._conn = conn
        self.refresh()

    def refresh(self) -> None:
        """Reload rules from the database with current filters."""
        if self._conn is None:
            return
        self._on_filter_changed()

    def _on_filter_changed(self) -> None:
        """Reload rules based on current filter values."""
        if self._conn is None:
            return

        pattern = self._search_edit.text().strip() or None
        match_type = self._type_filter.currentData()
        status = self._status_filter.currentData()

        if pattern or match_type or status:
            self._rules = search_rules(
                self._conn, pattern=pattern, match_type=match_type, status=status
            )
        else:
            self._rules = get_all_rules(self._conn)

        self._populate_table()

    def _populate_table(self) -> None:
        """Fill the table with current rules list."""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._rules))

        for row, rule in enumerate(self._rules):
            id_item = QTableWidgetItem()
            id_item.setData(Qt.ItemDataRole.DisplayRole, rule.id)
            self._table.setItem(row, 0, id_item)

            self._table.setItem(row, 1, QTableWidgetItem(rule.vendor_pattern or "*"))
            self._table.setItem(row, 2, QTableWidgetItem(rule.vendor_match_type if rule.vendor_pattern else ""))
            self._table.setItem(row, 3, QTableWidgetItem(rule.pattern or "*"))
            self._table.setItem(row, 4, QTableWidgetItem(rule.match_type if rule.pattern else ""))

            status_item = QTableWidgetItem(rule.status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            color = _STATUS_COLORS.get(rule.status)
            if color:
                status_item.setForeground(QBrush(QColor(color)))
            self._table.setItem(row, 5, status_item)

            self._table.setItem(row, 6, QTableWidgetItem(rule.ppts_id or ""))
            self._table.setItem(row, 7, QTableWidgetItem(rule.comment or ""))

            count_item = QTableWidgetItem()
            count_item.setData(Qt.ItemDataRole.DisplayRole, rule.match_count)
            self._table.setItem(row, 8, count_item)

        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()

        total = len(get_all_rules(self._conn)) if self._conn else 0
        shown = len(self._rules)
        self._stats_label.setText(
            f"Показано: {shown} из {total} правил"
            if shown != total
            else f"Всего: {total} правил"
        )

    def _on_selection_changed(self) -> None:
        rule_id = self.selected_rule_id()
        if rule_id is not None:
            self.rule_selected.emit(rule_id)

    def _on_double_click(self) -> None:
        rule_id = self.selected_rule_id()
        if rule_id is not None:
            self.rule_double_clicked.emit(rule_id)

    def selected_rule_id(self) -> int | None:
        """Return the ID of the currently selected rule, or None."""
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        item = self._table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.DisplayRole)
