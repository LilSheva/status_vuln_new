"""Dialog for testing a rule against sample data."""

from __future__ import annotations

import logging
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared.constants import MATCH_CONTAINS, MATCH_EXACT, MATCH_REGEX
from shared.types import KnowledgeBaseRule

logger = logging.getLogger(__name__)


class RuleTesterDialog(QDialog):
    """Dialog for testing a knowledge base rule against sample texts."""

    def __init__(
        self,
        rule: KnowledgeBaseRule,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule = rule
        self._setup_ui()

    def _setup_ui(self) -> None:
        title_parts = []
        if self._rule.vendor_pattern:
            title_parts.append(f"Вендор: {self._rule.vendor_pattern}")
        if self._rule.pattern:
            title_parts.append(f"Продукт: {self._rule.pattern}")
        self.setWindowTitle(f"Тест правила — {' | '.join(title_parts)}"[:80])
        self.setMinimumSize(650, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        info_parts = []
        if self._rule.vendor_pattern:
            info_parts.append(
                f"Вендор: <b>{self._rule.vendor_pattern}</b> ({self._rule.vendor_match_type})"
            )
        else:
            info_parts.append("Вендор: <i>любой</i>")
        if self._rule.pattern:
            info_parts.append(
                f"Продукт: <b>{self._rule.pattern}</b> ({self._rule.match_type})"
            )
        else:
            info_parts.append("Продукт: <i>любой</i>")
        info_parts.append(f"Статус: <b>{self._rule.status}</b>")

        info = QLabel(" | ".join(info_parts))
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addWidget(QLabel(
            "Введите тестовые данные (по строке: Вендор, Продукт):"
        ))
        self._input = QPlainTextEdit()
        self._input.setPlaceholderText(
            "Microsoft, Windows 10 Pro\n"
            "Apache, HTTP Server 2.4\n"
            "Red Hat, Enterprise Linux 8"
        )
        self._input.setMaximumHeight(120)
        layout.addWidget(self._input)

        btn_row = QHBoxLayout()
        btn_test = QPushButton("Проверить")
        btn_test.clicked.connect(self._run_test)
        btn_row.addWidget(btn_test)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Результаты:"))
        self._results_table = QTableWidget()
        self._results_table.setColumnCount(4)
        self._results_table.setHorizontalHeaderLabels([
            "Вендор", "Продукт", "Вендор?", "Продукт?"
        ])
        self._results_table.horizontalHeader().setStretchLastSection(True)
        self._results_table.setAlternatingRowColors(True)
        layout.addWidget(self._results_table, 1)

        btn_close = QPushButton("Закрыть")
        btn_close.setObjectName("btn_secondary")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)

    def _run_test(self) -> None:
        """Test the rule against all input lines."""
        lines = [
            line.strip()
            for line in self._input.toPlainText().splitlines()
            if line.strip()
        ]
        if not lines:
            return

        self._results_table.setRowCount(len(lines))

        for row, line in enumerate(lines):
            if ", " in line:
                vendor, product = line.split(", ", 1)
            elif " - " in line:
                vendor, product = line.split(" - ", 1)
            else:
                vendor, product = "", line

            vendor_ok = self._test_pattern(
                vendor, self._rule.vendor_pattern, self._rule.vendor_match_type
            ) if self._rule.vendor_pattern else True

            product_ok = self._test_pattern(
                product, self._rule.pattern, self._rule.match_type
            ) if self._rule.pattern else True

            both_ok = vendor_ok and product_ok

            self._results_table.setItem(row, 0, QTableWidgetItem(vendor))
            self._results_table.setItem(row, 1, QTableWidgetItem(product))

            v_item = QTableWidgetItem("да" if vendor_ok else "нет")
            v_item.setForeground(Qt.GlobalColor.darkGreen if vendor_ok else Qt.GlobalColor.darkRed)
            self._results_table.setItem(row, 2, v_item)

            p_item = QTableWidgetItem("да" if product_ok else "нет")
            p_item.setForeground(Qt.GlobalColor.darkGreen if product_ok else Qt.GlobalColor.darkRed)
            self._results_table.setItem(row, 3, p_item)

            if both_ok:
                for col in range(4):
                    item = self._results_table.item(row, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.green)

        self._results_table.resizeColumnsToContents()

    def _test_pattern(self, text: str, pattern: str, match_type: str) -> bool:
        """Test a single text against a pattern."""
        if not pattern:
            return True
        text_lower = text.strip().lower()
        pattern_lower = pattern.lower()

        if match_type == MATCH_EXACT:
            return text_lower == pattern_lower
        if match_type == MATCH_CONTAINS:
            return pattern_lower in text_lower
        if match_type == MATCH_REGEX:
            try:
                return bool(re.search(pattern, text, re.IGNORECASE))
            except re.error:
                return False
        return False
