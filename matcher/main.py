"""Entry point for the Matcher application."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Import sentence_transformers before PySide6 to avoid shiboken MemoryError
# when inspecting large transformers module source at runtime.
import sentence_transformers  # noqa: F401

from PySide6.QtWidgets import QApplication

from matcher.gui.main_window import MainWindow

logger = logging.getLogger(__name__)

_STYLES_PATH = Path(__file__).parent / "gui" / "styles" / "theme.qss"


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

    # Load QSS theme
    if _STYLES_PATH.exists():
        stylesheet = _STYLES_PATH.read_text(encoding="utf-8")
        app.setStyleSheet(stylesheet)
        logger.info("Loaded theme from %s", _STYLES_PATH)
    else:
        logger.warning("Theme file not found: %s", _STYLES_PATH)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
