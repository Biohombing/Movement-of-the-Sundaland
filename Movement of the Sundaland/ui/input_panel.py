"""
ui/input_panel.py — Observation Points panel (no shapefile)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QLabel, QGroupBox,
    QHeaderView, QAbstractItemView, QFrame, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from models.data_models import ObservationPoint


class InputPanel(QWidget):
    add_point_requested      = pyqtSignal()
    search_location_requested = pyqtSignal(str)   # search query
    remove_point_requested   = pyqtSignal(int)
    load_csv_requested       = pyqtSignal()
    load_excel_requested     = pyqtSignal()
    load_defaults_requested  = pyqtSignal()
    gps_correction_requested = pyqtSignal()

    COL_NO   = 0
    COL_NAME = 1
    COL_LAT  = 2
    COL_LON  = 3
    COLUMNS  = ["#", "Location Name", "Latitude (°)", "Longitude (°)"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(6)

        # ── Search bar ────────────────────────────────────────
        search_grp = QGroupBox("🔍 Search Location")
        search_lay = QHBoxLayout(search_grp)
        search_lay.setSpacing(4)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("City, village, hamlet… (e.g. Desa Sukarami)")
        self.search_edit.setFixedHeight(28)
        self.btn_search = QPushButton("Search")
        self.btn_search.setFixedHeight(28)
        self.btn_search.setFixedWidth(60)
        search_lay.addWidget(self.search_edit)
        search_lay.addWidget(self.btn_search)

        hdr = QLabel("📌 Observation Points")
        hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hdr.setStyleSheet("color:#3060A8; padding:4px 2px 0;")
        root.addWidget(search_grp)
        root.addWidget(hdr)

        # Load group
        grp_load = QGroupBox("📂 Load Data")
        load_lay = QHBoxLayout(grp_load)
        load_lay.setSpacing(4)

        self.btn_csv   = QPushButton("📄 CSV")
        self.btn_excel = QPushButton("📊 Excel")
        self.btn_def   = QPushButton("🏙 Defaults")
        for btn in (self.btn_csv, self.btn_excel, self.btn_def):
            btn.setFixedHeight(30)
            load_lay.addWidget(btn)

        self.btn_csv.setToolTip("Load points from CSV file")
        self.btn_excel.setToolTip("Load points from Excel (.xlsx)")
        self.btn_def.setToolTip("Use 8 default cities")
        root.addWidget(grp_load)

        # Table
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_NAME, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_LAT, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(
            self.COL_LON, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(self.COL_NO, 32)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, 1)

        # Action buttons
        act_lay = QHBoxLayout()
        act_lay.setSpacing(4)

        self.btn_add = QPushButton("➕ Add Point")
        self.btn_add.setFixedHeight(32)
        self.btn_add.setToolTip("Add new point manually")
        self.btn_add.setStyleSheet(
            "background-color:#2e6b3e; color:#ffffff;"
            "border-color:#256830; font-weight:bold;")

        self.btn_remove = QPushButton("➖ Remove")
        self.btn_remove.setFixedHeight(32)
        self.btn_remove.setToolTip("Remove selected point")
        self.btn_remove.setStyleSheet(
            "background-color:#6b2e2e; color:#ffffff; border-color:#8a3a3a;")

        self.btn_clear_all = QPushButton("🗑 Clear All")
        self.btn_clear_all.setFixedHeight(32)

        act_lay.addWidget(self.btn_add)
        act_lay.addWidget(self.btn_remove)
        act_lay.addWidget(self.btn_clear_all)
        root.addLayout(act_lay)

        self.count_lbl = QLabel("0 observation points")
        self.count_lbl.setStyleSheet("color:#777777; font-size:10px; padding:2px;")
        root.addWidget(self.count_lbl)

        # Divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color:#C8C0C0;")
        root.addWidget(div)

        # GPS Correction button
        self.btn_gps = QPushButton("🛰️  GPS Satellite Correction")
        self.btn_gps.setFixedHeight(40)
        self.btn_gps.setToolTip(
            "Open GPS correction — compare Euler prediction with GPS data")
        self.btn_gps.setStyleSheet(
            "QPushButton { background-color:#1a5a8a; color:#ffffff;"
            " border:2px solid #2a7ab0; border-radius:6px;"
            " font-size:12px; font-weight:bold; padding:6px 12px; }"
            "QPushButton:hover { background-color:#2a7ab0; }"
            "QPushButton:pressed { background-color:#0f3a5a; }"
        )
        root.addWidget(self.btn_gps)

        gps_hint = QLabel("Compare Euler prediction with GPS satellite data")
        gps_hint.setStyleSheet("color:#999999; font-size:9px; padding:2px;")
        gps_hint.setWordWrap(True)
        root.addWidget(gps_hint)

        # Connections
        self.btn_add.clicked.connect(self.add_point_requested)
        self.btn_remove.clicked.connect(self._on_remove)
        self.btn_clear_all.clicked.connect(self._on_clear_all)
        self.btn_csv.clicked.connect(self.load_csv_requested)
        self.btn_excel.clicked.connect(self.load_excel_requested)
        self.btn_def.clicked.connect(self.load_defaults_requested)
        self.btn_gps.clicked.connect(self.gps_correction_requested)
        self.btn_search.clicked.connect(self._on_search)
        self.search_edit.returnPressed.connect(self._on_search)

    def _on_search(self):
        q = self.search_edit.text().strip()
        if q:
            self.search_location_requested.emit(q)

    def set_points(self, points):
        self.table.setRowCount(0)
        for pt in points:
            self._append_row(pt)
        n = len(points)
        self.count_lbl.setText(
            f"{n} observation point{'s' if n != 1 else ''}")

    def add_row(self, point):
        self._append_row(point)
        n = self.table.rowCount()
        self.count_lbl.setText(
            f"{n} observation point{'s' if n != 1 else ''}")

    def selected_row(self):
        rows = self.table.selectedItems()
        return self.table.row(rows[0]) if rows else -1

    def _append_row(self, point):
        row = self.table.rowCount()
        self.table.insertRow(row)
        items = [
            QTableWidgetItem(str(row + 1)),
            QTableWidgetItem(point.name),
            QTableWidgetItem(f"{point.lat:.6f}"),
            QTableWidgetItem(f"{point.lon:.6f}"),
        ]
        for col, item in enumerate(items):
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter if col != self.COL_NAME
                else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.table.setItem(row, col, item)

    def _on_remove(self):
        row = self.selected_row()
        if row >= 0:
            self.remove_point_requested.emit(row)

    def _on_clear_all(self):
        # FIX #4: Snapshot jumlah baris sebelum iterasi agar aman saat
        # remove_point_requested menyebabkan _refresh_input_table() mengubah rowCount.
        count = self.table.rowCount()
        for row in range(count - 1, -1, -1):
            self.remove_point_requested.emit(row)
