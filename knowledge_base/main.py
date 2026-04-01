"""Entry point for the Knowledge Base application."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from knowledge_base.config import load_config
from knowledge_base.gui.main_window import MainWindow
from shared.themes import ThemeManager

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Launch the Knowledge Base GUI application."""
    _setup_logging()
    logger.info("Starting Knowledge Base v2.0")

    app = QApplication(sys.argv)

    theme_mgr = ThemeManager("knowledge_base")
    config = load_config()
    theme_name = config.get("theme", "Светлая")
    app.setStyleSheet(theme_mgr.get_stylesheet(theme_name))
    logger.info("Applied theme: %s", theme_name)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
