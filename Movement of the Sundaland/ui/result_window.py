"""
ui/result_window.py — GeoPlate Analyst v2.4
Result Table with clickable 🧭 Rose column per row.
Each click opens an independent resizable Rose Diagram window for that point.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import Normalize

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QHeaderView, QAbstractItemView, QSizePolicy,
    QApplication
)
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap


# ── Rose window (one per point, reusable) ─────────────────────────────────────

class RoseWindow(QMainWindow):
    """
    Standalone resizable window showing the rose diagram for ONE point.
    Has full OS min/max/close title bar buttons.
    """
    def __init__(self, result, parent=None):
        super().__init__(None)          # No parent → independent window
        self.setWindowTitle(f"Rose Diagram — {result.name}")
        self.setWindowFlags(Qt.WindowType.Window)
        self.resize(480, 480)
        self.setMinimumSize(320, 320)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header
        _icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "compass_rose.png"
        )
        hdr = QLabel(f"  Rose Diagram  —  {result.name}")
        hdr.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hdr.setStyleSheet("color:#3060A8;")
        icon_lbl = QLabel()
        if os.path.exists(_icon_path):
            pix = QPixmap(_icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(icon_lbl)
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        info = QLabel(
            f"V Total: {result.vT:.2f} mm/yr  |  "
            f"Azimuth: {result.azimuth:.1f}°  |  "
            f"Direction: {result.compass}"
        )
        info.setStyleSheet("color:#555555; font-size:10px;")
        layout.addWidget(info)

        # Plot
        fig = Figure(figsize=(3, 3), dpi=80, facecolor='#f2f2f2')
        canvas = FigureCanvas(fig)
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(canvas, 1)

        self._draw(fig, result)
        canvas.draw()

    def _draw(self, fig, r):
        ax = fig.add_subplot(111, projection='polar', facecolor='#f2f2f2')
        ax.set_theta_direction(-1)
        ax.set_theta_zero_location('N')

        theta = np.radians(r.azimuth)
        rho   = 0.75

        # Arrow
        ax.annotate("", xy=(theta, rho), xytext=(0, 0),
                    arrowprops=dict(arrowstyle='->', color='#3060A8',
                                    lw=2.5, mutation_scale=18))

        # Speed label — fontsize minimal 7
        ax.text(theta, rho + 0.15,
                f"{r.vT:.2f}\nmm/yr",
                ha='center', va='center',
                fontsize=7, color='#3060A8', fontweight='bold')

        # Compass labels — fontsize minimal 7
        for az_deg, label in [(0,'N'),(90,'E'),(180,'S'),(270,'W')]:
            ax.text(np.radians(az_deg), 1.18, label,
                    ha='center', va='center',
                    fontsize=7, color='#333333', fontweight='bold')

        ax.set_ylim(0, 1.3)
        ax.set_yticklabels([])
        ax.tick_params(colors='#888888', labelsize=7)
        ax.grid(color='#d0d0d0', lw=0.5, linestyle='--')

        # Title — fontsize minimal 8
        ax.set_title(
            f"{r.name}\nAzimuth: {r.azimuth:.1f}°  ({r.compass})",
            color='#3060A8', fontsize=8, fontweight='bold', pad=14
        )
        fig.patch.set_facecolor('#f2f2f2')

    def closeEvent(self, event):
        event.ignore()
        self.hide()


# ── Main result window ─────────────────────────────────────────────────────────

class ResultWindow(QMainWindow):
    """
    Main results window with table.
    Last column = 🧭 button → opens individual RoseWindow for that row.
    """
    export_excel_requested = pyqtSignal()
    export_csv_requested   = pyqtSignal()

    # Column indices
    COL_NO    = 0
    COL_LOC   = 1
    COL_LAT   = 2
    COL_LON   = 3
    COL_VN    = 4
    COL_VE    = 5
    COL_VT    = 6
    COL_AZ    = 7
    COL_DIR   = 8
    COL_ROSE  = 9

    HEADERS = [
        "#", "Location", "Lat", "Lon",
        "vN (mm/yr)", "vE (mm/yr)", "V Total\n(mm/yr)",
        "Az (°)", "Direction", "Rose"
    ]

    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowTitle("GeoPlate Analyst — Results")
        self.setWindowFlags(Qt.WindowType.Window)
        self.resize(950, 480)
        self.setMinimumSize(600, 300)

        self._results     = []
        self._rose_wins   = {}   # name → RoseWindow (reuse per point)

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Header bar
        hdr_bar = QWidget()
        hdr_bar.setStyleSheet("background-color:#f2f2f2; border-radius:4px;")
        hdr_lay = QHBoxLayout(hdr_bar)
        hdr_lay.setContentsMargins(8, 4, 8, 4)
        hdr_lay.setSpacing(6)

        title = QLabel("📊  Calculation Results")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color:#3060A8; border:none;")
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self.btn_xlsx = QPushButton("💾 Export Excel")
        self.btn_csv  = QPushButton("📄 Export CSV")
        self.btn_xlsx.setFixedHeight(26)
        self.btn_csv.setFixedHeight(26)

        _btn_style = (
            "QPushButton { background-color:#1a5a8a; color:#ffffff;"
            " border:1px solid #2a7ab0; border-radius:4px;"
            " font-size:11px; font-weight:bold; padding:2px 10px; }"
            "QPushButton:hover { background-color:#2a7ab0; }"
            "QPushButton:pressed { background-color:#0f3a5a; }"
        )
        self.btn_xlsx.setStyleSheet(_btn_style)
        self.btn_csv.setStyleSheet(_btn_style)

        # ← Dua baris ini WAJIB ada, tombol tidak tampil tanpa ini
        hdr_lay.addWidget(self.btn_xlsx)
        hdr_lay.addWidget(self.btn_csv)
        root.addWidget(hdr_bar)

        # Status
        self._status_lbl = QLabel("No results yet — run the calculation first.")
        self._status_lbl.setStyleSheet("color:#777777; font-size:10px;")
        root.addWidget(self._status_lbl)

        # Table
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)

        # Column widths
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(self.COL_NO,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_LOC,  QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(self.COL_LAT,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_LON,  QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_VN,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_VE,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_VT,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_AZ,   QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(self.COL_DIR,  QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(self.COL_ROSE, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(self.COL_LOC,  110)
        self.table.setColumnWidth(self.COL_ROSE,  80)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setWordWrap(False)
        root.addWidget(self.table, 1)

        # Hint label
        hint = QLabel("💡  Click 🧭 in the last column to view the rose diagram for each point.")
        hint.setStyleSheet("color:#999999; font-size:9px;")
        root.addWidget(hint)

        # Signals
        self.btn_xlsx.clicked.connect(self.export_excel_requested)
        self.btn_csv.clicked.connect(self.export_csv_requested)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_results(self, results):
        self._results = results
        # FIX #7: Tutup semua RoseWindow lama sebelum clear dict agar tidak memory leak
        self._close_all_rose_wins()
        self._populate_table(results)
        if results:
            vmin = min(r.vT for r in results)
            vmax = max(r.vT for r in results)
            n    = len(results)
            self._status_lbl.setText(
                f"{n} point{'s' if n != 1 else ''}  |  "
                f"Velocity range: {vmin:.2f} – {vmax:.2f} mm/yr  |  "
                f"Click 🧭 to view individual rose diagrams"
            )

    def clear(self):
        self.table.setRowCount(0)
        self._results = []
        # FIX #7: Tutup window dulu agar Qt melepas resource, baru hapus dari dict
        self._close_all_rose_wins()
        self._status_lbl.setText("No results yet — run the calculation first.")

    def _close_all_rose_wins(self):
        """Tutup semua RoseWindow secara eksplisit untuk mencegah memory leak."""
        for win in list(self._rose_wins.values()):
            # Override closeEvent sementara agar window benar-benar bisa ditutup
            win.closeEvent = lambda e: e.accept()
            win.close()
        self._rose_wins.clear()

    def closeEvent(self, event):
        # Close all open rose windows too
        for w in self._rose_wins.values():
            w.hide()
        event.ignore()
        self.hide()

    # ── Table population ───────────────────────────────────────────────────────

    def _populate_table(self, results):
        self.table.setRowCount(0)
        self.table.setRowCount(len(results))

        for i, r in enumerate(results):
            def _item(text, align=Qt.AlignmentFlag.AlignCenter):
                it = QTableWidgetItem(str(text))
                it.setTextAlignment(align)
                return it

            left = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft

            self.table.setItem(i, self.COL_NO,  _item(str(i + 1)))
            self.table.setItem(i, self.COL_LOC, _item(r.name, left))
            self.table.setItem(i, self.COL_LAT, _item(f"{r.lat:.4f}"))
            self.table.setItem(i, self.COL_LON, _item(f"{r.lon:.4f}"))
            self.table.setItem(i, self.COL_VN,  _item(f"{r.vN:+.2f}"))
            self.table.setItem(i, self.COL_VE,  _item(f"{r.vE:+.2f}"))
            self.table.setItem(i, self.COL_VT,  _item(f"{r.vT:.2f}"))
            self.table.setItem(i, self.COL_AZ,  _item(f"{r.azimuth:.1f}°"))
            self.table.setItem(i, self.COL_DIR, _item(r.compass, left))

            # Rose button
            btn = QPushButton()
            btn.setFixedHeight(26)
            #btn.setFixedWidth(26)

            # Load ikon kompas
            _icon_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "assets", "compass_rose.png"
            )
            if os.path.exists(_icon_path):
                btn.setIcon(QIcon(_icon_path))
                btn.setIconSize(QSize(16, 16))
            else:
                btn.setText("🧭")   # fallback jika gambar tidak ditemukan

            btn.setToolTip(f"Show rose diagram for {r.name}")
            # Capture r in closure
            btn.clicked.connect(lambda checked, result=r: self._open_rose(result))

            cell_widget = QWidget()
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(2, 1, 2, 1)
            cell_layout.addWidget(btn)
            self.table.setCellWidget(i, self.COL_ROSE, cell_widget)

            self.table.setRowHeight(i, 26)

    def _open_rose(self, result):
        """Open (or bring to front) the rose diagram window for this result."""
        name = result.name
        if name not in self._rose_wins:
            self._rose_wins[name] = RoseWindow(result)
        win = self._rose_wins[name]
        win.show()
        win.raise_()
        win.activateWindow()