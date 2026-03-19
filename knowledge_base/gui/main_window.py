"""Main window for the Knowledge Base application."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from knowledge_base.config import load_config, save_config
from knowledge_base.gui.rule_editor import RuleEditorDialog
from knowledge_base.gui.rule_tester import RuleTesterDialog
from knowledge_base.gui.rules_table import RulesTable
from shared.db.models import init_db
from shared.db.repository import create_rule, delete_rule, get_rule_by_id, update_rule

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main window for the Knowledge Base manager."""

    def __init__(self) -> None:
        super().__init__()
        self._conn: sqlite3.Connection | None = None
        self._db_path: str = ""
        self._setup_ui()
        self._connect_signals()
        self._try_load_last_db()

    def _setup_ui(self) -> None:
        self.setWindowTitle("База Знаний v2.0")
        self.setMinimumSize(900, 600)

        config = load_config()
        self.resize(config.get("window_width", 1100), config.get("window_height", 700))

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

        title = QLabel("База Знаний")
        title.setObjectName("title_label")
        header_layout.addWidget(title)

        subtitle = QLabel("Управление правилами сопоставления")
        subtitle.setObjectName("subtitle_label")
        header_layout.addWidget(subtitle)

        main_layout.addWidget(header)

        # --- DB selector ---
        db_row = QHBoxLayout()
        db_row.setSpacing(8)
        db_row.addWidget(QLabel("База данных:"))

        self._db_label = QLabel("Не выбрана")
        self._db_label.setStyleSheet("color: #7a7a9a;")
        db_row.addWidget(self._db_label, 1)

        btn_open = QPushButton("Открыть")
        btn_open.setObjectName("btn_secondary")
        btn_open.setFixedWidth(90)
        btn_open.clicked.connect(self._on_open_db)
        db_row.addWidget(btn_open)

        btn_new = QPushButton("Создать")
        btn_new.setObjectName("btn_secondary")
        btn_new.setFixedWidth(90)
        btn_new.clicked.connect(self._on_new_db)
        db_row.addWidget(btn_new)

        main_layout.addLayout(db_row)

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_add = QPushButton("Добавить правило")
        self._btn_add.setEnabled(False)
        btn_row.addWidget(self._btn_add)

        self._btn_edit = QPushButton("Редактировать")
        self._btn_edit.setObjectName("btn_secondary")
        self._btn_edit.setEnabled(False)
        btn_row.addWidget(self._btn_edit)

        self._btn_test = QPushButton("Тестировать")
        self._btn_test.setObjectName("btn_secondary")
        self._btn_test.setEnabled(False)
        btn_row.addWidget(self._btn_test)

        self._btn_delete = QPushButton("Удалить")
        self._btn_delete.setObjectName("btn_danger")
        self._btn_delete.setEnabled(False)
        btn_row.addWidget(self._btn_delete)

        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        # --- Rules table ---
        rules_group = QGroupBox("Правила")
        rules_layout = QVBoxLayout(rules_group)
        self._rules_table = RulesTable()
        rules_layout.addWidget(self._rules_table)
        main_layout.addWidget(rules_group, 1)

        # --- Status bar ---
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Выберите или создайте базу данных")

    def _connect_signals(self) -> None:
        self._btn_add.clicked.connect(self._on_add_rule)
        self._btn_edit.clicked.connect(self._on_edit_rule)
        self._btn_test.clicked.connect(self._on_test_rule)
        self._btn_delete.clicked.connect(self._on_delete_rule)
        self._rules_table.rule_selected.connect(self._on_rule_selected)
        self._rules_table.rule_double_clicked.connect(self._on_edit_rule_by_id)

    def _try_load_last_db(self) -> None:
        """Try to reopen the last used database."""
        config = load_config()
        last_path = config.get("last_db_path", "")
        if last_path and Path(last_path).exists():
            self._open_db(last_path)

    def _open_db(self, path: str) -> None:
        """Open a SQLite database file."""
        if self._conn is not None:
            self._conn.close()

        try:
            self._conn = init_db(path)
            self._db_path = path
            self._db_label.setText(Path(path).name)
            self._db_label.setToolTip(path)
            self._db_label.setStyleSheet("color: #2e2e4e; font-weight: 500;")
            self._rules_table.set_connection(self._conn)
            self._btn_add.setEnabled(True)
            self._status_bar.showMessage(f"Открыта: {Path(path).name}")

            config = load_config()
            config["last_db_path"] = path
            save_config(config)

            logger.info("Opened database: %s", path)
        except Exception as exc:
            logger.exception("Failed to open database")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть базу:\n{exc}")

    @Slot()
    def _on_open_db(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть базу знаний",
            "",
            "SQLite (*.db *.sqlite);;All Files (*)",
        )
        if path:
            self._open_db(path)

    @Slot()
    def _on_new_db(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Создать базу знаний",
            "knowledge.db",
            "SQLite (*.db);;All Files (*)",
        )
        if path:
            self._open_db(path)

    @Slot(int)
    def _on_rule_selected(self, rule_id: int) -> None:
        has_selection = True
        self._btn_edit.setEnabled(has_selection)
        self._btn_test.setEnabled(has_selection)
        self._btn_delete.setEnabled(has_selection)

    @Slot()
    def _on_add_rule(self) -> None:
        if self._conn is None:
            logger.warning("Cannot add rule: no database connection")
            return

        dialog = RuleEditorDialog(parent=self)
        dialog.setModal(True)
        dialog.raise_()
        dialog.activateWindow()
        result = dialog.exec()
        logger.info("Add rule dialog result: %s", result)
        if result == QDialog.DialogCode.Accepted:
            rule = dialog.get_rule()
            if rule is not None:
                rule_id = create_rule(self._conn, rule)
                self._rules_table.refresh()
                self._status_bar.showMessage(f"Правило #{rule_id} создано")

    @Slot()
    def _on_edit_rule(self) -> None:
        rule_id = self._rules_table.selected_rule_id()
        if rule_id is not None:
            self._on_edit_rule_by_id(rule_id)

    @Slot(int)
    def _on_edit_rule_by_id(self, rule_id: int) -> None:
        if self._conn is None:
            return

        rule = get_rule_by_id(self._conn, rule_id)
        if rule is None:
            QMessageBox.warning(self, "Ошибка", f"Правило #{rule_id} не найдено.")
            return

        dialog = RuleEditorDialog(rule=rule, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_rule = dialog.get_rule()
            if updated_rule is not None:
                update_rule(self._conn, updated_rule)
                self._rules_table.refresh()
                self._status_bar.showMessage(f"Правило #{rule_id} обновлено")

    @Slot()
    def _on_test_rule(self) -> None:
        if self._conn is None:
            return

        rule_id = self._rules_table.selected_rule_id()
        if rule_id is None:
            return

        rule = get_rule_by_id(self._conn, rule_id)
        if rule is None:
            return

        dialog = RuleTesterDialog(rule=rule, parent=self)
        dialog.exec()

    @Slot()
    def _on_delete_rule(self) -> None:
        if self._conn is None:
            return

        rule_id = self._rules_table.selected_rule_id()
        if rule_id is None:
            return

        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить правило #{rule_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_rule(self._conn, rule_id)
            self._rules_table.refresh()
            self._btn_edit.setEnabled(False)
            self._btn_test.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._status_bar.showMessage(f"Правило #{rule_id} удалено")

    def closeEvent(self, event) -> None:
        """Save config and close DB."""
        config = load_config()
        config["window_width"] = self.width()
        config["window_height"] = self.height()
        save_config(config)

        if self._conn is not None:
            self._conn.close()
        super().closeEvent(event)
