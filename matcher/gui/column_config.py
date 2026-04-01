"""Dialog for configuring PPTS column mappings."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from matcher.io.readers import ReaderError, auto_detect_ppts_mapping, read_ppts_headers
from shared.types import PptsColumnMapping

logger = logging.getLogger(__name__)

_NOT_SET = "(не выбран)"


class ColumnConfigDialog(QDialog):
    """Dialog for selecting which columns map to ID, Name, and Vendor."""

    def __init__(
        self,
        file_path: str,
        current_mapping: PptsColumnMapping | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._file_path = file_path
        self._result: PptsColumnMapping | None = None
        self._headers: list[str] = []

        try:
            self._headers = read_ppts_headers(file_path)
        except ReaderError as exc:
            logger.warning("Cannot read headers from %s: %s", file_path, exc)

        self._setup_ui(current_mapping)

    def _setup_ui(self, current: PptsColumnMapping | None) -> None:
        self.setWindowTitle(f"Настройка столбцов — {Path(self._file_path).name}")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(
            f"Файл: <b>{Path(self._file_path).name}</b><br>"
            f"Столбцов: <b>{len(self._headers)}</b>"
        )
        info.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        items = [_NOT_SET] + [
            f"[{chr(65 + i)}] {h}" if i < 26 else f"[{i}] {h}"
            for i, h in enumerate(self._headers)
        ]

        auto = None
        if current is None or current.col_name is None:
            try:
                auto = auto_detect_ppts_mapping(self._file_path)
            except Exception:
                pass

        self._combo_id = QComboBox()
        self._combo_id.addItems(items)
        preset_id = (current.col_id if current and current.col_id is not None
                     else (auto.col_id if auto and auto.col_id is not None else None))
        if preset_id is not None:
            self._combo_id.setCurrentIndex(preset_id + 1)
        form.addRow("ID ППТС:", self._combo_id)

        self._combo_name = QComboBox()
        self._combo_name.addItems(items)
        preset_name = (current.col_name if current and current.col_name is not None
                       else (auto.col_name if auto and auto.col_name is not None else None))
        if preset_name is not None:
            self._combo_name.setCurrentIndex(preset_name + 1)
        form.addRow("Наименование ПО:", self._combo_name)

        self._combo_vendor = QComboBox()
        self._combo_vendor.addItems(items)
        preset_vendor = (current.col_vendor if current and current.col_vendor is not None
                         else (auto.col_vendor if auto and auto.col_vendor is not None else None))
        if preset_vendor is not None:
            self._combo_vendor.setCurrentIndex(preset_vendor + 1)
        form.addRow("Вендор:", self._combo_vendor)

        layout.addLayout(form)

        preview_label = QLabel("Первые строки для проверки будут видны после сохранения.")
        preview_label.setObjectName("preview_hint")
        layout.addWidget(preview_label)

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

    def _combo_to_index(self, combo: QComboBox) -> int | None:
        """Convert combo selection to 0-based column index, or None if unset."""
        idx = combo.currentIndex()
        if idx <= 0:
            return None
        return idx - 1

    def _on_save(self) -> None:
        col_name = self._combo_to_index(self._combo_name)
        if col_name is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", "Столбец «Наименование ПО» обязателен.")
            return

        self._result = PptsColumnMapping(
            file_path=self._file_path,
            col_id=self._combo_to_index(self._combo_id),
            col_name=col_name,
            col_vendor=self._combo_to_index(self._combo_vendor),
            headers=self._headers,
        )
        self.accept()

    def get_mapping(self) -> PptsColumnMapping | None:
        """Return the configured mapping, or None if cancelled."""
        return self._result
