"""
ui/result_panel.py  — English labels, grey theme
"""

import numpy as np
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import Normalize, LinearSegmentedColormap

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from models.data_models import PlateVelocity

VEL_CMAP = LinearSegmentedColormap.from_list(
    'geoplate_vel',
    ['#00ccff', '#00ff88', '#ffee00', '#ff6600', '#ff0044']
)


class ResultTable(QWidget):
    export_excel_requested = pyqtSignal()
    export_csv_requested   = pyqtSignal()

    COLUMNS = [
        "#", "Location", "Lat (°)", "Lon (°)",
        "vN (mm/yr)", "vE (mm/yr)", "V Total (mm/yr)",
        "Azimuth (°)", "Direction"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        bar = QHBoxLayout()
        lbl = QLabel("📊 Calculation Results")
        lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl.setStyleSheet("color:#7ab0e0;")
        bar.addWidget(lbl)
        bar.addStretch()

        self.btn_xlsx = QPushButton("💾 Export Excel")
        self.btn_csv  = QPushButton("📄 Export CSV")
        for btn in (self.btn_xlsx, self.btn_csv):
            btn.setFixedHeight(28)
            bar.addWidget(btn)
        layout.addLayout(bar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        self.btn_xlsx.clicked.connect(self.export_excel_requested)
        self.btn_csv.clicked.connect(self.export_csv_requested)

    def set_results(self, results):
        self.table.setRowCount(0)
        speeds = [r.vT for r in results]
        vmax   = max(speeds) if speeds else 1.0
        vmin   = min(speeds) if speeds else 0.0
        norm   = Normalize(vmin=vmin, vmax=vmax)

        for i, r in enumerate(results):
            row = self.table.rowCount()
            self.table.insertRow(row)
            color = VEL_CMAP(norm(r.vT))
            rgb   = tuple(int(255 * c) for c in color[:3])
            qcol  = QColor(*rgb, 100)
            cells = [
                str(i + 1), r.name,
                f"{r.lat:.4f}", f"{r.lon:.4f}",
                f"{r.vN:+.2f}", f"{r.vE:+.2f}",
                f"{r.vT:.2f}", f"{r.azimuth:.1f}°", r.compass,
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter if col != 1
                    else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
                if col == 6:
                    item.setBackground(qcol)
                    item.setForeground(QColor(*rgb))
                self.table.setItem(row, col, item)

    def clear(self):
        self.table.setRowCount(0)


class RoseDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig    = Figure(figsize=(5, 5), facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.fig)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._draw_empty()

    def plot_results(self, results):
        self.fig.clear()
        if not results:
            self._draw_empty(); return

        ax = self.fig.add_subplot(111, projection='polar', facecolor='#222222')
        ax.set_theta_direction(-1)
        ax.set_theta_zero_location('N')

        speeds = [r.vT for r in results]
        vmax   = max(speeds) if speeds else 1.0
        norm   = Normalize(vmin=0, vmax=vmax)
        rose_r = 0.35 + 0.6 * np.array(speeds) / vmax
        azimuths = np.radians([r.azimuth for r in results])

        for theta, rho, r in zip(azimuths, rose_r, results):
            col = VEL_CMAP(norm(r.vT))
            ax.annotate("", xy=(theta, rho), xytext=(0, 0),
                        arrowprops=dict(arrowstyle='->', color=col, lw=2.0, mutation_scale=12))
            ax.text(theta, rho + 0.08, r.name[:3],
                    ha='center', va='center', fontsize=7.5,
                    color=col, fontweight='bold')

        ax.set_ylim(0, 1.2)
        ax.set_yticklabels([])
        ax.tick_params(colors='#aaaaaa', labelsize=8)
        ax.grid(color='#444444', lw=0.7, linestyle='--')
        ax.set_title("Plate Motion Direction\n(Rose Diagram)",
                     color='#7ab0e0', fontsize=9, fontweight='bold', pad=14)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.canvas.draw()

    def _draw_empty(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111, facecolor='#2b2b2b')
        ax.set_axis_off()
        ax.text(0.5, 0.5, "No data available\nfor rose diagram",
                ha='center', va='center', color='#555555',
                fontsize=10, transform=ax.transAxes)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.canvas.draw()


class ResultPanel(QWidget):
    export_excel_requested = pyqtSignal()
    export_csv_requested   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.result_table = ResultTable()
        self.rose_diagram = RoseDiagram()

        self.tabs.addTab(self.result_table, "📋 Result Table")
        self.tabs.addTab(self.rose_diagram,  "🧭 Rose Diagram")
        layout.addWidget(self.tabs)

        self.result_table.export_excel_requested.connect(self.export_excel_requested)
        self.result_table.export_csv_requested.connect(self.export_csv_requested)

    def set_results(self, results):
        self.result_table.set_results(results)
        self.rose_diagram.plot_results(results)

    def clear(self):
        self.result_table.clear()
        self.rose_diagram._draw_empty()
