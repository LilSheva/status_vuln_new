"""Dialog for creating and editing knowledge base rules."""

from __future__ import annotations

import logging
import re

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from shared.constants import ALL_MATCH_TYPES, ALL_STATUSES, MATCH_VECTOR
from shared.types import KnowledgeBaseRule

logger = logging.getLogger(__name__)

_MATCH_TYPE_LABELS = {
    "exact": "exact — точное совпадение",
    "contains": "contains — подстрока",
    "regex": "regex — регулярное выражение",
    "vector": "vector — векторное сравнение",
}


def _make_match_type_combo() -> QComboBox:
    """Create a match type combo box."""
    combo = QComboBox()
    for mt in ALL_MATCH_TYPES:
        combo.addItem(_MATCH_TYPE_LABELS.get(mt, mt), mt)
    return combo


class RuleEditorDialog(QDialog):
    """Dialog for creating or editing a single rule with separate vendor/product patterns."""

    def __init__(
        self,
        rule: KnowledgeBaseRule | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule = rule
        self._result_rule: KnowledgeBaseRule | None = None
        self._setup_ui()
        if rule is not None:
            self._populate(rule)

    def _setup_ui(self) -> None:
        is_edit = self._rule is not None
        self.setWindowTitle("Редактировать правило" if is_edit else "Новое правило")
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        vendor_group = QGroupBox("Паттерн вендора (опционально)")
        vendor_form = QFormLayout(vendor_group)
        vendor_form.setSpacing(8)

        self._vendor_pattern = QLineEdit()
        self._vendor_pattern.setPlaceholderText("Пусто = любой вендор")
        vendor_form.addRow("Паттерн:", self._vendor_pattern)

        self._vendor_match_type = _make_match_type_combo()
        idx = self._vendor_match_type.findData("contains")
        if idx >= 0:
            self._vendor_match_type.setCurrentIndex(idx)
        vendor_form.addRow("Тип:", self._vendor_match_type)

        layout.addWidget(vendor_group)

        product_group = QGroupBox("Паттерн продукта")
        product_form = QFormLayout(product_group)
        product_form.setSpacing(8)

        self._product_pattern = QLineEdit()
        self._product_pattern.setPlaceholderText("Текст для сопоставления по продукту...")
        product_form.addRow("Паттерн:", self._product_pattern)

        self._product_match_type = _make_match_type_combo()
        product_form.addRow("Тип:", self._product_match_type)

        layout.addWidget(product_group)

        common_form = QFormLayout()
        common_form.setSpacing(8)

        self._status = QComboBox()
        for st in ALL_STATUSES:
            self._status.addItem(st, st)
        common_form.addRow("Статус:", self._status)

        self._ppts_id = QLineEdit()
        self._ppts_id.setPlaceholderText("Опционально...")
        common_form.addRow("ППТС ID:", self._ppts_id)

        self._threshold_widget = QWidget()
        thr_layout = QHBoxLayout(self._threshold_widget)
        thr_layout.setContentsMargins(0, 0, 0, 0)
        self._threshold_spin = QDoubleSpinBox()
        self._threshold_spin.setRange(0.0, 1.0)
        self._threshold_spin.setSingleStep(0.05)
        self._threshold_spin.setDecimals(2)
        self._threshold_spin.setValue(0.7)
        thr_layout.addWidget(self._threshold_spin)
        thr_layout.addWidget(QLabel("(0.0 — 1.0)"))
        thr_layout.addStretch()
        self._threshold_widget.setVisible(False)
        common_form.addRow("Порог вектора:", self._threshold_widget)

        self._product_match_type.currentIndexChanged.connect(self._on_match_type_changed)
        self._vendor_match_type.currentIndexChanged.connect(self._on_match_type_changed)

        self._comment = QTextEdit()
        self._comment.setPlaceholderText("Комментарий аналитика...")
        self._comment.setMaximumHeight(70)
        common_form.addRow("Комментарий:", self._comment)

        layout.addLayout(common_form)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("btn_secondary")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._on_save)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

    def _on_match_type_changed(self) -> None:
        is_vector = (
            self._product_match_type.currentData() == MATCH_VECTOR
            or self._vendor_match_type.currentData() == MATCH_VECTOR
        )
        self._threshold_widget.setVisible(is_vector)

    def _populate(self, rule: KnowledgeBaseRule) -> None:
        """Fill UI controls from an existing rule."""
        self._product_pattern.setText(rule.pattern)
        idx = self._product_match_type.findData(rule.match_type)
        if idx >= 0:
            self._product_match_type.setCurrentIndex(idx)

        self._vendor_pattern.setText(rule.vendor_pattern)
        idx = self._vendor_match_type.findData(rule.vendor_match_type)
        if idx >= 0:
            self._vendor_match_type.setCurrentIndex(idx)

        idx = self._status.findData(rule.status)
        if idx >= 0:
            self._status.setCurrentIndex(idx)

        self._ppts_id.setText(rule.ppts_id or "")

        if rule.vector_threshold is not None:
            self._threshold_spin.setValue(rule.vector_threshold)

        self._comment.setPlainText(rule.comment or "")
        self._on_match_type_changed()

    def _on_save(self) -> None:
        """Validate and accept."""
        product_pattern = self._product_pattern.text().strip()
        vendor_pattern = self._vendor_pattern.text().strip()

        if not product_pattern and not vendor_pattern:
            QMessageBox.warning(
                self, "Ошибка",
                "Укажите хотя бы один паттерн (вендор или продукт).",
            )
            self._product_pattern.setFocus()
            return

        product_mt = self._product_match_type.currentData()
        vendor_mt = self._vendor_match_type.currentData()

        for label, pat, mt in [
            ("продукта", product_pattern, product_mt),
            ("вендора", vendor_pattern, vendor_mt),
        ]:
            if pat and mt == "regex":
                try:
                    re.compile(pat)
                except re.error as exc:
                    QMessageBox.warning(
                        self, "Ошибка",
                        f"Некорректное регулярное выражение {label}:\n{exc}",
                    )
                    return

        vector_threshold = None
        if product_mt == MATCH_VECTOR or vendor_mt == MATCH_VECTOR:
            vector_threshold = self._threshold_spin.value()

        self._result_rule = KnowledgeBaseRule(
            id=self._rule.id if self._rule else None,
            pattern=product_pattern,
            match_type=product_mt,
            vendor_pattern=vendor_pattern,
            vendor_match_type=vendor_mt,
            status=self._status.currentData(),
            ppts_id=self._ppts_id.text().strip() or None,
            vector_threshold=vector_threshold,
            comment=self._comment.toPlainText().strip() or None,
            match_count=self._rule.match_count if self._rule else 0,
        )
        self.accept()

    def get_rule(self) -> KnowledgeBaseRule | None:
        """Return the edited rule, or None if cancelled."""
        return self._result_rule
