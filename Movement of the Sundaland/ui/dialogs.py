"""
ui/dialogs.py  — English labels, grey theme
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QPushButton,
    QDialogButtonBox, QMessageBox, QGroupBox,
    QComboBox, QFrame, QTabWidget, QWidget, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from models.data_models import ObservationPoint


class AddPointDialog(QDialog):
    def __init__(self, lat=0.0, lon=0.0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Observation Point")
        self.setMinimumWidth(360)
        self.setModal(True)
        self._build_ui(lat, lon)

    def _build_ui(self, lat, lon):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 12)

        title = QLabel("📍 Add New Observation Point")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color:#7ab0e0; margin-bottom:4px;")
        layout.addWidget(title)

        grp  = QGroupBox("Coordinates")
        form = QFormLayout(grp)
        form.setSpacing(8)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Bengkulu, GPS Station-01 …")
        self.name_edit.setMinimumWidth(220)
        form.addRow("Point Name:", self.name_edit)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0); self.lat_spin.setDecimals(6)
        self.lat_spin.setSingleStep(0.01); self.lat_spin.setValue(lat); self.lat_spin.setSuffix("  °")
        self.lat_spin.setToolTip("Latitude: negative = South, positive = North")
        form.addRow("Latitude:", self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0); self.lon_spin.setDecimals(6)
        self.lon_spin.setSingleStep(0.01); self.lon_spin.setValue(lon); self.lon_spin.setSuffix("  °")
        self.lon_spin.setToolTip("Longitude: negative = West, positive = East")
        form.addRow("Longitude:", self.lon_spin)
        layout.addWidget(grp)

        hint = QLabel("ℹ  WGS84 decimal coordinates. Example: Bengkulu → Lat -3.80, Lon 102.27")
        hint.setStyleSheet("color:#666666; font-size:9px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("✔  Add Point")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("✖  Cancel")
        btn_box.accepted.connect(self._validate_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _validate_and_accept(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Point name cannot be empty.")
            self.name_edit.setFocus(); return
        pt = ObservationPoint(name=name, lat=self.lat_spin.value(), lon=self.lon_spin.value())
        ok, msg = pt.validate()
        if not ok:
            QMessageBox.warning(self, "Invalid Coordinates", msg); return
        self.accept()

    def get_point(self):
        return ObservationPoint(
            name=self.name_edit.text().strip(),
            lat=self.lat_spin.value(), lon=self.lon_spin.value()
        )


class EulerPoleDialog(QDialog):
    """
    Euler Pole configuration dialog — three tabs:
      1. Preset   : official ITRF2020-PMM plates (EURA default)
      2. Sundaland: two regional estimates (Simons 2007, Alif 2024) + warnings
      3. Manual   : user-defined lat / lon / omega input
    """

    def __init__(self, ep_params: dict = None, parent=None):
        super().__init__(parent)
        self._ep_params  = ep_params or {}
        self._result     = None          # filled on accept
        self.setWindowTitle("Euler Pole Configuration")
        self.setMinimumWidth(560)
        self.setMinimumHeight(520)
        self.setModal(True)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        from core.constants import ITRF2020_PMM, ADDITIONAL_PLATES, wxyz_to_pole

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 12)

        # Title
        title = QLabel("⚙️  Euler Pole Configuration")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title.setStyleSheet("color:#3060A8;")
        root.addWidget(title)

        # Tabs
        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)

        self._build_tab_preset(ITRF2020_PMM)
        self._build_tab_sundaland(ADDITIONAL_PLATES, wxyz_to_pole)
        self._build_tab_manual()

        # ORB info strip
        orb_lbl = QLabel(
            "Origin Rate Bias (ORB) applied automatically — "
            "Tx=+0.37  Ty=+0.35  Tz=+0.74 mm/yr  (Altamimi 2023, Table 2)"
        )
        orb_lbl.setStyleSheet("color:#666666; font-size:9px; padding:2px 0;")
        root.addWidget(orb_lbl)

        # Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.button(QDialogButtonBox.StandardButton.Ok).setText("✔  Apply")
        btn_box.button(QDialogButtonBox.StandardButton.Cancel).setText("✖  Cancel")
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        root.addWidget(btn_box)

        # Restore active tab from current ep_params
        self._restore_active_tab()

    # ── Tab 1: Preset ITRF2020 ────────────────────────────────────────────────

    def _build_tab_preset(self, ITRF2020_PMM):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 8)

        info = QLabel(
            "Select one of the 13 official plates from the "
            "ITRF2020 Plate Motion Model (Altamimi et al. 2023, Table 1). "
            "<b>EURA (Eurasian)</b> is recommended as the default for the "
            "Sundaland region, as Sundaland is not officially included in "
            "ITRF2020-PMM."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#444444; font-size:10px;")
        lay.addWidget(info)

        # Plate selector
        row = QHBoxLayout()
        row.addWidget(QLabel("Tectonic plate:"))
        self._preset_combo = QComboBox()
        for code, d in ITRF2020_PMM.items():
            ns = d.get('ns', '?')
            self._preset_combo.addItem(
                f"{code} — {d['name']}  [{ns} stations]", code
            )
        row.addWidget(self._preset_combo, 1)
        lay.addLayout(row)

        # Parameter display
        pgrp = QGroupBox("Rotation Parameters")
        play = QFormLayout(pgrp)
        play.setSpacing(5)
        self._p_wx = QLabel(); self._p_wy = QLabel(); self._p_wz = QLabel()
        self._p_lat = QLabel(); self._p_lon = QLabel(); self._p_omega = QLabel()
        mono = "font-family:'Consolas','Courier New',monospace; font-size:11px;"
        for lbl in (self._p_wx, self._p_wy, self._p_wz,
                    self._p_lat, self._p_lon, self._p_omega):
            lbl.setStyleSheet(mono)
        play.addRow("wx (mas/yr):",      self._p_wx)
        play.addRow("wy (mas/yr):",      self._p_wy)
        play.addRow("wz (mas/yr):",      self._p_wz)
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        play.addRow(div)
        play.addRow("→ Lat (°N):",       self._p_lat)
        play.addRow("→ Lon (0-360°/EW):",self._p_lon)
        play.addRow("→ ω (°/Ma):",       self._p_omega)
        lay.addWidget(pgrp)
        lay.addStretch()

        self._preset_combo.currentIndexChanged.connect(self._update_preset_display)
        self._update_preset_display()
        self._tabs.addTab(tab, "🌍  ITRF2020 Official")

    # ── Tab 2: Sundaland estimates ────────────────────────────────────────────

    def _build_tab_sundaland(self, ADDITIONAL_PLATES, wxyz_to_pole):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 8)

        # ── Scientific warning box ────────────────────────────────────────────
        warn_box = QGroupBox("⚠  Scientific Limitations — Please Read")
        warn_box.setStyleSheet(
            "QGroupBox { border:2px solid #e65c00; border-radius:5px; "
            "margin-top:14px; padding:8px; background:#fff8f0; }"
            "QGroupBox::title { color:#e65c00; font-weight:bold; "
            "subcontrol-origin:margin; padding:0 6px; }"
        )
        wlay = QVBoxLayout(warn_box)
        warn_txt = QLabel(
            "<b>The Sundaland block has NO official Euler Pole in the "
            "ITRF2020-PMM (Altamimi et al. 2023).</b><br><br>"
            "All GPS stations in the Sundaland region were excluded from "
            "ITRF2020-PMM because they fail the strict site-selection criteria:<br>"
            "  &bull; Located &lt;100 km from the Sunda Trench plate boundary<br>"
            "  &bull; Significant interseismic coupling from Indo-Australian subduction<br>"
            "  &bull; Large postseismic deformation from major earthquakes: "
            "Aceh 2004 (M9.1), Nias 2005 (M8.6), Bengkulu 2007 (M8.4), "
            "North Sumatra 2012 (M8.6) — velocity residuals far exceed the "
            "1 mm/yr ITRF2020-PMM threshold<br>"
            "  &bull; Internal deformation from the active Great Sumatran Fault "
            "(2–3 mm/yr)<br><br>"
            "The two parameter sets below are <b>regional estimates only</b>. "
            "Inter-study uncertainty is <b>±3–4 mm/yr</b> on predicted velocity. "
            "Results should be interpreted with caution and not used as a "
            "substitute for site-specific GPS observations."
        )
        warn_txt.setWordWrap(True)
        warn_txt.setStyleSheet("color:#5a2a00; font-size:10px; line-height:1.5;")
        warn_txt.setTextFormat(Qt.TextFormat.RichText)
        wlay.addWidget(warn_txt)
        lay.addWidget(warn_box)

        # ── Variant selector ──────────────────────────────────────────────────
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Parameter source:"))
        self._sund_combo = QComboBox()
        for code, d in ADDITIONAL_PLATES.items():
            self._sund_combo.addItem(
                f"{d['name']}  [{d['frame']}  |  {d['data_period']}]", code
            )
        sel_row.addWidget(self._sund_combo, 1)
        lay.addLayout(sel_row)

        # Source detail label
        self._sund_src_lbl = QLabel()
        self._sund_src_lbl.setStyleSheet("color:#555555; font-size:9.5px; padding-left:4px;")
        self._sund_src_lbl.setWordWrap(True)
        lay.addWidget(self._sund_src_lbl)

        # Parameter display
        sgrp = QGroupBox("Rotation Parameters (Regional Estimate)")
        slay = QFormLayout(sgrp)
        slay.setSpacing(5)
        self._s_wx = QLabel(); self._s_wy = QLabel(); self._s_wz = QLabel()
        self._s_lat = QLabel(); self._s_lon = QLabel(); self._s_omega = QLabel()
        mono = "font-family:'Consolas','Courier New',monospace; font-size:11px;"
        for lbl in (self._s_wx, self._s_wy, self._s_wz,
                    self._s_lat, self._s_lon, self._s_omega):
            lbl.setStyleSheet(mono)
        slay.addRow("wx (mas/yr):",       self._s_wx)
        slay.addRow("wy (mas/yr):",       self._s_wy)
        slay.addRow("wz (mas/yr):",       self._s_wz)
        div2 = QFrame(); div2.setFrameShape(QFrame.Shape.HLine)
        slay.addRow(div2)
        slay.addRow("→ Lat (°N):",        self._s_lat)
        slay.addRow("→ Lon (0-360°/EW):", self._s_lon)
        slay.addRow("→ ω (°/Ma):",        self._s_omega)
        lay.addWidget(sgrp)
        lay.addStretch()

        self._sund_combo.currentIndexChanged.connect(self._update_sund_display)
        self._update_sund_display()
        self._tabs.addTab(tab, "🏝  Sundaland (Regional)")

    # ── Tab 3: Manual input ───────────────────────────────────────────────────

    def _build_tab_manual(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setSpacing(10)
        lay.setContentsMargins(12, 12, 12, 8)

        info = QLabel(
            "Enter a custom Euler Pole either by geographic coordinates "
            "(lat / lon / ω) <b>or</b> by Cartesian rotation components "
            "(wx / wy / wz). Both sections are fully editable and stay "
            "synchronised automatically."
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.TextFormat.RichText)
        info.setStyleSheet("color:#444444; font-size:10px;")
        lay.addWidget(info)

        # Name + frame
        meta_grp = QGroupBox("Identification")
        meta_lay = QFormLayout(meta_grp)
        meta_lay.setSpacing(6)
        self._m_name = QLineEdit()
        self._m_name.setPlaceholderText("e.g.  My Custom Plate")
        self._m_frame = QLineEdit()
        self._m_frame.setPlaceholderText("e.g.  ITRF2020, ITRF2014, custom…")
        meta_lay.addRow("Plate name:", self._m_name)
        meta_lay.addRow("Reference frame:", self._m_frame)
        lay.addWidget(meta_grp)

        # ── Section A: lat/lon/omega ──────────────────────────────────────────
        geo_grp = QGroupBox("Section A — Geographic Euler Pole  (lat / lon / ω)")
        geo_lay = QFormLayout(geo_grp)
        geo_lay.setSpacing(7)

        self._m_lat = QDoubleSpinBox()
        self._m_lat.setRange(-90.0, 90.0); self._m_lat.setDecimals(4)
        self._m_lat.setSuffix("  °N"); self._m_lat.setValue(50.7)

        self._m_lon = QDoubleSpinBox()
        self._m_lon.setRange(-180.0, 180.0); self._m_lon.setDecimals(4)
        self._m_lon.setSuffix("  °  (−W / +E)"); self._m_lon.setValue(-83.4)

        self._m_omega = QDoubleSpinBox()
        self._m_omega.setRange(0.0001, 5.0); self._m_omega.setDecimals(4)
        self._m_omega.setSuffix("  °/Ma"); self._m_omega.setValue(0.287)

        geo_lay.addRow("Pole latitude:", self._m_lat)
        geo_lay.addRow("Pole longitude:", self._m_lon)
        geo_lay.addRow("Rotation rate ω:", self._m_omega)
        lay.addWidget(geo_grp)

        # ── Section B: wx/wy/wz (editable) ───────────────────────────────────
        wxyz_grp = QGroupBox("Section B — Cartesian Rotation Vector  (wx / wy / wz)")
        wxyz_lay = QFormLayout(wxyz_grp)
        wxyz_lay.setSpacing(7)
        mono = "font-family:'Consolas','Courier New',monospace; font-size:11px;"

        self._m_wx = QDoubleSpinBox()
        self._m_wx.setRange(-10.0, 10.0); self._m_wx.setDecimals(3)
        self._m_wx.setSuffix("  mas/yr"); self._m_wx.setStyleSheet(mono)

        self._m_wy = QDoubleSpinBox()
        self._m_wy.setRange(-10.0, 10.0); self._m_wy.setDecimals(3)
        self._m_wy.setSuffix("  mas/yr"); self._m_wy.setStyleSheet(mono)

        self._m_wz = QDoubleSpinBox()
        self._m_wz.setRange(-10.0, 10.0); self._m_wz.setDecimals(3)
        self._m_wz.setSuffix("  mas/yr"); self._m_wz.setStyleSheet(mono)

        wxyz_lay.addRow("wx (mas/yr):", self._m_wx)
        wxyz_lay.addRow("wy (mas/yr):", self._m_wy)
        wxyz_lay.addRow("wz (mas/yr):", self._m_wz)
        lay.addWidget(wxyz_grp)
        lay.addStretch()

        # Sync flag to prevent infinite loops
        self._syncing = False

        # A → B (geographic → cartesian)
        for w in (self._m_lat, self._m_lon, self._m_omega):
            w.valueChanged.connect(self._geo_to_wxyz)
        # B → A (cartesian → geographic)
        for w in (self._m_wx, self._m_wy, self._m_wz):
            w.valueChanged.connect(self._wxyz_to_geo)

        # Initialise B from A
        self._geo_to_wxyz()

        self._tabs.addTab(tab, "✏️  Manual Input")

    def _geo_to_wxyz(self):
        """Sync Section A (lat/lon/omega) → Section B (wx/wy/wz)."""
        if self._syncing:
            return
        from core.constants import _pole_to_wxyz
        self._syncing = True
        try:
            wx, wy, wz = _pole_to_wxyz(
                self._m_lat.value(), self._m_lon.value(), self._m_omega.value())
            self._m_wx.setValue(wx)
            self._m_wy.setValue(wy)
            self._m_wz.setValue(wz)
        except Exception:
            pass
        finally:
            self._syncing = False

    def _wxyz_to_geo(self):
        """Sync Section B (wx/wy/wz) → Section A (lat/lon/omega)."""
        if self._syncing:
            return
        from core.constants import wxyz_to_pole
        self._syncing = True
        try:
            wx, wy, wz = self._m_wx.value(), self._m_wy.value(), self._m_wz.value()
            if abs(wx) < 1e-6 and abs(wy) < 1e-6 and abs(wz) < 1e-6:
                return
            pole = wxyz_to_pole(wx, wy, wz)
            self._m_lat.setValue(pole['lat'])
            self._m_lon.setValue(pole['lon_180'])
            self._m_omega.setValue(pole['omega'])
        except Exception:
            pass
        finally:
            self._syncing = False

    # ── Update helpers ────────────────────────────────────────────────────────

    def _update_preset_display(self):
        from core.constants import ITRF2020_PMM, wxyz_to_pole
        code = self._preset_combo.currentData()
        if not code or code not in ITRF2020_PMM:
            return
        pmm  = ITRF2020_PMM[code]
        pole = wxyz_to_pole(pmm['wx'], pmm['wy'], pmm['wz'])
        self._p_wx.setText(f"{pmm['wx']:+.3f} mas/yr")
        self._p_wy.setText(f"{pmm['wy']:+.3f} mas/yr")
        self._p_wz.setText(f"{pmm['wz']:+.3f} mas/yr")
        lat = pole['lat']
        self._p_lat.setText(f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}")
        lon360 = pole['lon']; lon180 = pole['lon_180']
        ew = 'E' if lon180 >= 0 else 'W'
        self._p_lon.setText(f"{lon360:.4f}°  ({abs(lon180):.4f}° {ew})")
        self._p_omega.setText(f"{pole['omega']:.4f} °/Ma")

    def _update_sund_display(self):
        from core.constants import ADDITIONAL_PLATES, wxyz_to_pole
        code = self._sund_combo.currentData()
        if not code or code not in ADDITIONAL_PLATES:
            return
        pmm  = ADDITIONAL_PLATES[code]
        pole = wxyz_to_pole(pmm['wx'], pmm['wy'], pmm['wz'])
        self._s_wx.setText(f"{pmm['wx']:+.3f} mas/yr")
        self._s_wy.setText(f"{pmm['wy']:+.3f} mas/yr")
        self._s_wz.setText(f"{pmm['wz']:+.3f} mas/yr")
        lat = pole['lat']
        self._s_lat.setText(f"{abs(lat):.4f}° {'N' if lat >= 0 else 'S'}")
        lon360 = pole['lon']; lon180 = pole['lon_180']
        ew = 'E' if lon180 >= 0 else 'W'
        self._s_lon.setText(f"{lon360:.4f}°  ({abs(lon180):.4f}° {ew})")
        self._s_omega.setText(f"{pole['omega']:.4f} °/Ma")
        src = pmm.get('source', '')
        note = pmm.get('note', '')
        self._sund_src_lbl.setText(f"📄 {src}\n{note}")

    # ── Restore active tab from ep_params ────────────────────────────────────

    def _restore_active_tab(self):
        from core.constants import ITRF2020_PMM, ADDITIONAL_PLATES
        name = self._ep_params.get('name', 'Eurasian')
        # Check ITRF2020 plates
        for i in range(self._preset_combo.count()):
            code = self._preset_combo.itemData(i)
            if code in ITRF2020_PMM and ITRF2020_PMM[code]['name'] == name:
                self._preset_combo.setCurrentIndex(i)
                self._tabs.setCurrentIndex(0)
                return
        # Check Sundaland plates
        for i in range(self._sund_combo.count()):
            code = self._sund_combo.itemData(i)
            if code in ADDITIONAL_PLATES and ADDITIONAL_PLATES[code]['name'] == name:
                self._sund_combo.setCurrentIndex(i)
                self._tabs.setCurrentIndex(1)
                return
        # Default to EURA
        for i in range(self._preset_combo.count()):
            if self._preset_combo.itemData(i) == 'EURA':
                self._preset_combo.setCurrentIndex(i)
                break
        self._tabs.setCurrentIndex(0)

    # ── Accept / get_params ───────────────────────────────────────────────────

    def _on_accept(self):
        from core.constants import ITRF2020_PMM, ADDITIONAL_PLATES, wxyz_to_pole, _pole_to_wxyz
        tab = self._tabs.currentIndex()

        if tab == 0:
            # Preset ITRF2020
            code = self._preset_combo.currentData() or 'EURA'
            pmm  = ITRF2020_PMM[code]
            pole = wxyz_to_pole(pmm['wx'], pmm['wy'], pmm['wz'])
            pole.update({
                'name'  : pmm['name'],
                'source': 'Altamimi et al. (2023) ITRF2020-PMM Table 1',
                'frame' : 'ITRF2020',
                'ref'   : 'doi:10.1029/2023GL106373',
            })

        elif tab == 1:
            # Sundaland regional estimate
            code = self._sund_combo.currentData()
            pmm  = ADDITIONAL_PLATES[code]
            pole = wxyz_to_pole(pmm['wx'], pmm['wy'], pmm['wz'])
            pole.update({
                'name'  : pmm['name'],
                'source': pmm.get('source', 'Regional estimate'),
                'frame' : pmm.get('frame', 'Non-ITRF2020'),
                'ref'   : pmm.get('source', ''),
                'warning': pmm.get('note', ''),
            })

        else:
            # Manual input — use wx/wy/wz directly (Section B)
            name  = self._m_name.text().strip() or "Custom Plate"
            frame = self._m_frame.text().strip() or "User-defined"
            wx = self._m_wx.value()
            wy = self._m_wy.value()
            wz = self._m_wz.value()
            # Also capture lat/lon/omega from Section A for metadata
            lat   = self._m_lat.value()
            lon   = self._m_lon.value()
            omega = self._m_omega.value()
            from core.constants import wxyz_to_pole
            pole = wxyz_to_pole(wx, wy, wz)
            pole.update({
                'name'  : name,
                'source': (f"Manual input — lat={lat:.4f}°N, lon={lon:.4f}°, "
                           f"ω={omega:.4f}°/Ma  |  wx={wx:+.3f}, wy={wy:+.3f}, wz={wz:+.3f} mas/yr"),
                'frame' : frame,
                'ref'   : 'User-defined custom Euler Pole',
            })

        self._result = pole
        self.accept()

    def get_params(self) -> dict:
        """Return the Euler Pole parameter dict after dialog is accepted."""
        return self._result or {}

    def get_plate_code(self) -> str:
        tab = self._tabs.currentIndex()
        if tab == 0:
            return self._preset_combo.currentData() or 'EURA'
        elif tab == 1:
            return self._sund_combo.currentData() or 'SUND_S07'
        else:
            return 'CUSTOM'


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About GeoPlate Analyst")
        self.setFixedSize(560, 620)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(24, 20, 24, 16)

        from core.constants import APP_VERSION, APP_AUTHOR, APP_NAME

        # ── Text colours — white works on both dark (#1e1e1e) and
        # light (#F5F0F0) backgrounds because QGroupBox adds its own
        # slightly-contrasted background in both themes.
        C_TITLE = "#5599dd"      # blue accent — visible on any bg
        C_BODY  = "#ffffff"      # white — readable on dark & light
        C_SUB   = "#aaaaaa"      # muted grey subtitle
        C_DIV   = "#555555"      # divider line

        # ── Header ────────────────────────────────────────────────────────────
        title_lbl = QLabel(
            f'<span style="font-size:16px; font-weight:bold; color:{C_TITLE};">'
            '🌏 GeoPlate Analyst — Sundaland</span>'
        )
        layout.addWidget(title_lbl)

        version_lbl = QLabel(
            f'<span style="color:{C_SUB}; font-size:9px;">'
            f'Version {APP_VERSION} &nbsp;|&nbsp; {APP_AUTHOR} &nbsp;|&nbsp; '
            f'Reference Frame: ITRF2020</span>'
        )
        layout.addWidget(version_lbl)

        div_top = QFrame()
        div_top.setFrameShape(QFrame.Shape.HLine)
        div_top.setStyleSheet(f"color:{C_DIV}; margin:4px 0px;")
        layout.addWidget(div_top)

        # ── Description ───────────────────────────────────────────────────────
        desc = QLabel(
            "<b>GeoPlate Analyst</b> is a tectonic plate velocity calculator "
            "for the <b>Sundaland</b> region and surrounding areas. "
            "The application uses the <b>Euler Pole</b> method based on the "
            "<b>ITRF2020</b> (International Terrestrial Reference Frame 2020) "
            "reference frame, with official plate rotation parameters from "
            "<i>Altamimi et al. (2023)</i>."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{C_BODY}; font-size:10px;")
        layout.addWidget(desc)

        # ── Calculation Method ────────────────────────────────────────────────
        method_grp = QGroupBox("Calculation Method")
        method_lay = QVBoxLayout(method_grp)
        method_lay.setSpacing(4)
        method_txt = QLabel(
            "<b>Core formula:</b> &nbsp; v&#8407; = &#969;&#8407; &times; r&#8407;<br><br>"
            "The plate velocity at a given coordinate is computed as the "
            "cross product of the Euler rotation vector "
            "<b>&#969;&#8407;</b> (rad/yr) and the observation point position vector "
            "<b>r&#8407;</b> (km) in the ECEF (<i>Earth-Centered, Earth-Fixed</i>) "
            "coordinate system, producing a velocity vector in <b>mm/yr</b>."
            "<br><br>"
            "<b>Rotation components</b> wx, wy, wz in mas/yr "
            "(<i>milli-arcsecond per year</i>) are taken directly from the "
            "official ITRF2020 Plate Motion Model (PMM) &mdash; Altamimi et al. "
            "(2023) Table 1, covering 12 major tectonic plates. Results are "
            "projected onto topocentric components <b>vN</b> (North) and "
            "<b>vE</b> (East), along with total velocity <b>vT</b> and azimuth."
            "<br><br>"
            "<b>Origin Rate Bias (ORB)</b> is applied to every calculation "
            "following Altamimi (2023) Section 5, ensuring full consistency "
            "with the ITRF2020 frame: "
            "Tx = +0.37 mm/yr, Ty = +0.35 mm/yr, Tz = +0.74 mm/yr."
            "<br><br>"
            "<b>Sundaland plate (SUND)</b> is not included in the official "
            "ITRF2020-PMM table. The SUND parameters used in this application "
            "are based on a regional estimate from Simons et al. (2007) as a "
            "supplementary reference, and are explicitly labelled to avoid "
            "confusion with the official ITRF2020 plates."
        )
        method_txt.setWordWrap(True)
        method_txt.setStyleSheet(f"color:{C_BODY}; font-size:10px; line-height:1.5;")
        method_lay.addWidget(method_txt)
        layout.addWidget(method_grp)

        # ── Scientific References ─────────────────────────────────────────────
        ref_grp = QGroupBox("Scientific References")
        ref_lay = QVBoxLayout(ref_grp)
        ref_lay.setSpacing(4)
        refs = QLabel(
            "&#9312; <b>Altamimi, Z., M&eacute;tivier, L., Rebischung, P., Rouby, H., &amp; "
            "Collilieux, X. (2023).</b><br>"
            "&nbsp;&nbsp;&nbsp;ITRF2020 plate motion model. "
            "<i>Journal of Geodesy</i>, 97(5), 48.<br>"
            "&nbsp;&nbsp;&nbsp;doi: <i>10.1007/s00190-023-01737-x</i>"
            "&nbsp;&mdash; <b>Primary reference for PMM &amp; ORB</b><br><br>"
            "&#9313; <b>Simons, W. J. F., et al. (2007).</b><br>"
            "&nbsp;&nbsp;&nbsp;A decade of GPS in Southeast Asia: Resolving "
            "Sundaland motion and boundaries.<br>"
            "&nbsp;&nbsp;&nbsp;<i>Journal of Geophysical Research</i>, "
            "112, B12402.<br>"
            "&nbsp;&nbsp;&nbsp;doi: <i>10.1029/2007JB004948</i>"
            "&nbsp;&mdash; <b>Sundaland plate (SUND) parameter estimate</b><br><br>"
            "&#9314; <b>Bird, P. (2003).</b><br>"
            "&nbsp;&nbsp;&nbsp;An updated digital model of plate boundaries.<br>"
            "&nbsp;&nbsp;&nbsp;<i>Geochemistry, Geophysics, Geosystems</i>, "
            "4(3), 1027.<br>"
            "&nbsp;&nbsp;&nbsp;doi: <i>10.1029/2001GC000252</i>"
            "&nbsp;&mdash; <b>Sundaland plate boundary data on map</b>"
        )
        refs.setWordWrap(True)
        refs.setStyleSheet(f"color:{C_BODY}; font-size:10px; line-height:1.7;")
        ref_lay.addWidget(refs)
        layout.addWidget(ref_grp)

        # ── Application Features ──────────────────────────────────────────────
        feat_grp = QGroupBox("Application Features")
        feat_lay = QVBoxLayout(feat_grp)
        feat_txt = QLabel(
            "&nbsp;<b>Interactive map</b> &mdash; zoom, pan, click-to-coordinate<br>"
            "&nbsp;<b>Euler Pole calculator</b> &mdash; 12 ITRF2020 plates + SUND<br>"
            "&nbsp;<b>GPS data input</b> &mdash; import CSV / Excel (vN, vE)<br>"
            "&nbsp;<b>GPS vs Euler comparison</b> &mdash; residuals &amp; agreement (%)<br>"
            "&nbsp;<b>Location search</b> &mdash; offline database + Nominatim online<br>"
            "&nbsp;<b>Export results</b> &mdash; Excel, CSV, PDF report, project (.json)"
        )
        feat_txt.setWordWrap(True)
        feat_txt.setStyleSheet(f"color:{C_BODY}; font-size:10px; line-height:1.7;")
        feat_lay.addWidget(feat_txt)
        layout.addWidget(feat_grp)

        layout.addStretch()

        div_bot = QFrame()
        div_bot.setFrameShape(QFrame.Shape.HLine)
        div_bot.setStyleSheet(f"color:{C_DIV};")
        layout.addWidget(div_bot)

        btn = QPushButton("Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignRight)
