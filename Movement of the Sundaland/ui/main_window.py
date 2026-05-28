"""
ui/main_window.py — GeoPlate Analyst v2.1
Light #F5F0F0 theme · Zoom buttons top-right of map · Results in separate window
"""

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QStatusBar, QProgressBar,
    QLabel, QFileDialog, QMessageBox, QSizePolicy,
    QPushButton, QFrame, QButtonGroup, QDialog,
    QVBoxLayout as QVBox, QHBoxLayout as QHBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QAction, QKeySequence, QUndoStack, QUndoCommand

from models.data_models import ObservationPoint, ProjectData
from core.constants import EULER_POLE, DEFAULT_POINTS, APP_NAME, APP_VERSION
from services.calculation_worker import CalculationWorker
from services.search_worker import SearchWorker
from services.input_service import (
    load_csv, load_excel,
    export_excel, export_csv, save_project, load_project,
)
from ui.input_panel      import InputPanel
from ui.result_window    import ResultWindow
from ui.coord_popup           import CoordPopup
from ui.search_result_dialog  import SearchResultDialog
from ui.theme_manager         import apply as apply_theme, get_current as get_theme
from ui.gps_panel        import GPSPanel
from ui.dialogs          import AddPointDialog, EulerPoleDialog, AboutDialog
from visualization.map_canvas import MapCanvas



# ── Undo/Redo Commands ─────────────────────────────────────────────────────────

class AddPointCommand(QUndoCommand):
    """Undoable: add one observation point."""
    def __init__(self, window, point: ObservationPoint, description="Add Point"):
        super().__init__(description)
        self._win   = window
        self._point = point

    def redo(self):
        self._win._project.add_point(self._point)
        self._win.input_panel.add_row(self._point)
        self._win._update_point_count()
        self._win._set_status(f"➕ Point '{self._point.name}' added.")

    def undo(self):
        idx = len(self._win._project.points) - 1
        # Find exact index in case multiple points exist
        for i, p in enumerate(self._win._project.points):
            if p is self._point:
                idx = i
                break
        self._win._project.remove_point(idx)
        self._win._refresh_input_table()
        self._win._set_status(f"↩ Undo: removed '{self._point.name}'.")


class RemovePointCommand(QUndoCommand):
    """Undoable: remove one observation point by index."""
    def __init__(self, window, index: int, description="Remove Point"):
        super().__init__(description)
        self._win   = window
        self._index = index
        self._point = window._project.points[index]

    def redo(self):
        self._win._project.remove_point(self._index)
        self._win._refresh_input_table()
        self._win._update_point_count()
        self._win._set_status(f"➖ Point '{self._point.name}' removed.")

    def undo(self):
        # Re-insert at original position
        self._win._project.points.insert(self._index, self._point)
        self._win._refresh_input_table()
        self._win._update_point_count()
        self._win._set_status(f"↩ Undo: restored '{self._point.name}'.")


