"""
ui/theme_manager.py
Manages Light / Dark theme switching.
"""

import os
from PyQt6.QtWidgets import QApplication


THEMES = {
    'light': 'style_light.qss',
    'dark':  'style_dark.qss',
}

_current_theme = 'light'


def get_current() -> str:
    return _current_theme


def apply(theme: str, app: QApplication = None):
    """Apply theme by name ('light' or 'dark')."""
    global _current_theme
    if theme not in THEMES:
        return

    _current_theme = theme
    qss_file = THEMES[theme]

    # Find QSS file relative to this file
    ui_dir  = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(ui_dir, qss_file)

    if not os.path.exists(qss_path):
        return

    with open(qss_path, 'r', encoding='utf-8') as f:
        qss = f.read()

    target = app or QApplication.instance()
    if target:
        target.setStyleSheet(qss)


def toggle(app: QApplication = None) -> str:
    """Toggle between light and dark. Returns new theme name."""
    new = 'dark' if _current_theme == 'light' else 'light'
    apply(new, app)
    return new
