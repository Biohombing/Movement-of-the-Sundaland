"""
main.py
Entry point for Sundaland Motion Pro.

Run with:
    python main.py          <- mode development
    SundalandMotionPro.exe  <- mode distribusi (hasil PyInstaller build)

Requirements:
    pip install PyQt6 cartopy geopandas contextily pandas openpyxl matplotlib numpy
"""

import sys
import os

# CRITICAL: set DPI env BEFORE importing Qt
# Ensures Qt and Matplotlib use consistent pixel units on HiDPI (125/150/200%)
os.environ.setdefault('QT_ENABLE_HIGHDPI_SCALING', '1')

if getattr(sys, 'frozen', False):
    ROOT    = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    ROOT    = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow
from core.constants import APP_NAME, APP_VERSION


def load_stylesheet(app: QApplication, theme: str = 'light'):
    from ui.theme_manager import apply as apply_theme
    apply_theme(theme, app)


def main():
    # PassThrough: allow fractional DPI (1.5x etc) without rounding
    # devicePixelRatioF() in GeoCoordTransformer handles the scaling correctly
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("GeodynamicsLab")

    # Set explicit font to avoid QFont::setPointSize warnings at HiDPI
    font = QFont()
    font.setFamily("Segoe UI")
    font.setPointSize(10)
    app.setFont(font)
    
    # Suppress verbose Qt warnings (cosmetic only, not errors)
    import os
    os.environ.setdefault('QT_LOGGING_RULES', '*.debug=false;qt.qpa.fonts=false')

    load_stylesheet(app)

    win = MainWindow()
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