class LoadPointsCommand(QUndoCommand):
    """Undoable: bulk load points (CSV/Excel/Defaults)."""
    def __init__(self, window, new_points: list, description="Load Points"):
        super().__init__(description)
        self._win        = window
        self._new_points = new_points
        self._old_points = list(window._project.points)

    def redo(self):
        self._win._project.points = list(self._new_points)
        self._win._refresh_input_table()
        self._win._set_status(f"📂 Loaded {len(self._new_points)} point(s).")

    def undo(self):
        self._win._project.points = list(self._old_points)
        self._win._refresh_input_table()
        self._win._set_status(f"↩ Undo: restored {len(self._old_points)} point(s).")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(1300, 820)

        self._project = ProjectData()
        self._worker  = None
        self._search_worker = None
        self._ep      = dict(EULER_POLE)
        self._calc_success = False

        # Undo/Redo stack
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(50)

        # Separate result window (created once, show/hide)
        self._result_win = ResultWindow(parent=None)
        self._result_win.export_excel_requested.connect(self._on_export_excel)
        self._result_win.export_csv_requested.connect(self._on_export_csv)

        self._gps_panel  = GPSPanel(parent=None)
        self._coord_popup = CoordPopup(parent=None)

        self._build_menu()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._connect_signals()
        self._set_status("Welcome!  Add observation points to begin.")

    # ── UI CONSTRUCTION ────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        fm = mb.addMenu("&File")
        fm.addAction("🆕  New Project",      self._on_new_project)
        fm.addAction("📂  Open Project…",    self._on_open_project)
        fm.addAction("💾  Save Project…",    self._on_save_project)
        fm.addSeparator()
        fm.addAction("📄  Load CSV…",        self._on_load_csv)
        fm.addAction("📊  Load Excel…",      self._on_load_excel)
        fm.addSeparator()
        fm.addAction("💾  Export Excel…",    self._on_export_excel)
        fm.addAction("📄  Export CSV…",      self._on_export_csv)
        act_pdf = fm.addAction("📑  Export PDF Report…", self._on_export_pdf)
        act_pdf.setShortcut(QKeySequence("Ctrl+Shift+P"))
        fm.addAction("🖼   Save Map (PNG)…", self._on_save_image)
        fm.addSeparator()
        fm.addAction("✖   Exit",             self.close)

        em = mb.addMenu("&Edit")
        # Undo / Redo
        act_undo = self._undo_stack.createUndoAction(self, "↩  Undo")
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        act_redo = self._undo_stack.createRedoAction(self, "↪  Redo")
        act_redo.setShortcut(QKeySequence.StandardKey.Redo)
        em.addAction(act_undo)
        em.addAction(act_redo)
        em.addSeparator()
        em.addAction("➕  Add Point…",            self._on_add_point)
        em.addAction("➖  Remove Selected Point",  self._on_remove_selected)
        em.addSeparator()
        em.addAction("🏙   Load Default Data",     self._on_load_defaults)
        em.addSeparator()
        em.addAction("🌐  Euler Pole Parameters…", self._on_euler_pole)

        vm = mb.addMenu("&View")
        self._act_click_mode = vm.addAction("📍  Map Click Mode (add point)", self._on_toggle_click_mode)
        self._act_click_mode.setCheckable(True)
        vm.addSeparator()
        vm.addAction("📊  Show Results Window", self._show_results_window)
        vm.addSeparator()
        self._act_theme = vm.addAction("🌙  Switch to Dark Theme", self._toggle_theme)
        vm.addAction("🛰️   GPS Correction Window", self._show_gps_panel)

        hm = mb.addMenu("&Help")
        hm.addAction("ℹ   About…", self._on_about)

    def _build_toolbar(self):
        tb = QToolBar("Main Toolbar")
        tb.setMovable(False)
        tb.setIconSize(QSize(20, 20))
        self.addToolBar(tb)

        def tbtn(text, slot, tip=""):
            act = QAction(text, self)
            act.triggered.connect(slot)
            act.setToolTip(tip)
            tb.addAction(act)
            return act

        tbtn("➕ Add",   self._on_add_point,       "Add point manually")
        tbtn("📂 CSV",         self._on_load_csv,         "Load from CSV")
        tbtn("📊 Excel",       self._on_load_excel,       "Load from Excel")
        tb.addSeparator()
        tbtn("🏙 Default",    self._on_load_defaults,    "Load 8 default cities")
        tb.addSeparator()
        tbtn("▶ Run",     self._on_run_calculation,  "Run Euler Pole velocity calculation")
        tb.addSeparator()
        tbtn("📊 Results",     self._show_results_window, "Show results table & rose diagram")
        tbtn("💾 Excel", self._on_export_excel,     "Export results to Excel")
        tbtn("🖼 Map",    self._on_save_image,       "Save map to PNG")
        tb.addSeparator()
        tbtn("🌐 Euler",  self._on_euler_pole,       "View / edit Euler Pole parameters")
        tb.addSeparator()
        tbtn("🗑 Clear",   self._on_clear_all,        "Delete all data")

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # ── Title bar ──────────────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("title_bar")
        tbl = QHBoxLayout(title_bar)
        tbl.setContentsMargins(10, 5, 10, 5)
        title_lbl = QLabel(f"🌏  {APP_NAME}")
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setObjectName("app_title_lbl")
        sub_lbl = QLabel(
            f"Euler Pole: {EULER_POLE.get('name','EURA')} | ITRF2020-PMM, Altamimi (2023)  |  "
            f"wx={EULER_POLE['wx']:.3f}, wy={EULER_POLE['wy']:.3f}, wz={EULER_POLE['wz']:.3f} mas/yr  |  "
            f"omega={EULER_POLE['omega']:.4f} deg/Ma"
        )
        sub_lbl.setObjectName("app_sub_lbl")
        tbl.addWidget(title_lbl)
        tbl.addStretch()
        tbl.addWidget(sub_lbl)

        # Theme toggle button in title bar
        self._theme_btn = QPushButton("🌙 Dark")
        self._theme_btn.setFixedHeight(26)
        self._theme_btn.setFixedWidth(80)
        self._theme_btn.setToolTip("Switch to Dark theme")
        self._theme_btn.setStyleSheet(
            "QPushButton { background-color:#4A7EC7; color:#ffffff;"
            " border:1px solid #3060A8; border-radius:4px;"
            " font-size:11px; font-weight:bold; padding:2px 8px; }"
            "QPushButton:hover { background-color:#2a5aa0; }"
        )
        self._theme_btn.clicked.connect(self._toggle_theme)
        tbl.addSpacing(8)
        tbl.addWidget(self._theme_btn)
        self._title_bar = title_bar
        root.addWidget(title_bar)

        # ── Horizontal splitter: input panel | map ─────────────────────────────
        h_split = QSplitter(Qt.Orientation.Horizontal)
        self._h_split = h_split          # stored for maximise/restore

        self.input_panel = InputPanel()
        self.input_panel.setMinimumWidth(290)
        self.input_panel.setMaximumWidth(420)

        # ── Map wrapper (toolbar + canvas + coord bar) ─────────────────────────
        map_wrap = QWidget()
        map_wrap.setStyleSheet("background-color:#f2f2f2;")
        mwl = QVBoxLayout(map_wrap)
        mwl.setContentsMargins(0, 0, 0, 0)
        mwl.setSpacing(0)
        self._map_wrap = map_wrap        # stored for maximise/restore

        # ── Map toolbar (blue top bar) ─────────────────────────────────────────
        top_bar = QWidget()
        top_bar.setObjectName("map_toolbar")
        top_bar.setFixedHeight(36)
        top_bar.setStyleSheet(
            "background-color:#1a5a8a; border-bottom:2px solid #2a7ab0;"
        )
        tbar_lay = QHBoxLayout(top_bar)
        tbar_lay.setContentsMargins(8, 3, 8, 3)
        tbar_lay.setSpacing(2)

        map_lbl = QLabel("🗺  Interactive Map")
        map_lbl.setStyleSheet("color:#ffffff; font-weight:bold; font-size:11px; border:none;")
        tbar_lay.addWidget(map_lbl)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet("color:#2a7ab0;")
        tbar_lay.addWidget(sep1)

        # ── Map tool buttons (ArcGIS-style) ────────────────────────────────────
        _tool_style = (
            "QPushButton { background-color:#0d3a6a; color:#ffffff;"
            " border:2px solid #2a7ab0; border-radius:5px;"
            " font-size:15px; font-family:'Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji',Arial,sans-serif;"
            " min-width:30px; max-width:30px; min-height:30px; max-height:30px; padding:0px; }"
            "QPushButton:hover { background-color:#1a5a8a; border-color:#4a9ad0; }"
            "QPushButton:checked { background-color:#ffffff; border:2px solid #2a7ab0; color:#0d3a6a; }"
            "QPushButton:pressed { background-color:#061a3a; color:#ffffff; }"
        )

        self.btn_tool_pointer = QPushButton("↖")
        self.btn_tool_pointer.setCheckable(True)
        self.btn_tool_pointer.setChecked(True)
        self.btn_tool_pointer.setToolTip("Pointer — click map for coordinates")
        self.btn_tool_pointer.setStyleSheet(_tool_style)

        self.btn_tool_hand = QPushButton("✋")
        self.btn_tool_hand.setCheckable(True)
        self.btn_tool_hand.setToolTip("Hand — drag to pan map")
        self.btn_tool_hand.setStyleSheet(_tool_style)

        self.btn_tool_addpoint = QPushButton("📍")
        self.btn_tool_addpoint.setCheckable(True)
        self.btn_tool_addpoint.setToolTip("Add Point — click map to add observation point")
        self.btn_tool_addpoint.setStyleSheet(_tool_style)

        self._map_tool_group = [
            self.btn_tool_pointer,
            self.btn_tool_hand,
            self.btn_tool_addpoint,
        ]
        for b in self._map_tool_group:
            tbar_lay.addWidget(b)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color:#2a7ab0;")
        tbar_lay.addWidget(sep2)

        # ── Zoom controls ──────────────────────────────────────────────────────
        self.btn_zoom_in    = QPushButton("+")
        self.btn_zoom_out   = QPushButton("−")
        self.btn_zoom_reset = QPushButton("⌂")
        self.btn_zoom_in.setObjectName("btn_zoom_in")
        self.btn_zoom_out.setObjectName("btn_zoom_out")
        self.btn_zoom_reset.setObjectName("btn_zoom_reset")
        self.btn_zoom_in.setToolTip("Zoom In  (+)")
        self.btn_zoom_out.setToolTip("Zoom Out  (−)")
        self.btn_zoom_reset.setToolTip("Reset View  (R / double-click)")
        for b in (self.btn_zoom_in, self.btn_zoom_out, self.btn_zoom_reset):
            tbar_lay.addWidget(b)

        sep3 = QFrame()
        sep3.setFrameShape(QFrame.Shape.VLine)
        sep3.setStyleSheet("color:#2a7ab0;")
        tbar_lay.addWidget(sep3)

        # ── Vector scale slider ────────────────────────────────────────────────
        # Allows dynamic adjustment of arrow length without restarting.
        # Slider integer range 1..20 maps to scale 0.01..0.20 (step 0.01).
        from PyQt6.QtWidgets import QSlider, QLabel as _QLabel
        from visualization.map_canvas import (
            VECTOR_SCALE_DEFAULT, VECTOR_SCALE_MIN, VECTOR_SCALE_MAX
        )

        vec_lbl = _QLabel("Vectors:")
        vec_lbl.setStyleSheet("color:#cce4ff; font-size:10px; border:none;")
        tbar_lay.addWidget(vec_lbl)

        self._vec_slider = QSlider(Qt.Orientation.Horizontal)
        self._vec_slider.setFixedWidth(90)
        self._vec_slider.setFixedHeight(20)
        self._vec_slider.setMinimum(1)   # → 0.01 deg/(mm/yr)
        self._vec_slider.setMaximum(20)  # → 0.20 deg/(mm/yr)
        # Map default (0.05) to integer 5
        _default_int = round(VECTOR_SCALE_DEFAULT / VECTOR_SCALE_MIN)
        self._vec_slider.setValue(_default_int)
        self._vec_slider.setToolTip(
            "Vector Scale — drag to adjust arrow length\n"
            "Left = shorter arrows   Right = longer arrows"
        )
        self._vec_slider.setStyleSheet(
            "QSlider::groove:horizontal { height:4px; background:#2a7ab0; border-radius:2px; }"
            "QSlider::handle:horizontal { background:#ffffff; border:1px solid #4a9ad0;"
            " width:12px; height:12px; margin:-4px 0; border-radius:6px; }"
            "QSlider::sub-page:horizontal { background:#88ccff; border-radius:2px; }"
        )
        tbar_lay.addWidget(self._vec_slider)

        # Live readout label (e.g. "×0.05")
        self._vec_scale_lbl = _QLabel(f"x{VECTOR_SCALE_DEFAULT:.2f}")
        self._vec_scale_lbl.setStyleSheet(
            "color:#cce4ff; font-size:10px; border:none; min-width:34px;"
        )
        tbar_lay.addWidget(self._vec_scale_lbl)

        sep4 = QFrame()
        sep4.setFrameShape(QFrame.Shape.VLine)
        sep4.setStyleSheet("color:#2a7ab0;")
        tbar_lay.addWidget(sep4)

        # ── Maximise / restore button ──────────────────────────────────────────
        # Expands the map panel to fill the window (hides input panel and title
        # bar) — professional GIS behaviour similar to QGIS/ArcGIS.
        self.btn_maximize = QPushButton("⛶")
        self.btn_maximize.setCheckable(True)
        self.btn_maximize.setToolTip(
            "Maximise Map Panel  (F11)\n"
            "Hides the input panel and title bar for a full-screen map view.\n"
            "Click again or press F11 to restore."
        )
        self.btn_maximize.setStyleSheet(_tool_style)
        tbar_lay.addWidget(self.btn_maximize)

        tbar_lay.addStretch()

        # Active tool readout (right-aligned)
        self._tool_lbl = QLabel("Tool: Pointer")
        self._tool_lbl.setStyleSheet("color:#cce4ff; font-size:10px; border:none;")
        tbar_lay.addWidget(self._tool_lbl)

        self._map_toolbar = top_bar
        mwl.addWidget(top_bar)

        # ── Map canvas ─────────────────────────────────────────────────────────
        self.map_canvas = MapCanvas()
        self.map_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        mwl.addWidget(self.map_canvas, 1)

        # ── Coordinate bar below map ───────────────────────────────────────────
        coord_bar = QWidget()
        coord_bar.setObjectName("coord_bar")
        coord_bar.setFixedHeight(20)
        cbl = QHBoxLayout(coord_bar)
        cbl.setContentsMargins(8, 2, 8, 2)
        self._coords_lbl = QLabel("Lat: —   Lon: —")
        self._coords_lbl.setObjectName("coords_lbl")
        cbl.addWidget(self._coords_lbl)
        cbl.addStretch()
        hint_lbl = QLabel("Scroll=Zoom  |  Drag=Pan  |  R=Reset  |  Ctrl+Z=Undo  |  F11=Maximise")
        hint_lbl.setObjectName("hint_lbl")
        cbl.addWidget(hint_lbl)
        self._coord_bar = coord_bar
        mwl.addWidget(coord_bar)

        h_split.addWidget(self.input_panel)
        h_split.addWidget(map_wrap)
        h_split.setStretchFactor(1, 4)

        root.addWidget(h_split, 1)

    def _build_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet("color:#555555;")
        sb.addWidget(self._status_lbl, 1)
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(200)
        self._progress.setMaximumHeight(14)
        self._progress.setVisible(False)
        sb.addPermanentWidget(self._progress)
        self._point_count_lbl = QLabel("0 points")
        self._point_count_lbl.setStyleSheet("color:#555555;")
        sb.addPermanentWidget(self._point_count_lbl)

    # ── SIGNALS ────────────────────────────────────────────────────────────────

    def _connect_signals(self):
        p = self.input_panel
        p.add_point_requested.connect(self._on_add_point)
        p.remove_point_requested.connect(self._on_remove_point)
        p.load_csv_requested.connect(self._on_load_csv)
        p.load_excel_requested.connect(self._on_load_excel)
        p.load_defaults_requested.connect(self._on_load_defaults)
        p.gps_correction_requested.connect(self._show_gps_panel)
        p.search_location_requested.connect(self._on_search_location)

        self.map_canvas.coords_hovered.connect(self._on_coords_hovered)
        self.map_canvas.coord_clicked.connect(self._on_coord_clicked)
        # Map-panel maximise signal emitted by canvas (e.g. via F11 key)
        self.map_canvas.maximize_toggled.connect(self._on_map_maximize_toggled)

        self._coord_popup.add_point_requested.connect(self._on_add_from_popup)

        self.btn_zoom_in.clicked.connect(self._on_zoom_in)
        self.btn_zoom_out.clicked.connect(self._on_zoom_out)
        self.btn_zoom_reset.clicked.connect(self.map_canvas.reset_view)

        # Map tool buttons
        self.btn_tool_pointer.clicked.connect(
            lambda: self._set_map_tool('pointer'))
        self.btn_tool_hand.clicked.connect(
            lambda: self._set_map_tool('hand'))
        self.btn_tool_addpoint.clicked.connect(
            lambda: self._set_map_tool('addpoint'))

        # Maximise button in map toolbar
        self.btn_maximize.clicked.connect(self._on_btn_maximize_clicked)

        # Vector scale slider — valueChanged fires on every tick for live preview
        self._vec_slider.valueChanged.connect(self._on_vector_scale_changed)

        # GPS panel signals
        self._gps_panel.gps_overlay_ready.connect(self.map_canvas.set_gps_overlay)
        self._gps_panel.gps_overlay_clear.connect(self.map_canvas.clear_gps_overlay)

    # ── SLOTS ──────────────────────────────────────────────────────────────────

    def _show_results_window(self):
        self._result_win.show()
        self._result_win.raise_()
        self._result_win.activateWindow()

    def _show_gps_panel(self):
        self._gps_panel.show()
        self._gps_panel.raise_()
        self._gps_panel.activateWindow()

    def _on_zoom_in(self):
        self.map_canvas._extent_ctrl.zoom(0.80)
        self.map_canvas._apply_extent_only()

    def _on_zoom_out(self):
        self.map_canvas._extent_ctrl.zoom(1.20)
        self.map_canvas._apply_extent_only()

    def _set_map_tool(self, tool: str):
        """Switch map interaction mode."""
        for b in self._map_tool_group:
            b.setChecked(False)

        if tool == 'pointer':
            self.btn_tool_pointer.setChecked(True)
            self.map_canvas.set_click_mode(False)
            self.map_canvas.set_tool_mode('pointer')
            self._tool_lbl.setText("Tool: Pointer")
            self._act_click_mode.setChecked(False)

        elif tool == 'hand':
            self.btn_tool_hand.setChecked(True)
            self.map_canvas.set_click_mode(False)
            self.map_canvas.set_tool_mode('hand')
            self._tool_lbl.setText("Tool: Pan")
            self._act_click_mode.setChecked(False)

        elif tool == 'addpoint':
            self.btn_tool_addpoint.setChecked(True)
            self.map_canvas.set_click_mode(True)
            self.map_canvas.set_tool_mode('addpoint')
            self._tool_lbl.setText("Tool: Add Point  (click map)")
            self._act_click_mode.setChecked(True)
            self._set_status(
                "📍 Add Point mode — click anywhere on the map")

    # ── Vector scale ───────────────────────────────────────────────────────────

    def _on_vector_scale_changed(self, int_value: int):
        """
        Translate slider integer (1-20) → scale float (0.01-0.20) and
        push it to the canvas for an immediate redraw.
        """
        from visualization.map_canvas import VECTOR_SCALE_MIN
        scale = int_value * VECTOR_SCALE_MIN          # e.g. 5 -> 0.05
        self._vec_scale_lbl.setText(f"x{scale:.2f}")
        self.map_canvas.set_vector_scale(scale)

    # ── Map-panel maximise / restore ───────────────────────────────────────────

    def _on_btn_maximize_clicked(self, checked: bool):
        """
        Toolbar maximise button clicked — sync state to canvas and apply layout.
        The btn_maximize is checkable so `checked` reflects new state directly.
        """
        # Keep canvas internal state in sync (without re-emitting the signal)
        self.map_canvas._is_maximized = checked
        self._apply_map_maximized(checked)

    def _on_map_maximize_toggled(self, maximized: bool):
        """
        Canvas emitted maximize_toggled (e.g. user pressed F11).
        Sync toolbar button and apply the layout change.
        """
        # Block button signals briefly to avoid recursive loop
        self.btn_maximize.blockSignals(True)
        self.btn_maximize.setChecked(maximized)
        self.btn_maximize.blockSignals(False)
        self._apply_map_maximized(maximized)

    def _apply_map_maximized(self, maximized: bool):
        """
        Core maximise / restore logic — GIS-style panel expansion.

        When maximised:
          - Title bar hidden (saves ~40 px; keeps blue map toolbar visible).
          - Input panel (left side of splitter) hidden.
          - Toolbar button icon changes to restore symbol.
          - Map canvas fills the entire central area.

        When restored:
          - All hidden widgets shown again.
          - Splitter sizes restored.
          - Toolbar button icon reverts to maximise symbol.

        All existing map interactions (zoom, pan, click, overlay) are
        unaffected because only the surrounding Qt layout changes.
        """
        if maximized:
            # Hide non-map widgets
            self._title_bar.hide()
            self.input_panel.hide()
            # Update button tooltip & icon
            self.btn_maximize.setToolTip(
                "Restore Map Panel  (F11)\n"
                "Shows the input panel and title bar again."
            )
            self.btn_maximize.setText("⛶")   # same icon; checked state = blue
            self._set_status("🗺  Map panel maximised — F11 or ⛶ to restore")
        else:
            # Restore all widgets
            self._title_bar.show()
            self.input_panel.show()
            self.btn_maximize.setToolTip(
                "Maximise Map Panel  (F11)\n"
                "Hides the input panel and title bar for a full-screen map view.\n"
                "Click again or press F11 to restore."
            )
            self.btn_maximize.setText("⛶")
            self._set_status("Map panel restored.")

        # Trigger a background-cache refresh so the canvas redraws cleanly
        # at its new size after the Qt layout settles (200 ms delay).
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(200, lambda: self._invalidate_map_cache())

    def _invalidate_map_cache(self):
        """Force canvas to rebuild its background cache at the new size."""
        self.map_canvas._bg_cache = None
        self.map_canvas._full_redraw(empty=not self.map_canvas._results)

    # ── Coordinate display ─────────────────────────────────────────────────────

    def _on_coords_hovered(self, lat, lon):
        if lat == 0.0 and lon == 0.0:
            self._coords_lbl.setText("Lat: —   Lon: —")
        else:
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            self._coords_lbl.setText(
                f"Lat: {abs(lat):.4f}°{ns}   Lon: {abs(lon):.4f}°{ew}"
            )

    def _on_coord_clicked(self, lat: float, lon: float):
        """Show coordinate popup at click position."""
        from PyQt6.QtGui import QCursor
        self._coord_popup.show_at(lat, lon, QCursor.pos())

    def _on_add_from_popup(self, name: str, lat: float, lon: float):
        """Add point from coordinate popup — supports undo."""
        pt  = ObservationPoint(name=name, lat=lat, lon=lon)
        cmd = AddPointCommand(self, pt, f"Add '{name}' from map")
        self._undo_stack.push(cmd)
        self.map_canvas.set_click_mode(False)

    def _on_search_location(self, query: str):
        """Search location in background thread — non-blocking."""
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.abort()
            self._search_worker.wait()

        self._set_status(f"🔍 Searching for '{query}'…")
        self.input_panel.btn_search.setEnabled(False)
        self.input_panel.btn_search.setText("…")

        self._search_worker = SearchWorker(query, parent=self)
        self._search_worker.result_ready.connect(self._on_search_done)
        self._search_worker.error.connect(self._on_search_error)
        self._search_worker.finished.connect(self._on_search_finished)
        self._search_worker.start()

    def _on_search_done(self, query: str, results: list, source: str):
        if not results:
            QMessageBox.information(
                self, "Not Found",
                f"Location '{query}' not found.\n\n"
                "Tips:\n  - Check spelling\n"
                "  - Try English name\n"
                "  - Connect to internet for wider search"
            )
            self._set_status(f"'{query}' not found.")
            return

        dlg = SearchResultDialog(query, results, source, parent=self)
        if dlg.exec():
            sel = dlg.get_selected()
            if sel:
                name, lat, lon = sel
                pt = ObservationPoint(name=name, lat=lat, lon=lon)
                cmd = AddPointCommand(self, pt, f"Add '{name}' from search")
                self._undo_stack.push(cmd)
                self._update_point_count()
                src_icon = "💾" if source == "offline" else "🌐"
                self._set_status(f"{src_icon} Point '{name}' added from search.")

    def _on_search_error(self, msg: str):
        self._set_status(f"⚠ Search error: {msg[:80]}")

    def _on_search_finished(self):
        self.input_panel.btn_search.setEnabled(True)
        self.input_panel.btn_search.setText("Search")

    def _on_new_project(self):
        if not self._confirm_discard(): return
        self._project = ProjectData()
        self._refresh_input_table()
        self._result_win.clear()
        self.map_canvas.clear_map()
        self._gps_panel._on_clear()
        self._coord_popup.reset_counter()
        self._set_status("New project created.")

    def _on_open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "GeoPlate Project (*.smp);;All Files (*)"
        )
        if not path: return
        try:
            self._project = load_project(path)
            self._refresh_input_table(); self._result_win.clear(); self.map_canvas.clear_map()
            self._gps_panel._on_clear()
            self._set_status(f"Project loaded: {os.path.basename(path)}")
        except Exception as e:
            self._show_error("Failed to Open Project", str(e))

    def _on_save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "project.smp", "GeoPlate Project (*.smp);;All Files (*)"
        )
        if not path: return
        try:
            save_project(self._project, path)
            self._set_status(f"Project saved: {os.path.basename(path)}")
        except Exception as e:
            self._show_error("Failed to Save Project", str(e))

    def _on_add_point(self):
        dlg = AddPointDialog(parent=self)
        if dlg.exec():
            pt  = dlg.get_point()
            cmd = AddPointCommand(self, pt, f"Add '{pt.name}'")
            self._undo_stack.push(cmd)

    def _on_map_click(self, lat, lon):
        dlg = AddPointDialog(lat=lat, lon=lon, parent=self)
        if dlg.exec():
            pt  = dlg.get_point()
            cmd = AddPointCommand(self, pt, f"Add '{pt.name}' from map")
            self._undo_stack.push(cmd)

    def _on_remove_point(self, row):
        if 0 <= row < len(self._project.points):
            cmd = RemovePointCommand(self, row)
            self._undo_stack.push(cmd)

    def _on_remove_selected(self):
        row = self.input_panel.selected_row()
        if row >= 0:
            self._on_remove_point(row)

    def _on_load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load CSV", "", "CSV Files (*.csv);;All Files (*)")
        if path: self._load_file(path, load_csv)

    def _on_load_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Excel", "", "Excel Files (*.xlsx *.xls);;All Files (*)")
        if path: self._load_file(path, load_excel)

    def _load_file(self, path, loader_fn):
        try:
            points, warnings = loader_fn(path)
            if not points:
                self._show_error("No Data", "No valid points found in the file.")
                return
            all_points = list(self._project.points) + points
            cmd = LoadPointsCommand(self, all_points,
                                    f"Load {len(points)} points from {os.path.basename(path)}")
            self._undo_stack.push(cmd)
            msg = f"{len(points)} point(s) loaded from {os.path.basename(path)}."
            if warnings:
                msg += f"  {len(warnings)} row(s) skipped."
            self._set_status(msg)
        except Exception as e:
            self._show_error("Failed to Load File", str(e))

    def _on_load_defaults(self):
        new_pts = [ObservationPoint(name=n, lat=la, lon=lo)
                   for n, la, lo in DEFAULT_POINTS]
        all_pts = list(self._project.points) + new_pts
        cmd = LoadPointsCommand(self, all_pts, "Load Default Cities")
        self._undo_stack.push(cmd)

    def _on_clear_all(self):
        if QMessageBox.question(
            self, "Confirm", "Delete all points and results?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            self._project = ProjectData()
            self._refresh_input_table(); self._result_win.clear(); self.map_canvas.clear_map()
            self._gps_panel._on_clear()
            self._set_status("All data cleared.")

    def _on_run_calculation(self):
        if not self._project.points:
            QMessageBox.information(self, "No Points",
                                    "Please add at least 1 observation point first.")
            return
        if self._worker and self._worker.isRunning():
            self._worker.abort(); self._worker.wait()
        self._project.clear_results(); self._result_win.clear()
        self._progress.setVisible(True)
        self._progress.setRange(0, len(self._project.points))
        self._progress.setValue(0)
        self._set_status("Computing velocity vectors…")
        if 'wx' in self._ep and self._ep['wx'] is not None:
            self._worker = CalculationWorker(
                points=self._project.points,
                wx_mas=self._ep['wx'],
                wy_mas=self._ep['wy'],
                wz_mas=self._ep['wz'],
                apply_orb=True,
                parent=self,
            )
        else:
            self._worker = CalculationWorker(
                points=self._project.points,
                ep_lat=self._ep['lat'],
                ep_lon=self._ep.get('lon_180', self._ep.get('lon', 0.0)),
                omega=self._ep['omega'],
                apply_orb=True,
                parent=self,
            )
        self._worker.progress.connect(self._on_calc_progress)
        self._worker.result_ready.connect(self._on_calc_done)
        self._worker.error.connect(self._on_calc_error)
        self._worker.finished.connect(self._on_calc_finished)
        self._worker.start()

    def _on_calc_progress(self, current, total):
        self._progress.setValue(current)
        self._set_status(f"Computing … {current}/{total}")

    def _on_calc_done(self, results):
        self._project.results = results
        self._progress.setVisible(False)
        self._result_win.set_results(results)
        self.map_canvas.plot_results(results)
        self._gps_panel.set_euler_results(results)
        self._show_results_window()
        if results:
            self._set_status(
                f"✅ Calculation complete — {len(results)} points.  "
                f"Velocity range: {min(r.vT for r in results):.2f} – "
                f"{max(r.vT for r in results):.2f} mm/yr"
            )
        else:
            self._set_status("✅ Calculation complete — 0 points computed.")
        self._calc_success = True

    def _on_calc_finished(self):
        self._progress.setVisible(False)
        if not getattr(self, '_calc_success', False):
            self._set_status("Ready.")
        self._calc_success = False

    def _on_calc_error(self, msg):
        self._progress.setVisible(False)
        self._calc_success = False
        self._show_error("Calculation Error", msg)

    def _on_export_excel(self):
        if not self._project.results:
            QMessageBox.information(self, "No Results", "Please run the calculation first."); return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", "geoplate_results.xlsx", "Excel Files (*.xlsx);;All Files (*)"
        )
        if path:
            try:
                export_excel(self._project.results, path, euler_info=self._ep)
                self._set_status(f"Excel saved: {os.path.basename(path)}")
            except Exception as e:
                self._show_error("Failed to Export Excel", str(e))

    def _on_export_csv(self):
        if not self._project.results:
            QMessageBox.information(self, "No Results", "Please run the calculation first."); return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", "geoplate_results.csv", "CSV Files (*.csv);;All Files (*)"
        )
        if path:
            try:
                export_csv(self._project.results, path)
                self._set_status(f"CSV saved: {os.path.basename(path)}")
            except Exception as e:
                self._show_error("Failed to Export CSV", str(e))

    def _on_export_pdf(self):
        """Export full PDF report with table + charts."""
        if not self._project.results:
            QMessageBox.information(self, "No Results",
                                    "Please run the calculation first."); return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF Report", "geoplate_report.pdf",
            "PDF Files (*.pdf);;All Files (*)"
        )
        if not path:
            return
        try:
            from services.pdf_exporter import export_pdf
            from core.constants import APP_VERSION
            self._set_status("📑 Generating PDF report…")
            export_pdf(
                self._project.results,
                path,
                euler_info=self._ep,
                app_version=APP_VERSION,
            )
            self._set_status(f"📑 PDF report saved: {os.path.basename(path)}")
            if QMessageBox.question(
                self, "PDF Saved",
                f"Report saved to:\n{path}\n\nOpen the file now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                import subprocess, sys
                if sys.platform == 'win32':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', path])
                else:
                    subprocess.Popen(['xdg-open', path])
        except Exception as e:
            self._show_error("Failed to Export PDF", str(e))

    def _on_save_image(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Map", "geoplate_map.png", "PNG Images (*.png);;All Files (*)"
        )
        if path:
            try:
                self.map_canvas.save_image(path, dpi=200)
                self._set_status(f"Map saved: {os.path.basename(path)}")
            except Exception as e:
                self._show_error("Failed to Save Image", str(e))

    def _on_euler_pole(self):
        dlg = EulerPoleDialog(self._ep, parent=self)
        if dlg.exec():
            self._ep = dlg.get_params()
            if 'wx' in self._ep:
                self._set_status(
                    f"Euler Pole: {self._ep.get('name','Custom')} | "
                    f"wx={self._ep['wx']:.3f}, wy={self._ep['wy']:.3f}, wz={self._ep['wz']:.3f} | "
                    f"omega={self._ep['omega']:.4f} deg/Ma")
            else:
                self._set_status(f"Euler Pole updated: omega={self._ep['omega']} deg/Ma")

    def _on_toggle_click_mode(self):
        enabled = self._act_click_mode.isChecked()
        if enabled:
            self._set_map_tool('addpoint')
        else:
            self._set_map_tool('pointer')

    def _on_about(self):
        AboutDialog(self).exec()

    def _toggle_theme(self):
        from PyQt6.QtWidgets import QApplication
        new_theme = 'dark' if get_theme() == 'light' else 'light'
        apply_theme(new_theme, QApplication.instance())

        self.map_canvas.set_theme(new_theme)

        if new_theme == 'dark':
            bar_style  = 'background-color:#1a1a1a; border-bottom:1px solid #333;'
            cbar_style = 'background-color:#1a1a1a; border-top:1px solid #333;'
        else:
            bar_style  = 'background-color:#f2f2f2; border-bottom:1px solid #C8C0C0;'
            cbar_style = 'background-color:#f2f2f2; border-top:1px solid #C8C0C0;'
        self._title_bar.setStyleSheet(bar_style)
        self._coord_bar.setStyleSheet(cbar_style)

        if new_theme == 'dark':
            self._act_theme.setText("☀️  Switch to Light Theme")
            self._theme_btn.setText("☀️ Light")
            self._theme_btn.setToolTip("Switch to Light theme")
            self._theme_btn.setStyleSheet(
                "QPushButton { background-color:#444444; color:#ffee88;"
                " border:1px solid #555555; border-radius:4px;"
                " font-size:11px; font-weight:bold; padding:2px 8px; }"
                "QPushButton:hover { background-color:#222222; }"
            )
            self._set_status("Dark theme applied.")
        else:
            self._act_theme.setText("🌙  Switch to Dark Theme")
            self._theme_btn.setText("🌙 Dark")
            self._theme_btn.setToolTip("Switch to Dark theme")
            self._theme_btn.setStyleSheet(
                "QPushButton { background-color:#4A7EC7; color:#ffffff;"
                " border:1px solid #3060A8; border-radius:4px;"
                " font-size:11px; font-weight:bold; padding:2px 8px; }"
                "QPushButton:hover { background-color:#2a5aa0; }"
            )
            self._set_status("Light theme applied.")

    def _refresh_input_table(self):
        self.input_panel.set_points(self._project.points)
        self._update_point_count()

    def _update_point_count(self):
        n = len(self._project.points)
        self._point_count_lbl.setText(f"{n} point{'s' if n != 1 else ''}")

    def _set_status(self, msg):
        self._status_lbl.setText(msg)

    def _show_error(self, title, detail):
        QMessageBox.critical(self, title, detail)
        self._set_status(f"❌ Error: {detail[:80]}")

    def _confirm_discard(self):
        if not self._project.points: return True
        return QMessageBox.question(
            self, "Confirm", "Current data will be lost. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.abort(); self._worker.wait()
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.abort(); self._search_worker.wait()
        self._result_win.close()
        self._gps_panel.close()
        self._coord_popup.close()
        event.accept()
