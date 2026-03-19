"""Settings panel for configuring pipeline parameters."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from shared.constants import (
    DEFAULT_FUZZY_THRESHOLD,
    DEFAULT_MIN_WORD_LENGTH,
    DEFAULT_TOP_N,
    DEFAULT_VECTOR_THRESHOLD,
)
from shared.types import PipelineSettings

logger = logging.getLogger(__name__)


class SettingsPanel(QWidget):
    """Panel for configuring pipeline settings."""

    settings_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(10)

        # Top-N candidates
        self._top_n = QSpinBox()
        self._top_n.setRange(1, 100)
        self._top_n.setValue(DEFAULT_TOP_N)
        self._top_n.setToolTip("Количество кандидатов из векторного поиска")
        self._top_n.valueChanged.connect(self.settings_changed)
        layout.addRow("Top-N кандидатов:", self._top_n)

        # Vector threshold
        self._vector_threshold = QDoubleSpinBox()
        self._vector_threshold.setRange(0.0, 1.0)
        self._vector_threshold.setSingleStep(0.05)
        self._vector_threshold.setDecimals(2)
        self._vector_threshold.setValue(DEFAULT_VECTOR_THRESHOLD)
        self._vector_threshold.setToolTip("Минимальный cosine similarity для кандидатов")
        self._vector_threshold.valueChanged.connect(self.settings_changed)
        layout.addRow("Порог вектора:", self._vector_threshold)

        # Fuzzy threshold
        self._fuzzy_threshold = QSpinBox()
        self._fuzzy_threshold.setRange(0, 100)
        self._fuzzy_threshold.setValue(DEFAULT_FUZZY_THRESHOLD)
        self._fuzzy_threshold.setToolTip("Минимальный fuzzy score (0-100)")
        self._fuzzy_threshold.valueChanged.connect(self.settings_changed)
        layout.addRow("Порог fuzzy:", self._fuzzy_threshold)

        # Min word length
        self._min_word_length = QSpinBox()
        self._min_word_length.setRange(1, 20)
        self._min_word_length.setValue(DEFAULT_MIN_WORD_LENGTH)
        self._min_word_length.setToolTip("Минимальная длина слова для fuzzy-сравнения")
        self._min_word_length.valueChanged.connect(self.settings_changed)
        layout.addRow("Мин. длина слова:", self._min_word_length)

        # Transliteration direction
        self._translit_dir = QComboBox()
        self._translit_dir.addItem("В латиницу (to_en)", "to_en")
        self._translit_dir.addItem("В кириллицу (to_ru)", "to_ru")
        self._translit_dir.setToolTip("Направление транслитерации при нормализации")
        self._translit_dir.currentIndexChanged.connect(self.settings_changed)
        layout.addRow("Транслитерация:", self._translit_dir)

        # Knowledge base toggle + path
        kb_widget = QWidget()
        kb_layout = QVBoxLayout(kb_widget)
        kb_layout.setContentsMargins(0, 0, 0, 0)
        kb_layout.setSpacing(4)

        self._use_kb = QCheckBox("Использовать базу знаний")
        self._use_kb.setToolTip("Проверять по правилам базы знаний перед анализом")
        self._use_kb.toggled.connect(self._on_kb_toggled)
        self._use_kb.toggled.connect(self.settings_changed)
        kb_layout.addWidget(self._use_kb)

        kb_path_row = QHBoxLayout()
        kb_path_row.setContentsMargins(0, 0, 0, 0)
        self._kb_path_edit = QLineEdit()
        self._kb_path_edit.setReadOnly(True)
        self._kb_path_edit.setPlaceholderText("Путь к knowledge.db...")
        self._kb_path_edit.setEnabled(False)
        kb_path_row.addWidget(self._kb_path_edit, 1)

        self._kb_browse_btn = QPushButton("Обзор...")
        self._kb_browse_btn.setObjectName("btn_secondary")
        self._kb_browse_btn.setFixedWidth(80)
        self._kb_browse_btn.setEnabled(False)
        self._kb_browse_btn.clicked.connect(self._browse_kb)
        kb_path_row.addWidget(self._kb_browse_btn)

        kb_layout.addLayout(kb_path_row)
        layout.addRow("База знаний:", kb_widget)

    def _on_kb_toggled(self, checked: bool) -> None:
        self._kb_path_edit.setEnabled(checked)
        self._kb_browse_btn.setEnabled(checked)

    def _browse_kb(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать базу знаний",
            "",
            "SQLite (*.db *.sqlite);;All Files (*)",
        )
        if path:
            self._kb_path_edit.setText(path)
            self._kb_path_edit.setToolTip(path)
            self.settings_changed.emit()

    def get_settings(self) -> PipelineSettings:
        """Return current settings as a PipelineSettings object."""
        return PipelineSettings(
            top_n=self._top_n.value(),
            vector_threshold=self._vector_threshold.value(),
            fuzzy_threshold=self._fuzzy_threshold.value(),
            transliteration_direction=self._translit_dir.currentData(),
            min_word_length=self._min_word_length.value(),
            use_knowledge_base=self._use_kb.isChecked(),
            kb_path=self._kb_path_edit.text(),
        )

    def set_settings(self, settings: PipelineSettings) -> None:
        """Apply settings to the UI controls."""
        self._top_n.setValue(settings.top_n)
        self._vector_threshold.setValue(settings.vector_threshold)
        self._fuzzy_threshold.setValue(settings.fuzzy_threshold)
        self._min_word_length.setValue(settings.min_word_length)

        idx = self._translit_dir.findData(settings.transliteration_direction)
        if idx >= 0:
            self._translit_dir.setCurrentIndex(idx)

        self._use_kb.setChecked(settings.use_knowledge_base)
        self._kb_path_edit.setText(settings.kb_path)
        self._kb_path_edit.setEnabled(settings.use_knowledge_base)
        self._kb_browse_btn.setEnabled(settings.use_knowledge_base)
