"""
ui/search_result_dialog.py
Search result dialog — shows Nominatim results with place type info.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QDialogButtonBox, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


# Place type icons
_TYPE_ICON = {
    'village'       : '🏘️',
    'hamlet'        : '🏚️',
    'suburb'        : '🏙️',
    'neighbourhood' : '🏘️',
    'town'          : '🏙️',
    'city'          : '🌆',
    'administrative': '🗺️',
    'county'        : '🗺️',
    'state'         : '🗺️',
    'country'       : '🌍',
    'island'        : '🏝️',
    'peak'          : '⛰️',
    'river'         : '🌊',
    'bay'           : '🌊',
    'beach'         : '🏖️',
    'forest'        : '🌲',
    'university'    : '🎓',
    'school'        : '🏫',
    'hospital'      : '🏥',
    'mosque'        : '🕌',
    'church'        : '⛪',
}

def _place_icon(place_type: str) -> str:
    return _TYPE_ICON.get(place_type.lower(), '📍')


class SearchResultDialog(QDialog):
    def __init__(self, query: str, results: list, source: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Search Results — \"{query}\"")
        self.setMinimumWidth(520)
        self.setMinimumHeight(340)
        self.setModal(True)
        self._results = results
        self._build_ui(query, results, source)

    def _build_ui(self, query, results, source):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 14, 14, 12)

        # Header
        icon   = '💾' if source == 'offline' else '🌐'
        src_txt = 'Local database' if source == 'offline' \
                  else 'Online — Nominatim / OpenStreetMap'
        hdr = QLabel(
            f"{icon}  Search: <b>\"{query}\"</b>  —  {src_txt}"
        )
        hdr.setStyleSheet("color:#3060A8; font-size:11px;")
        layout.addWidget(hdr)

        if source == 'online':
            note = QLabel(
                "ℹ  Results from OpenStreetMap — includes villages, "
                "hamlets, streets and landmarks."
            )
            note.setStyleSheet("color:#777777; font-size:10px;")
            note.setWordWrap(True)
            layout.addWidget(note)

        hint = QLabel("Select a location then click ➕ Add Point:")
        hint.setStyleSheet("color:#555555; font-size:10px;")
        layout.addWidget(hint)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color:#C8C0C0;")
        layout.addWidget(div)

        # Results list
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setSpacing(2)
        font = QFont("Segoe UI", 10)
        self.list_widget.setFont(font)
        self.list_widget.setStyleSheet(
            "QListWidget {"
            "  background-color: #ffffff;"
            "  color: #1a1a1a;"
            "  border: 1px solid #C8C0C0;"
            "  border-radius: 4px;"
            "}"
            "QListWidget::item {"
            "  padding: 6px 8px;"
            "  color: #1a1a1a;"
            "}"
            "QListWidget::item:alternate {"
            "  background-color: #f5f2f2;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #2979C7;"
            "  color: #ffffff;"
            "}"
            "QListWidget::item:hover:!selected {"
            "  background-color: #e8f0fb;"
            "}"
        )

        for name, lat, lon, country in results:
            ns  = 'N' if lat >= 0 else 'S'
            ew  = 'E' if lon >= 0 else 'W'
            # Determine icon from name keywords
            icon_char = '📍'
            name_lower = name.lower()
            for key, ico in _TYPE_ICON.items():
                if key in name_lower:
                    icon_char = ico
                    break

            text = (
                f"{icon_char}  {name}\n"
                f"     🌐 {country}   |   "
                f"Lat: {abs(lat):.6f}°{ns}   "
                f"Lon: {abs(lon):.6f}°{ew}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, (name, lat, lon))
            self.list_widget.addItem(item)

        if results:
            self.list_widget.setCurrentRow(0)

        self.list_widget.doubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget, 1)

        # Count label
        count_lbl = QLabel(f"  {len(results)} location(s) found")
        count_lbl.setStyleSheet("color:#888888; font-size:10px;")
        layout.addWidget(count_lbl)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            "➕  Add Point")
        btn_box.button(
            QDialogButtonBox.StandardButton.Cancel).setText("✖  Cancel")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_selected(self):
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
