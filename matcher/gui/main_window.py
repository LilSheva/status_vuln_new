"""Main window for the Matcher application."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from matcher.config import (
    load_ppts_mappings,
    load_responsible_data,
    load_settings,
    save_ppts_mappings,
    save_responsible_data,
    save_settings,
)
from matcher.core.pipeline import Pipeline
from matcher.gui.file_loader import FileLoaderPanel
from matcher.gui.progress_view import ProgressView
from matcher.gui.results_view import ResultsView
from matcher.gui.settings_panel import SettingsPanel
from matcher.io.readers import ReaderError, read_journal, read_ppts, read_tsu

if TYPE_CHECKING:
    from shared.types import AnalysisResult, JournalEntry, PipelineSettings, Software, Vulnerability

logger = logging.getLogger(__name__)


class _PipelineWorker(QObject):
    """Worker that runs the pipeline in a background thread."""

    progress = Signal(str, int, int)  # stage, current, total
    finished = Signal(list)  # list[AnalysisResult]
    error = Signal(str)
    log_message = Signal(str)

    def __init__(
        self,
        settings: PipelineSettings,
        vulnerabilities: list[Vulnerability],
        software_list: list[Software],
        journal_entries: list[JournalEntry] | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._vulnerabilities = vulnerabilities
        self._software_list = software_list
        self._journal_entries = journal_entries

    @Slot()
    def run(self) -> None:
        """Execute the pipeline."""
        try:
            pipeline = Pipeline(self._settings)
            pipeline.set_progress_callback(self._on_progress)
            results = pipeline.run(
                self._vulnerabilities, self._software_list, self._journal_entries
            )
            self.finished.emit(results)
        except Exception as exc:
            logger.exception("Pipeline failed")
            self.error.emit(str(exc))

    def _on_progress(self, stage: str, current: int, total: int) -> None:
        self.progress.emit(stage, current, total)


class MainWindow(QMainWindow):
    """Main application window for the Matcher."""

    def __init__(self) -> None:
        super().__init__()
        self._worker: _PipelineWorker | None = None
        self._thread: QThread | None = None
        self._results: list[AnalysisResult] = []
        self._setup_ui()
        self._load_saved_settings()
        self._load_saved_mappings()
        self._load_responsible_data()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Сопоставитель уязвимостей v2.0")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 12, 16, 12)

        # --- Header ---
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        title = QLabel("Сопоставитель уязвимостей")
        title.setObjectName("title_label")
        header_layout.addWidget(title)

        subtitle = QLabel("Автоматический анализ ТСУ vs ППТС")
        subtitle.setObjectName("subtitle_label")
        header_layout.addWidget(subtitle)

        main_layout.addWidget(header)

        # --- Top area: files + settings ---
        top_splitter = QSplitter()

        # Left: file loading
        files_group = QGroupBox("Файлы")
        files_layout = QVBoxLayout(files_group)
        self._file_loader = FileLoaderPanel()
        files_layout.addWidget(self._file_loader)
        top_splitter.addWidget(files_group)

        # Right: settings
        settings_group = QGroupBox("Параметры")
        settings_layout = QVBoxLayout(settings_group)
        self._settings_panel = SettingsPanel()
        settings_layout.addWidget(self._settings_panel)
        top_splitter.addWidget(settings_group)

        top_splitter.setSizes([500, 400])
        main_layout.addWidget(top_splitter)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_run = QPushButton("Запустить анализ")
        self._btn_run.setEnabled(False)
        btn_row.addWidget(self._btn_run)

        self._btn_export = QPushButton("Экспорт XLSX")
        self._btn_export.setObjectName("btn_secondary")
        self._btn_export.setEnabled(False)
        btn_row.addWidget(self._btn_export)

        btn_row.addSpacing(20)

        btn_row.addWidget(QLabel("Ответственный:"))
        self._responsible_combo = QComboBox()
        self._responsible_combo.setEditable(True)
        self._responsible_combo.setMinimumWidth(180)
        self._responsible_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._responsible_combo.lineEdit().setPlaceholderText("Фамилия И.О.")
        btn_row.addWidget(self._responsible_combo)

        btn_row.addSpacing(10)

        btn_row.addWidget(QLabel("Публикация:"))
        self._publication_combo = QComboBox()
        self._publication_combo.addItems(["БДУ ФСТЕК", "RSS"])
        self._publication_combo.setMinimumWidth(110)
        btn_row.addWidget(self._publication_combo)

        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        # --- Bottom area: progress + results ---
        bottom_splitter = QSplitter()
        bottom_splitter.setOrientation(Qt.Orientation.Vertical)

        self._progress_view = ProgressView()
        bottom_splitter.addWidget(self._progress_view)

        self._results_view = ResultsView()
        bottom_splitter.addWidget(self._results_view)

        bottom_splitter.setSizes([200, 400])
        main_layout.addWidget(bottom_splitter, 1)

        # --- Status bar ---
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Готов")

    def _connect_signals(self) -> None:
        self._file_loader.files_changed.connect(self._on_files_changed)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_export.clicked.connect(self._on_export)

    def _load_responsible_data(self) -> None:
        """Populate the responsible and publication combos from saved config."""
        data = load_responsible_data()
        persons: list[str] = data.get("persons", [])  # type: ignore[assignment]
        last_resp: str = data.get("last_responsible", "")  # type: ignore[assignment]
        last_pub: str = data.get("last_publication", "БДУ ФСТЕК")  # type: ignore[assignment]

        self._responsible_combo.addItems(persons)
        if last_resp:
            idx = self._responsible_combo.findText(last_resp)
            if idx >= 0:
                self._responsible_combo.setCurrentIndex(idx)
            else:
                self._responsible_combo.setCurrentText(last_resp)

        idx = self._publication_combo.findText(last_pub)
        if idx >= 0:
            self._publication_combo.setCurrentIndex(idx)

    def _save_responsible_data(self) -> None:
        """Persist current responsible/publication selection; add new names to the list."""
        responsible = self._responsible_combo.currentText().strip()
        publication = self._publication_combo.currentText()
        persons = [
            self._responsible_combo.itemText(i)
            for i in range(self._responsible_combo.count())
        ]
        if responsible and responsible not in persons:
            persons.append(responsible)
            self._responsible_combo.addItem(responsible)
        save_responsible_data(persons, responsible, publication)

    def _load_saved_settings(self) -> None:
        settings = load_settings()
        self._settings_panel.set_settings(settings)

    def _load_saved_mappings(self) -> None:
        mappings = load_ppts_mappings()
        if "local" in mappings:
            self._file_loader.set_ppts_local_mapping(mappings["local"])
        if "general" in mappings:
            self._file_loader.set_ppts_general_mapping(mappings["general"])

    def _save_mappings(self) -> None:
        mappings = {}
        if self._file_loader.ppts_local_mapping is not None:
            mappings["local"] = self._file_loader.ppts_local_mapping
        if self._file_loader.ppts_general_mapping is not None:
            mappings["general"] = self._file_loader.ppts_general_mapping
        if mappings:
            save_ppts_mappings(mappings)

    def _on_files_changed(self) -> None:
        self._btn_run.setEnabled(self._file_loader.is_ready())

    def _on_run(self) -> None:
        """Start the analysis pipeline."""
        if not self._file_loader.is_ready():
            QMessageBox.warning(self, "Ошибка", "Выберите файлы ТСУ и ППТС.")
            return

        settings = self._settings_panel.get_settings()
        save_settings(settings)

        # Load files
        self._progress_view.reset()
        self._results_view.clear()
        self._btn_run.setEnabled(False)
        self._btn_export.setEnabled(False)
        self._status_bar.showMessage("Загрузка файлов...")

        try:
            self._progress_view.log(f"Загрузка ТСУ: {self._file_loader.tsu_path}")
            vulnerabilities = read_tsu(self._file_loader.tsu_path)
            self._progress_view.log(f"Загружено {len(vulnerabilities)} уязвимостей")

            # Load PPTS files (local + general)
            software_list = []
            if self._file_loader.ppts_local_path:
                self._progress_view.log(f"Загрузка ППТС (лок.): {Path(self._file_loader.ppts_local_path).name}")
                local_sw = read_ppts(
                    self._file_loader.ppts_local_path,
                    source="local_ppts",
                    mapping=self._file_loader.ppts_local_mapping,
                )
                software_list.extend(local_sw)
                self._progress_view.log(f"  -> {len(local_sw)} записей")

            if self._file_loader.ppts_general_path:
                self._progress_view.log(f"Загрузка ППТС (общ.): {Path(self._file_loader.ppts_general_path).name}")
                general_sw = read_ppts(
                    self._file_loader.ppts_general_path,
                    source="general_ppts",
                    mapping=self._file_loader.ppts_general_mapping,
                )
                software_list.extend(general_sw)
                self._progress_view.log(f"  -> {len(general_sw)} записей")

            self._progress_view.log(f"Всего ПО: {len(software_list)} записей")

            # Load journal files
            journal_entries = []
            for jpath in self._file_loader.journal_paths:
                self._progress_view.log(f"Загрузка журнала: {Path(jpath).name}")
                entries = read_journal(jpath)
                journal_entries.extend(entries)
                self._progress_view.log(f"  -> {len(entries)} записей")
            if journal_entries:
                self._progress_view.log(
                    f"Всего из журналов: {len(journal_entries)} записей"
                )
        except ReaderError as exc:
            self._progress_view.set_error(str(exc))
            self._btn_run.setEnabled(True)
            self._status_bar.showMessage("Ошибка загрузки файлов")
            QMessageBox.critical(self, "Ошибка чтения", str(exc))
            return

        # Run pipeline in background thread
        self._thread = QThread()
        self._worker = _PipelineWorker(
            settings, vulnerabilities, software_list,
            journal_entries=journal_entries or None,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_pipeline_progress)
        self._worker.finished.connect(self._on_pipeline_finished)
        self._worker.error.connect(self._on_pipeline_error)

        self._status_bar.showMessage("Анализ запущен...")
        self._thread.start()

    @Slot(str, int, int)
    def _on_pipeline_progress(self, stage: str, current: int, total: int) -> None:
        self._progress_view.update_progress(stage, current, total)

    @Slot(list)
    def _on_pipeline_finished(self, results: list[AnalysisResult]) -> None:
        self._results = results
        self._results_view.set_results(results)
        self._progress_view.set_finished(len(results))
        self._btn_run.setEnabled(True)
        self._btn_export.setEnabled(bool(results))
        self._status_bar.showMessage(f"Анализ завершён: {len(results)} записей")
        self._cleanup_thread()

    @Slot(str)
    def _on_pipeline_error(self, error_text: str) -> None:
        self._progress_view.set_error(error_text)
        self._btn_run.setEnabled(True)
        self._status_bar.showMessage("Ошибка анализа")
        QMessageBox.critical(self, "Ошибка", f"Ошибка пайплайна:\n{error_text}")
        self._cleanup_thread()

    def _cleanup_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    def _on_export(self) -> None:
        """Export results to an XLSX file."""
        if not self._results:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчёт",
            "report.xlsx",
            "Excel (*.xlsx)",
        )
        if not path:
            return

        try:
            from matcher.io.report_writer import write_report

            settings = self._settings_panel.get_settings()
            results = self._results_view.get_results()
            responsible = self._responsible_combo.currentText().strip()
            publication = self._publication_combo.currentText()
            write_report(Path(path), results, settings, responsible=responsible, publication=publication)
            self._save_responsible_data()
            self._progress_view.log(f"Отчёт сохранён: {path}")
            self._status_bar.showMessage(f"Отчёт сохранён: {Path(path).name}")

            msg = QMessageBox(self)
            msg.setWindowTitle("Готово")
            msg.setText(f"Отчёт сохранён:\n{path}")
            msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            open_btn = msg.addButton("Открыть файл", QMessageBox.ButtonRole.ActionRole)
            msg.exec()
            if msg.clickedButton() is open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        except Exception as exc:
            logger.exception("Failed to write report")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчёт:\n{exc}")

    def closeEvent(self, event) -> None:
        """Save settings, mappings, responsible data, and clean up on close."""
        settings = self._settings_panel.get_settings()
        save_settings(settings)
        self._save_mappings()
        self._save_responsible_data()
        self._cleanup_thread()
        super().closeEvent(event)
