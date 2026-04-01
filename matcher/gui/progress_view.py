"""Progress view: progress bar and log output."""

from __future__ import annotations

import logging
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ProgressView(QWidget):
    """Widget showing pipeline progress and log messages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._stage_label = QLabel("Готов к анализу")
        self._stage_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._stage_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(5000)
        layout.addWidget(self._log, 1)

    def update_progress(self, stage: str, current: int, total: int) -> None:
        """Update the progress display."""
        self._stage_label.setText(stage)
        if total > 0:
            pct = int(current / total * 100)
            self._progress_bar.setValue(pct)
            self._progress_bar.setFormat(f"{stage}: {current}/{total} ({pct}%)")
        else:
            self._progress_bar.setValue(0)
            self._progress_bar.setFormat(stage)

    def log(self, message: str) -> None:
        """Append a timestamped log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log.appendPlainText(f"[{timestamp}] {message}")

    def reset(self) -> None:
        """Reset progress to initial state."""
        self._stage_label.setText("Готов к анализу")
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("")
        self._log.clear()

    def set_finished(self, result_count: int) -> None:
        """Mark the pipeline as finished."""
        self._progress_bar.setValue(100)
        self._stage_label.setText(f"Анализ завершён — {result_count} записей")
        self.log(f"Анализ завершён: {result_count} записей обработано")

    def set_error(self, error_text: str) -> None:
        """Display an error state."""
        self._stage_label.setText("Ошибка")
        self.log(f"ОШИБКА: {error_text}")
