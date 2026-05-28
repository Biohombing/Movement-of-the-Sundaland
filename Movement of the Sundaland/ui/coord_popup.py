"""
ui/coord_popup.py — Coordinate popup when clicking on map.
Shows coordinates + Add Point button (name optional).
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont


class CoordPopup(QWidget):
    """
    Floating popup showing clicked coordinates.
    Name field is optional — can leave blank for auto-name.
    """
    add_point_requested = pyqtSignal(str, float, float)  # name, lat, lon

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(260)

        self._lat = 0.0
        self._lon = 0.0
        self._auto_counter = [0]

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        self._build_ui()

    def reset_counter(self):
        """FIX #11: Reset auto-counter agar Point-1 kembali muncul saat project baru."""
        self._auto_counter[0] = 0

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background-color:#FFFFFF;"
            " border:2px solid #4A7EC7; border-radius:8px; }"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(10, 8, 10, 8)
        fl.setSpacing(5)

        # Title
        title = QLabel("📍  Clicked Location")
        title.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        title.setStyleSheet("color:#3060A8; border:none;")
        fl.addWidget(title)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(
            "border:none; border-top:1px solid #d0d0d0;")
        fl.addWidget(div)

        # Coordinates
        self.lat_lbl = QLabel("Lat:  —")
        self.lon_lbl = QLabel("Lon:  —")
        self.dms_lbl = QLabel("")
        for lbl in (self.lat_lbl, self.lon_lbl, self.dms_lbl):
            lbl.setStyleSheet(
                "color:#222222; font-size:11px;"
                "font-family:'Consolas','Courier New',monospace; border:none;")
        fl.addWidget(self.lat_lbl)
        fl.addWidget(self.lon_lbl)
        fl.addWidget(self.dms_lbl)

        # Name input (optional)
        name_lbl = QLabel("Point name  (optional):")
        name_lbl.setStyleSheet(
            "color:#555555; font-size:10px; border:none;")
        fl.addWidget(name_lbl)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Leave blank for auto-name…")
        self.name_edit.setFixedHeight(26)
        self.name_edit.setStyleSheet(
            "border:1px solid #C0B8B8; border-radius:4px;"
            "padding:2px 6px; font-size:11px; background:#FAFAFA;")
        fl.addWidget(self.name_edit)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self.btn_add = QPushButton("➕ Add to Table")
        self.btn_add.setFixedHeight(28)
        self.btn_add.setStyleSheet(
            "QPushButton { background:#2e6b3e; color:#ffffff;"
            " border:1px solid #256830; border-radius:4px;"
            " font-size:10px; font-weight:bold; padding:2px 8px;}"
            "QPushButton:hover { background:#3a8a50; }")
        self.btn_add.setToolTip(
            "Add this location to observation points table")

        self.btn_close = QPushButton("✖")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setStyleSheet(
            "QPushButton { background:#f2f2f2; color:#666666;"
            " border:1px solid #C0B8B8; border-radius:4px;"
            " font-size:10px;}"
            "QPushButton:hover { background:#cc3333; color:#ffffff;}")

        btn_row.addWidget(self.btn_add)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_close)
        fl.addLayout(btn_row)

        outer.addWidget(frame)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_close.clicked.connect(self.hide)
        self.name_edit.returnPressed.connect(self._on_add)

    def show_at(self, lat: float, lon: float, global_pos: QPoint):
        self._lat = lat
        self._lon = lon
        self.name_edit.clear()

        ns = "N" if lat >= 0 else "S"
        ew = "E" if lon >= 0 else "W"
        self.lat_lbl.setText(f"Lat:  {abs(lat):.6f}°  {ns}")
        self.lon_lbl.setText(f"Lon:  {abs(lon):.6f}°  {ew}")
        self.dms_lbl.setText(
            f"      {self._dms(lat,'NS')}\n"
            f"      {self._dms(lon,'EW')}")

        self.adjustSize()
        x = global_pos.x() + 16
        y = global_pos.y() - 10

        from PyQt6.QtWidgets import QApplication
        scr = QApplication.primaryScreen().geometry()
        if x + self.width()  > scr.width():
            x = global_pos.x() - self.width() - 10
        if y + self.height() > scr.height():
            y = global_pos.y() - self.height() - 10

        self.move(x, y)
        self.show()
        self.raise_()
        self.name_edit.setFocus()

        self._timer.stop()
        self._timer.start(12000)   # auto-hide after 12 seconds

    def _dms(self, decimal: float, direction: str) -> str:
        pos  = abs(decimal)
        deg  = int(pos)
        mf   = (pos - deg) * 60
        mins = int(mf)
        secs = (mf - mins) * 60
        d    = ('N' if decimal >= 0 else 'S') if direction == 'NS' \
               else ('E' if decimal >= 0 else 'W')
        return f"{deg}° {mins}' {secs:.2f}\"  {d}"

    def _on_add(self):
        name = self.name_edit.text().strip()
        if not name:
            self._auto_counter[0] += 1
            name = f"Point-{self._auto_counter[0]}"
        self.hide()
        self._timer.stop()
        self.add_point_requested.emit(name, self._lat, self._lon)
