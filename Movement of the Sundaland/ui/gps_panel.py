"""
ui/gps_panel.py — GPS Correction Panel
Load GPS data (CSV/Excel) OR input manually like Add Point.
"""

import os          # FIX: pindah ke top-level dari dalam method
import pandas as pd  # FIX: pindah ke top-level dari dalam method
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QHeaderView, QAbstractItemView, QFileDialog,
    QGroupBox, QSizePolicy, QMessageBox, QSplitter,
    QTextEdit, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.comparator import compare, summary_stats
from services.gps_service import GPSPoint, create_gps_template, \
    load_gps_csv, load_gps_excel


# ── Manual GPS input dialog ────────────────────────────────────────────────────

class AddGPSPointDialog(QDialog):
    """Dialog to manually input a GPS observation point with vN and vE."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add GPS Point")
        self.setMinimumWidth(360)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 12)

        title = QLabel("🛰️  Add GPS Observation Point")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color:#3060A8; margin-bottom:4px;")
        layout.addWidget(title)

        grp  = QGroupBox("Coordinates & Velocity")
        form = QFormLayout(grp)
        form.setSpacing(8)

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Bengkulu, BKLN …")
        form.addRow("Station Name:", self.name_edit)

        # Latitude
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(6)
        self.lat_spin.setSingleStep(0.01)
        self.lat_spin.setValue(0.0)
        self.lat_spin.setSuffix("  °")
        self.lat_spin.setToolTip("Negative = South, Positive = North")
        form.addRow("Latitude:", self.lat_spin)

        # Longitude
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(6)
        self.lon_spin.setSingleStep(0.01)
        self.lon_spin.setValue(0.0)
        self.lon_spin.setSuffix("  °")
        self.lon_spin.setToolTip("Negative = West, Positive = East")
        form.addRow("Longitude:", self.lon_spin)

        # vN
        self.vn_spin = QDoubleSpinBox()
        self.vn_spin.setRange(-999.0, 999.0)
        self.vn_spin.setDecimals(4)
        self.vn_spin.setSingleStep(0.1)
        self.vn_spin.setValue(0.0)
        self.vn_spin.setSuffix("  mm/yr")
        self.vn_spin.setToolTip("GPS North velocity component (mm/yr)")
        form.addRow("vN (North):", self.vn_spin)

        # vE
        self.ve_spin = QDoubleSpinBox()
        self.ve_spin.setRange(-999.0, 999.0)
        self.ve_spin.setDecimals(4)
        self.ve_spin.setSingleStep(0.1)
        self.ve_spin.setValue(0.0)
        self.ve_spin.setSuffix("  mm/yr")
        self.ve_spin.setToolTip("GPS East velocity component (mm/yr)")
        form.addRow("vE (East):", self.ve_spin)

        layout.addWidget(grp)

        hint = QLabel(
            "ℹ  WGS84 coordinates. vN and vE in mm/yr from GPS solution.")
        hint.setStyleSheet("color:#888888; font-size:9px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("✔  Add")
        btn_box.button(
            QDialogButtonBox.StandardButton.Cancel).setText("✖  Cancel")
        btn_box.accepted.connect(self._validate)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Name Required",
                                "Station name cannot be empty.")
            self.name_edit.setFocus()
            return
        self.accept()

    def get_point(self) -> GPSPoint:
        return GPSPoint(
            name=self.name_edit.text().strip(),
            lat=self.lat_spin.value(),
            lon=self.lon_spin.value(),
            vN=self.vn_spin.value(),
            vE=self.ve_spin.value(),
        )


# ── GPS Panel main window ──────────────────────────────────────────────────────

class GPSPanel(QMainWindow):
    gps_overlay_ready = pyqtSignal(list)
    gps_overlay_clear = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowTitle("GeoPlate Analyst — GPS Satellite Correction")
        self.setWindowFlags(Qt.WindowType.Window)
        self.resize(1100, 620)
        self.setMinimumSize(700, 400)

        self._gps_points:    list = []
        self._euler_results: list = []
        self._comparisons:   list = []

        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Title
        hdr = QWidget()
        hdr.setStyleSheet("background-color:#f2f2f2; border-radius:4px;")
        hdrl = QHBoxLayout(hdr)
        hdrl.setContentsMargins(8, 4, 8, 4)
        title = QLabel("🛰️  GPS Satellite Correction — Residual Analysis")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color:#3060A8; border:none;")
        hdrl.addWidget(title)
        hdrl.addStretch()
        root.addWidget(hdr)

        # ── GPS data control bar ───────────────────────────────
        ctrl = QGroupBox("GPS Data Input")
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setSpacing(6)

        self.btn_add_manual = QPushButton("➕ Add GPS Point")
        self.btn_add_manual.setFixedHeight(30)
        self.btn_add_manual.setToolTip("Manually input GPS point with vN and vE")
        self.btn_add_manual.setStyleSheet(
            "background-color:#2e6b3e; color:#ffffff;"
            "border-color:#256830; font-weight:bold;")

        self.btn_remove_gps = QPushButton("➖ Remove Selected")
        self.btn_remove_gps.setFixedHeight(30)
        self.btn_remove_gps.setStyleSheet(
            "background-color:#6b2e2e; color:#ffffff; border-color:#8a3a3a;")

        self.btn_load_csv   = QPushButton("📄 Load CSV")
        self.btn_load_excel = QPushButton("📊 Load Excel")
        self.btn_template   = QPushButton("📋 Template")
        self.btn_run        = QPushButton("▶ Run Comparison")
        self.btn_run.setObjectName("btn_run")
        self.btn_clear      = QPushButton("🗑 Clear GPS")
        self.btn_export     = QPushButton("💾 Export Results")

        for b in (self.btn_load_csv, self.btn_load_excel, self.btn_template,
                  self.btn_run, self.btn_clear, self.btn_export):
            b.setFixedHeight(30)

        self.btn_run.setEnabled(False)
        self.btn_export.setEnabled(False)

        for b in (self.btn_add_manual, self.btn_remove_gps,
                  self.btn_load_csv, self.btn_load_excel,
                  self.btn_template, self.btn_run,
                  self.btn_clear, self.btn_export):
            ctrl_lay.addWidget(b)
        ctrl_lay.addStretch()

        self._gps_status = QLabel("No GPS data loaded.")
        self._gps_status.setStyleSheet("color:#555555; font-size:10px;")
        ctrl_lay.addWidget(self._gps_status)
        root.addWidget(ctrl)

        # ── GPS point table (top) + Comparison table (bottom) ──
        v_split = QSplitter(Qt.Orientation.Vertical)

        # GPS input table
        gps_wrap = QWidget()
        gps_lay  = QVBoxLayout(gps_wrap)
        gps_lay.setContentsMargins(0, 0, 0, 0)
        gps_hdr = QLabel("📍  GPS Input Points")
        gps_hdr.setStyleSheet(
            "color:#3060A8; font-weight:bold; font-size:11px;")
        gps_lay.addWidget(gps_hdr)

        self.gps_table = QTableWidget(0, 6)
        self.gps_table.setHorizontalHeaderLabels(
            ["#", "Station", "Lat (°)", "Lon (°)", "vN (mm/yr)", "vE (mm/yr)"])
        gh = self.gps_table.horizontalHeader()
        gh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in (0, 2, 3, 4, 5):
            gh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.gps_table.verticalHeader().setVisible(False)
        self.gps_table.setAlternatingRowColors(True)
        self.gps_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.gps_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        gps_lay.addWidget(self.gps_table)
        v_split.addWidget(gps_wrap)

        # Comparison result table + stats
        cmp_outer = QWidget()
        cmp_lay   = QVBoxLayout(cmp_outer)
        cmp_lay.setContentsMargins(0, 0, 0, 0)

        h_split = QSplitter(Qt.Orientation.Horizontal)

        tbl_wrap = QWidget()
        tbl_lay  = QVBoxLayout(tbl_wrap)
        tbl_lay.setContentsMargins(0, 0, 0, 0)
        tbl_hdr = QLabel("📊  Comparison Table  (GPS − Euler Residuals)")
        tbl_hdr.setStyleSheet(
            "color:#3060A8; font-weight:bold; font-size:11px;")
        tbl_lay.addWidget(tbl_hdr)

        self.cmp_table = QTableWidget(0, 13)
        self.cmp_table.setHorizontalHeaderLabels([
            "#", "Location",
            "Euler vN", "Euler vE", "Euler vT",
            "GPS vN",   "GPS vE",   "GPS vT",
            "Res vN",   "Res vE",   "Res vT",
            "Agreement", "Match"
        ])
        ch = self.cmp_table.horizontalHeader()
        ch.setSectionResizeMode(1,  QHeaderView.ResizeMode.Interactive)
        ch.setSectionResizeMode(11, QHeaderView.ResizeMode.ResizeToContents)
        ch.setSectionResizeMode(12, QHeaderView.ResizeMode.ResizeToContents)
        for c in range(13):
            if c not in (1, 11, 12):
                ch.setSectionResizeMode(
                    c, QHeaderView.ResizeMode.ResizeToContents)
        self.cmp_table.setColumnWidth(1, 100)
        self.cmp_table.verticalHeader().setVisible(False)
        self.cmp_table.setAlternatingRowColors(True)
        self.cmp_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.cmp_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        tbl_lay.addWidget(self.cmp_table, 1)
        h_split.addWidget(tbl_wrap)

        # Stats panel
        stats_wrap = QWidget()
        stats_wrap.setFixedWidth(230)
        stats_lay = QVBoxLayout(stats_wrap)
        stats_lay.setContentsMargins(4, 0, 0, 0)
        stats_hdr = QLabel("📈  Statistics")
        stats_hdr.setStyleSheet(
            "color:#3060A8; font-weight:bold; font-size:11px;")
        stats_lay.addWidget(stats_hdr)

        self.stats_box = QTextEdit()
        self.stats_box.setReadOnly(True)
        self.stats_box.setStyleSheet(
            "background:#f8f8f8; border:1px solid #d0d0d0;"
            "font-family:'Consolas','Courier New',monospace; font-size:10px;")
        self.stats_box.setPlaceholderText(
            "Statistics will appear here\nafter running comparison.")
        stats_lay.addWidget(self.stats_box, 1)

        legend = QLabel(
            "<b>Legend</b><br>"
            "🟦 Euler (predicted)<br>"
            "🟥 GPS (measured)<br>"
            "🟨 Residual (GPS−Euler)<br><br>"
            "<b>Match quality:</b><br>"
            "Excellent  ≥ 90%<br>"
            "Good       ≥ 75%<br>"
            "Moderate   ≥ 50%<br>"
            "Poor       &lt; 50%"
        )
        legend.setStyleSheet(
            "background:#F0EBEB; border:1px solid #d0d0d0; border-radius:4px;"
            "padding:6px; font-size:10px; color:#333333;")
        legend.setWordWrap(True)
        stats_lay.addWidget(legend)
        h_split.addWidget(stats_wrap)
        h_split.setStretchFactor(0, 3)

        cmp_lay.addWidget(h_split, 1)
        v_split.addWidget(cmp_outer)
        v_split.setStretchFactor(0, 1)
        v_split.setStretchFactor(1, 2)
        root.addWidget(v_split, 1)

        hint = QLabel(
            "ℹ  Add GPS points manually (➕) or load from CSV/Excel file. "
            "CSV/Excel must have columns: name, lat, lon, vN, vE")
        hint.setStyleSheet("color:#999999; font-size:9px;")
        root.addWidget(hint)

        # Connections
        self.btn_add_manual.clicked.connect(self._on_add_manual)
        self.btn_remove_gps.clicked.connect(self._on_remove_gps)
        self.btn_load_csv.clicked.connect(self._on_load_csv)
        self.btn_load_excel.clicked.connect(self._on_load_excel)
        self.btn_template.clicked.connect(self._on_download_template)
        self.btn_run.clicked.connect(self._on_run)
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_export.clicked.connect(self._on_export)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_euler_results(self, results: list):
        self._euler_results = results
        self._update_run_button()

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_add_manual(self):
        dlg = AddGPSPointDialog(parent=self)
        if dlg.exec():
            pt = dlg.get_point()
            self._gps_points.append(pt)
            self._append_gps_row(pt)
            self._update_gps_status()
            self._update_run_button()

    def _on_remove_gps(self):
        rows = self.gps_table.selectedItems()
        if not rows:
            return
        row = self.gps_table.row(rows[0])
        if 0 <= row < len(self._gps_points):
            self._gps_points.pop(row)
            self.gps_table.removeRow(row)
            # Renumber
            for r in range(self.gps_table.rowCount()):
                self.gps_table.item(r, 0).setText(str(r + 1))
            self._update_gps_status()
            self._update_run_button()

    def _on_load_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load GPS CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path:
            self._load_gps_file(path, 'csv')

    def _on_load_excel(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load GPS Excel", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)")
        if path:
            self._load_gps_file(path, 'excel')

    def _load_gps_file(self, path: str, fmt: str):
        # FIX: import os sudah di top-level, tidak perlu di sini lagi
        try:
            if fmt == 'csv':
                pts, warns = load_gps_csv(path)
            else:
                pts, warns = load_gps_excel(path)
            for pt in pts:
                self._gps_points.append(pt)
                self._append_gps_row(pt)
            self._update_gps_status()
            self._update_run_button()
            if warns:
                QMessageBox.warning(self, "Load Warnings",
                    f"{len(pts)} points loaded.\nSkipped:\n" +
                    "\n".join(warns))
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))

    def _on_download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save GPS Template", "gps_template.xlsx",
            "Excel Files (*.xlsx);;All Files (*)")
        if path:
            try:
                create_gps_template(path)
                QMessageBox.information(
                    self, "Template Saved", f"Template saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _on_run(self):
        if not self._euler_results:
            QMessageBox.warning(self, "No Euler Results",
                "Please run the Euler calculation first."); return
        if not self._gps_points:
            QMessageBox.warning(self, "No GPS Data",
                "Please add GPS points first."); return
        try:
            comps, warns = compare(self._euler_results, self._gps_points)
            self._comparisons = comps
            self._populate_cmp_table(comps)
            self._populate_stats(comps)
            self.btn_export.setEnabled(bool(comps))
            self.gps_overlay_ready.emit(comps)
            if warns:
                QMessageBox.warning(self, "Unmatched Points",
                    "Some points had no GPS match:\n" + "\n".join(warns))
        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", str(e))

    def _on_clear(self):
        self._gps_points  = []
        self._comparisons = []
        self.gps_table.setRowCount(0)
        self.cmp_table.setRowCount(0)
        self.stats_box.clear()
        self._gps_status.setText("No GPS data loaded.")
        self.btn_run.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.gps_overlay_clear.emit()

    def _on_export(self):
        if not self._comparisons:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Comparison", "gps_comparison.xlsx",
            "Excel Files (*.xlsx);;All Files (*)")
        if path:
            try:
                self._export_excel(path)
                QMessageBox.information(
                    self, "Exported", f"Results saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    # ── Table helpers ──────────────────────────────────────────────────────────

    def _append_gps_row(self, pt: GPSPoint):
        row = self.gps_table.rowCount()
        self.gps_table.insertRow(row)
        cells = [str(row+1), pt.name,
                 f"{pt.lat:.6f}", f"{pt.lon:.6f}",
                 f"{pt.vN:.4f}", f"{pt.vE:.4f}"]
        for col, val in enumerate(cells):
            item = QTableWidgetItem(val)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter if col != 1
                else Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.gps_table.setItem(row, col, item)
        self.gps_table.setRowHeight(row, 24)

    def _populate_cmp_table(self, comps):
        self.cmp_table.setRowCount(0)
        self.cmp_table.setRowCount(len(comps))
        BLUE   = QColor(200, 220, 255, 120)
        RED    = QColor(255, 200, 200, 120)
        YELLOW = QColor(255, 240, 180, 120)
        GREEN  = QColor(200, 240, 200, 120)
        ORANGE = QColor(255, 220, 160, 120)

        def _it(text, bg=None, align=Qt.AlignmentFlag.AlignCenter):
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(align)
            if bg:
                item.setBackground(bg)
            return item

        left = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        for i, c in enumerate(comps):
            mbg = GREEN if c.agreement_pct >= 75 else \
                  ORANGE if c.agreement_pct >= 50 else RED
            self.cmp_table.setItem(i,  0, _it(str(i+1)))
            self.cmp_table.setItem(i,  1, _it(c.name, align=left))
            self.cmp_table.setItem(i,  2, _it(f"{c.euler_vN:+.3f}", BLUE))
            self.cmp_table.setItem(i,  3, _it(f"{c.euler_vE:+.3f}", BLUE))
            self.cmp_table.setItem(i,  4, _it(f"{c.euler_vT:.3f}",  BLUE))
            self.cmp_table.setItem(i,  5, _it(f"{c.gps_vN:+.3f}",  RED))
            self.cmp_table.setItem(i,  6, _it(f"{c.gps_vE:+.3f}",  RED))
            self.cmp_table.setItem(i,  7, _it(f"{c.gps_vT:.3f}",   RED))
            self.cmp_table.setItem(i,  8, _it(f"{c.res_vN:+.3f}",  YELLOW))
            self.cmp_table.setItem(i,  9, _it(f"{c.res_vE:+.3f}",  YELLOW))
            self.cmp_table.setItem(i, 10, _it(f"{c.res_vT:.3f}",   YELLOW))
            self.cmp_table.setItem(i, 11, _it(f"{c.agreement_pct:.1f}%", mbg))
            self.cmp_table.setItem(i, 12, _it(c.match_label, mbg))
            self.cmp_table.setRowHeight(i, 24)

    def _populate_stats(self, comps):
        stats = summary_stats(comps)
        if not stats:
            return
        lines = [
            "══ Residual Statistics ══",
            f"  Points compared : {stats['n']}",
            f"  Mean |res| vT   : {stats['mean_res_vT']:.3f} mm/yr",
            f"  Std  |res| vT   : {stats['std_res_vT']:.3f} mm/yr",
            f"  Max  |res| vT   : {stats['max_res_vT']:.3f} mm/yr",
            f"  Min  |res| vT   : {stats['min_res_vT']:.3f} mm/yr",
            "",
            "══ Agreement ════════════",
            f"  Mean agreement  : {stats['mean_agree']:.1f}%",
            "",
            "══ Match quality ════════",
        ]
        counts = {"Excellent": 0, "Good": 0, "Moderate": 0, "Poor": 0}
        for c in comps:
            counts[c.match_label] += 1
        for k, v in counts.items():
            lines.append(f"  {k:<12}: {v}")
        self.stats_box.setPlainText("\n".join(lines))

    def _update_gps_status(self):
        n = len(self._gps_points)
        self._gps_status.setText(
            f"✅ {n} GPS point{'s' if n != 1 else ''} loaded")

    def _update_run_button(self):
        self.btn_run.setEnabled(
            bool(self._gps_points) and bool(self._euler_results))

    def _export_excel(self, path: str):
        # FIX: import pandas sudah di top-level, tidak perlu di sini lagi
        records = []
        for c in self._comparisons:
            records.append({
                "Location"        : c.name,
                "Lat"             : c.lat,
                "Lon"             : c.lon,
                "Euler vN (mm/yr)": c.euler_vN,
                "Euler vE (mm/yr)": c.euler_vE,
                "Euler vT (mm/yr)": c.euler_vT,
                "GPS vN (mm/yr)"  : c.gps_vN,
                "GPS vE (mm/yr)"  : c.gps_vE,
                "GPS vT (mm/yr)"  : c.gps_vT,
                "Residual vN"     : c.res_vN,
                "Residual vE"     : c.res_vE,
                "Residual vT"     : c.res_vT,
                "Res Azimuth (°)" : c.res_az,
                "Res Direction"   : c.res_compass,
                "Agreement (%)"   : round(c.agreement_pct, 2),
                "Match Quality"   : c.match_label,
            })
        df = pd.DataFrame(records)
        with pd.ExcelWriter(path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='GPS Comparison', index=False)
            ws = writer.sheets['GPS Comparison']
            for col in ws.columns:
                w = max(len(str(c.value or '')) for c in col) + 2
                ws.column_dimensions[col[0].column_letter].width = min(w, 30)
