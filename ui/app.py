"""PySide6 application bootstrap."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.logging_config import setup_logging


BASE_DIR = Path(__file__).resolve().parent.parent
FONT_CANDIDATES = [
    BASE_DIR / "assets" / "fonts" / "Vazirmatn-Regular.ttf",
    BASE_DIR / "assets" / "fonts" / "Vazirmatn[wght].ttf",
]


def _configure_ui_font(app: QApplication) -> None:
    """Load Vazirmatn font if available, then apply app-wide fallback chain."""
    loaded_family: str | None = None
    for font_path in FONT_CANDIDATES:
        if not font_path.exists():
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id == -1:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            loaded_family = families[0]
            break

    preferred_family = loaded_family or "Vazirmatn"
    app.setFont(QFont(preferred_family, 11))


def run() -> int:
    """Initialize logging and run the Qt application."""
    logger = setup_logging()
    logger.info("Starting DocuMind Scan application")

    app = QApplication(sys.argv)
    app.setApplicationName("DocuMind Scan")
    _configure_ui_font(app)

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    logger.info("Application exited with code %s", exit_code)
    return exit_code
