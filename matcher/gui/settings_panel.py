"""Settings panel for configuring pipeline parameters."""

from __future__ import annotations

import logging

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
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
from shared.themes import THEME_NAMES, ThemeManager
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

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(THEME_NAMES)
        self._theme_combo.setToolTip("Тема оформления приложения")
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addRow("Тема:", self._theme_combo)

        self._top_n = QSpinBox()
        self._top_n.setRange(1, 100)
        self._top_n.setValue(DEFAULT_TOP_N)
        self._top_n.setToolTip("Количество кандидатов из векторного поиска")
        self._top_n.valueChanged.connect(self.settings_changed)
        layout.addRow("Top-N кандидатов:", self._top_n)

        self._vector_threshold = QDoubleSpinBox()
        self._vector_threshold.setRange(0.0, 1.0)
        self._vector_threshold.setSingleStep(0.05)
        self._vector_threshold.setDecimals(2)
        self._vector_threshold.setValue(DEFAULT_VECTOR_THRESHOLD)
        self._vector_threshold.setToolTip("Минимальный cosine similarity для кандидатов")
        self._vector_threshold.valueChanged.connect(self.settings_changed)
        layout.addRow("Порог вектора:", self._vector_threshold)

        self._fuzzy_threshold = QSpinBox()
        self._fuzzy_threshold.setRange(0, 100)
        self._fuzzy_threshold.setValue(DEFAULT_FUZZY_THRESHOLD)
        self._fuzzy_threshold.setToolTip("Минимальный fuzzy score (0-100)")
        self._fuzzy_threshold.valueChanged.connect(self.settings_changed)
        layout.addRow("Порог fuzzy:", self._fuzzy_threshold)

        self._min_word_length = QSpinBox()
        self._min_word_length.setRange(1, 20)
        self._min_word_length.setValue(DEFAULT_MIN_WORD_LENGTH)
        self._min_word_length.setToolTip("Минимальная длина слова для fuzzy-сравнения")
        self._min_word_length.valueChanged.connect(self.settings_changed)
        layout.addRow("Мин. длина слова:", self._min_word_length)

        self._translit_dir = QComboBox()
        self._translit_dir.addItem("В латиницу (to_en)", "to_en")
        self._translit_dir.addItem("В кириллицу (to_ru)", "to_ru")
        self._translit_dir.setToolTip("Направление транслитерации при нормализации")
        self._translit_dir.currentIndexChanged.connect(self.settings_changed)
        layout.addRow("Транслитерация:", self._translit_dir)

        self._detail_primary_limit = QSpinBox()
        self._detail_primary_limit.setRange(0, 100)
        self._detail_primary_limit.setValue(0)
        self._detail_primary_limit.setToolTip("Макс. кандидатов из основного яруса (0 = все)")
        self._detail_primary_limit.valueChanged.connect(self.settings_changed)
        layout.addRow("Основной ярус (0=все):", self._detail_primary_limit)

        self._detail_secondary_limit = QSpinBox()
        self._detail_secondary_limit.setRange(0, 100)
        self._detail_secondary_limit.setValue(3)
        self._detail_secondary_limit.setToolTip("Макс. кандидатов из следующего яруса")
        self._detail_secondary_limit.valueChanged.connect(self.settings_changed)
        layout.addRow("Следующий ярус:", self._detail_secondary_limit)

        self._use_preprocessing = QCheckBox("Препроцессинг")
        self._use_preprocessing.setChecked(True)
        self._use_preprocessing.setToolTip("Запускать плагины препроцессинга из папки scripts/")
        self._use_preprocessing.toggled.connect(self.settings_changed)
        layout.addRow("", self._use_preprocessing)

        self._journal_recheck = QCheckBox("Перепроверка журналов")
        self._journal_recheck.setChecked(False)
        self._journal_recheck.setToolTip("Перепроверять записи из журналов проверок")
        self._journal_recheck.toggled.connect(self.settings_changed)
        layout.addRow("", self._journal_recheck)

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
        self._kb_browse_btn.setMinimumWidth(70)
        self._kb_browse_btn.setEnabled(False)
        self._kb_browse_btn.clicked.connect(self._browse_kb)
        kb_path_row.addWidget(self._kb_browse_btn)

        kb_layout.addLayout(kb_path_row)
        layout.addRow("База знаний:", kb_widget)

    def _on_theme_changed(self, name: str) -> None:
        """Apply the selected theme."""
        app = QApplication.instance()
        if app is not None:
            theme_mgr = ThemeManager("matcher")
            app.setStyleSheet(theme_mgr.get_stylesheet(name))
        self.settings_changed.emit()

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
            theme=self._theme_combo.currentText(),
            detail_primary_limit=self._detail_primary_limit.value(),
            detail_secondary_limit=self._detail_secondary_limit.value(),
            use_preprocessing=self._use_preprocessing.isChecked(),
            journal_recheck=self._journal_recheck.isChecked(),
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

        self._detail_primary_limit.setValue(settings.detail_primary_limit)
        self._detail_secondary_limit.setValue(settings.detail_secondary_limit)
        self._use_preprocessing.setChecked(settings.use_preprocessing)

        self._journal_recheck.setChecked(settings.journal_recheck)

        self._use_kb.setChecked(settings.use_knowledge_base)
        self._kb_path_edit.setText(settings.kb_path)
        self._kb_path_edit.setEnabled(settings.use_knowledge_base)
        self._kb_browse_btn.setEnabled(settings.use_knowledge_base)

        theme = getattr(settings, "theme", "Светлая")
        idx = self._theme_combo.findText(theme)
        if idx >= 0:
            self._theme_combo.blockSignals(True)
            self._theme_combo.setCurrentIndex(idx)
            self._theme_combo.blockSignals(False)
