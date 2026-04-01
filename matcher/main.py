"""Entry point for the Matcher application."""

from __future__ import annotations

import logging
import sys

# Import sentence_transformers before PySide6 to avoid shiboken MemoryError
# when inspecting large transformers module source at runtime.
import sentence_transformers  # noqa: F401

from shared.themes import ThemeManager

from PySide6.QtWidgets import QApplication

from matcher.gui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    """Launch the Matcher GUI application."""
    _setup_logging()
    logger.info("Starting Matcher v2.0")

    app = QApplication(sys.argv)

    # Load theme via ThemeManager
    from matcher.config import load_settings

    settings = load_settings()
    theme_mgr = ThemeManager("matcher")
    theme_name = getattr(settings, "theme", "Светлая")
    app.setStyleSheet(theme_mgr.get_stylesheet(theme_name))
    logger.info("Loaded theme: %s", theme_name)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
