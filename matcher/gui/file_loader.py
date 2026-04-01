"""File loader widgets for TSU, PPTS (x2), and Journal files."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from shared.types import PptsColumnMapping

logger = logging.getLogger(__name__)

_FILE_FILTER = "Excel/CSV (*.xlsx *.xls *.csv);;All Files (*)"
_EXCEL_FILTER = "Excel (*.xlsx *.xls);;All Files (*)"


class FileSelector(QWidget):
    """A single file selector: label + path display + browse button."""

    file_selected = Signal(str)

    def __init__(self, label_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = ""
        self._setup_ui(label_text)

    def _setup_ui(self, label_text: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text)
        label.setFixedWidth(120)
        layout.addWidget(label)

        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("Файл не выбран...")
        layout.addWidget(self._path_edit, 1)

        btn = QPushButton("Обзор...")
        btn.setObjectName("btn_secondary")
        btn.setMinimumWidth(80)
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл", "", _FILE_FILTER,
        )
        if path:
            self.set_path(path)

    def set_path(self, path: str) -> None:
        """Set the file path programmatically."""
        self._path = path
        self._path_edit.setText(Path(path).name if path else "")
        self._path_edit.setToolTip(path)
        self.file_selected.emit(path)

    def get_path(self) -> str:
        return self._path

    def is_set(self) -> bool:
        return bool(self._path and Path(self._path).exists())


class PptsSelector(QWidget):
    """PPTS file selector with column configuration button."""

    file_selected = Signal(str)
    mapping_changed = Signal()

    def __init__(self, label_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = ""
        self._mapping: PptsColumnMapping | None = None
        self._setup_ui(label_text)

    def _setup_ui(self, label_text: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text)
        label.setFixedWidth(120)
        layout.addWidget(label)

        self._path_edit = QLineEdit()
        self._path_edit.setReadOnly(True)
        self._path_edit.setPlaceholderText("Файл не выбран...")
        layout.addWidget(self._path_edit, 1)

        btn_browse = QPushButton("Обзор...")
        btn_browse.setObjectName("btn_secondary")
        btn_browse.setMinimumWidth(70)
        btn_browse.clicked.connect(self._browse)
        layout.addWidget(btn_browse)

        self._btn_columns = QPushButton("Столбцы...")
        self._btn_columns.setObjectName("btn_secondary")
        self._btn_columns.setMinimumWidth(70)
        self._btn_columns.setEnabled(False)
        self._btn_columns.setToolTip("Настроить столбцы ID / Наименование / Вендор")
        self._btn_columns.clicked.connect(self._configure_columns)
        layout.addWidget(self._btn_columns)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл ППТС", "", _FILE_FILTER,
        )
        if path:
            self._set_path(path)

    def _set_path(self, path: str) -> None:
        self._path = path
        self._path_edit.setText(Path(path).name if path else "")
        self._path_edit.setToolTip(path)
        self._btn_columns.setEnabled(bool(path))
        self._mapping = None
        self.file_selected.emit(path)

    def _configure_columns(self) -> None:
        if not self._path:
            return
        from matcher.gui.column_config import ColumnConfigDialog

        dialog = ColumnConfigDialog(
            self._path, current_mapping=self._mapping, parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._mapping = dialog.get_mapping()
            self.mapping_changed.emit()
            logger.info(
                "Column mapping set for %s: id=%s name=%s vendor=%s",
                Path(self._path).name,
                self._mapping.col_id if self._mapping else None,
                self._mapping.col_name if self._mapping else None,
                self._mapping.col_vendor if self._mapping else None,
            )

    def get_path(self) -> str:
        return self._path

    def get_mapping(self) -> PptsColumnMapping | None:
        return self._mapping

    def set_mapping(self, mapping: PptsColumnMapping | None) -> None:
        """Restore a saved mapping."""
        self._mapping = mapping

    def set_path(self, path: str) -> None:
        """Restore file path programmatically (e.g., from saved config)."""
        if path and Path(path).exists():
            self._set_path(path)

    def is_set(self) -> bool:
        return bool(self._path and Path(self._path).exists())


_ROLE_PINNED = Qt.ItemDataRole.UserRole + 1
_ROLE_PATH = Qt.ItemDataRole.UserRole + 2


class JournalSelector(QWidget):
    """Widget for selecting multiple journal files."""

    files_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._paths: list[str] = []
        self._pinned: set[str] = set()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Журналы проверок:"))
        header_row.addStretch()

        btn_add = QPushButton("Добавить")
        btn_add.setObjectName("btn_secondary")
        btn_add.setMinimumWidth(80)
        btn_add.clicked.connect(self._add_files)
        header_row.addWidget(btn_add)

        btn_clear = QPushButton("Очистить")
        btn_clear.setObjectName("btn_secondary")
        btn_clear.setMinimumWidth(80)
        btn_clear.clicked.connect(self._clear)
        header_row.addWidget(btn_clear)

        layout.addLayout(header_row)

        self._list = QListWidget()
        self._list.setMaximumHeight(60)
        self._list.itemDoubleClicked.connect(self._toggle_pin)
        layout.addWidget(self._list)

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Выбрать журналы проверок", "", _EXCEL_FILTER,
        )
        for path in paths:
            if path not in self._paths:
                self._paths.append(path)
                item = QListWidgetItem(Path(path).name)
                item.setData(_ROLE_PATH, path)
                item.setData(_ROLE_PINNED, False)
                self._list.addItem(item)
        if paths:
            self.files_changed.emit()

    def _toggle_pin(self, item: QListWidgetItem) -> None:
        """Toggle pinned state on double-click."""
        path = item.data(_ROLE_PATH)
        if not path:
            return
        is_pinned = item.data(_ROLE_PINNED)
        if is_pinned:
            self._pinned.discard(path)
            item.setData(_ROLE_PINNED, False)
            item.setText(Path(path).name)
        else:
            self._pinned.add(path)
            item.setData(_ROLE_PINNED, True)
            item.setText(f"\U0001f4cc {Path(path).name}")

    def _clear(self) -> None:
        """Remove only unpinned items; pinned items stay."""
        rows_to_remove: list[int] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and not item.data(_ROLE_PINNED):
                path = item.data(_ROLE_PATH)
                if path in self._paths:
                    self._paths.remove(path)
                rows_to_remove.append(i)
        for row in reversed(rows_to_remove):
            self._list.takeItem(row)
        self.files_changed.emit()

    def get_paths(self) -> list[str]:
        return list(self._paths)

    def get_pinned_paths(self) -> list[str]:
        """Return list of pinned file paths."""
        return [p for p in self._paths if p in self._pinned]

    def set_pinned_paths(self, paths: list[str]) -> None:
        """Restore pinned journals from saved config."""
        for path in paths:
            if path and Path(path).exists() and path not in self._paths:
                self._paths.append(path)
                self._pinned.add(path)
                item = QListWidgetItem(f"\U0001f4cc {Path(path).name}")
                item.setData(_ROLE_PATH, path)
                item.setData(_ROLE_PINNED, True)
                self._list.addItem(item)
        if paths:
            self.files_changed.emit()


class FileLoaderPanel(QWidget):
    """Panel with TSU, PPTS (local + general), and Journal file selectors."""

    files_changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._tsu_selector = FileSelector("ТСУ:")
        self._tsu_selector.file_selected.connect(lambda _: self.files_changed.emit())
        layout.addWidget(self._tsu_selector)

        self._ppts_local = PptsSelector("ППТС (лок.):")
        self._ppts_local.file_selected.connect(lambda _: self.files_changed.emit())
        layout.addWidget(self._ppts_local)

        self._ppts_general = PptsSelector("ППТС (общ.):")
        self._ppts_general.file_selected.connect(lambda _: self.files_changed.emit())
        layout.addWidget(self._ppts_general)

        self._journal_selector = JournalSelector()
        self._journal_selector.files_changed.connect(self.files_changed.emit)
        layout.addWidget(self._journal_selector)

    @property
    def tsu_path(self) -> str:
        return self._tsu_selector.get_path()

    @property
    def ppts_local_path(self) -> str:
        return self._ppts_local.get_path()

    @property
    def ppts_general_path(self) -> str:
        return self._ppts_general.get_path()

    @property
    def ppts_local_mapping(self) -> PptsColumnMapping | None:
        return self._ppts_local.get_mapping()

    @property
    def ppts_general_mapping(self) -> PptsColumnMapping | None:
        return self._ppts_general.get_mapping()

    @property
    def journal_paths(self) -> list[str]:
        return self._journal_selector.get_paths()

    def set_ppts_local_mapping(self, mapping: PptsColumnMapping | None) -> None:
        self._ppts_local.set_mapping(mapping)

    def set_ppts_general_mapping(self, mapping: PptsColumnMapping | None) -> None:
        self._ppts_general.set_mapping(mapping)

    def set_ppts_local_path(self, path: str) -> None:
        """Restore the local PPTS file path from saved config."""
        self._ppts_local.set_path(path)

    def set_ppts_general_path(self, path: str) -> None:
        """Restore the general PPTS file path from saved config."""
        self._ppts_general.set_path(path)

    def set_pinned_journals(self, paths: list[str]) -> None:
        """Restore pinned journal paths from saved config."""
        self._journal_selector.set_pinned_paths(paths)

    def get_pinned_journals(self) -> list[str]:
        """Return list of pinned journal file paths."""
        return self._journal_selector.get_pinned_paths()

    def is_ready(self) -> bool:
        """Return True if TSU and at least one PPTS file are selected."""
        return self._tsu_selector.is_set() and (
            self._ppts_local.is_set() or self._ppts_general.is_set()
        )
