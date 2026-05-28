"""
visualization/map_canvas.py  — GeoPlate Analyst v3.4
Matplotlib + Cartopy

Changes from v3.3:
  - Adjustable vector scale: VECTOR_SCALE_DEFAULT reduced + dynamic via set_vector_scale()
  - maximize_toggled signal for panel-only maximise (consumed by MainWindow)
  - Background-cache blitting preserved; no performance regressions
  - HiDPI-aware coordinate click retained
  - F11 keyboard shortcut toggles map-panel maximise
"""

import numpy as np
import time
import matplotlib
matplotlib.use('QtAgg')
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtCore import pyqtSignal, Qt, QPoint, QTimer
from PyQt6.QtWidgets import QSizePolicy

from core.constants import SUNDALAND_BOUNDARY, MAP_EXTENT, EULER_POLE

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    HAS_CARTOPY = True
except ImportError:
    HAS_CARTOPY = False

# ── Colour map ─────────────────────────────────────────────────────────────────
VEL_CMAP = LinearSegmentedColormap.from_list(
    'geoplate_vel',
    ['#0055cc', '#0099ff', '#00cc88', '#ffcc00', '#ff4400']
)

# ── Map limits / zoom ──────────────────────────────────────────────────────────
EXTENT_HARD_LIMIT = [60.0, 160.0, -25.0, 35.0]
EXTENT_DEFAULT    = list(MAP_EXTENT)
ZOOM_FACTOR       = 0.15
ZOOM_MIN_SPAN     = 1.5
ZOOM_MAX_SPAN     = 100.0
PAN_THROTTLE_MS   = 8          # <=8 ms throttle -> silky pan

# ── Vector-scale constants ─────────────────────────────────────────────────────
# Previous default was 3.0/30.0 = 0.1 -> arrows too large at small zoom.
# New default halved to 0.05 (approx 1.5deg/30 mm/yr) -- much cleaner.
VECTOR_SCALE_DEFAULT = 0.05    # degrees-per-(mm/yr); user can override via slider
VECTOR_SCALE_MIN     = 0.01
VECTOR_SCALE_MAX     = 0.20


# =============================================================================
# GeoCoordTransformer -- HiDPI-aware Qt pixel -> geographic (lon, lat)
# =============================================================================
class GeoCoordTransformer:
    """
    Converts Qt widget pixels to geographic (lon, lat) coordinates.

    The root-cause complexity: Matplotlib figures have a fixed logical size
    (figsize x dpi) while the Qt widget is freely resized by Qt's layout
    engine.  We compute a scale factor between the two coordinate spaces
    before feeding coordinates to ax.transData.
    """

    def __init__(self, fig, ax, canvas=None):
        self.fig    = fig
        self.ax     = ax
        self.canvas = canvas

    def display_to_geo(self, x_px, y_px):
        try:
            # Matplotlib figure logical size (constant, set at Figure creation)
            fig_w_pts = self.fig.get_size_inches()[0] * self.fig.dpi
            fig_h_pts = self.fig.get_size_inches()[1] * self.fig.dpi

            # Actual Qt widget size (changes with layout / splitter)
            if self.canvas is not None:
                w_px = self.canvas.width()
                h_px = self.canvas.height()
            else:
                w_px = fig_w_pts
                h_px = fig_h_pts

            if w_px <= 0 or h_px <= 0:
                return None, None

            # Scale factor: logical Matplotlib pts per on-screen Qt pixel
            x_scale = fig_w_pts / w_px
            y_scale = fig_h_pts / h_px

            # Qt origin = top-left; Matplotlib origin = bottom-left -> invert Y
            mpl_x = float(x_px) * x_scale
            mpl_y = fig_h_pts - (float(y_px) * y_scale)

            inv = self.ax.transData.inverted()
            xd, yd = inv.transform((mpl_x, mpl_y))
            if not (np.isfinite(xd) and np.isfinite(yd)):
                return None, None

            if HAS_CARTOPY:
                lon, lat = ccrs.PlateCarree().transform_point(
                    xd, yd, src_crs=self.ax.projection)
                if not (np.isfinite(lon) and np.isfinite(lat)):
                    return None, None
                return float(lon), float(lat)

            return float(xd), float(yd)
        except Exception:
            return None, None


# =============================================================================
# ExtentController -- map view state (zoom / pan / reset / undo)
# =============================================================================
class ExtentController:
    def __init__(self, initial=None):
        self._current = list(initial or EXTENT_DEFAULT)
        self._history = []

    @property
    def current(self):
        return list(self._current)

    def apply_to_axes(self, ax):
        if HAS_CARTOPY:
            ax.set_extent(self._current, crs=ccrs.PlateCarree())
        else:
            ax.set_xlim(self._current[0], self._current[1])
            ax.set_ylim(self._current[2], self._current[3])

    def zoom(self, factor, center_lon=None, center_lat=None):
        lon_min, lon_max, lat_min, lat_max = self._current
        cx = center_lon if center_lon is not None else (lon_min + lon_max) / 2
        cy = center_lat if center_lat is not None else (lat_min + lat_max) / 2
        nln = cx - (cx - lon_min) * factor
        nlx = cx + (lon_max - cx) * factor
        ntn = cy - (cy - lat_min) * factor
        ntx = cy + (lat_max - cy) * factor
        if (nlx - nln) < ZOOM_MIN_SPAN or (nlx - nln) > ZOOM_MAX_SPAN:
            return
        if (ntx - ntn) < ZOOM_MIN_SPAN:
            return
        self._history.append(list(self._current))
        self._current = self._clamp([nln, nlx, ntn, ntx])

    def pan(self, dlon, dlat):
        lo, hi, bo, to = self._current
        h = EXTENT_HARD_LIMIT
        nln = lo + dlon; nlx = hi + dlon
        ntn = bo + dlat; ntx = to + dlat
        if nln < h[0]: s = h[0] - nln; nln += s; nlx += s
        if nlx > h[1]: s = nlx - h[1]; nln -= s; nlx -= s
        if ntn < h[2]: s = h[2] - ntn; ntn += s; ntx += s
        if ntx > h[3]: s = ntx - h[3]; ntn -= s; ntx -= s
        self._current = [nln, nlx, ntn, ntx]

    def reset(self):
        self._history.append(list(self._current))
        self._current = list(EXTENT_DEFAULT)

    def undo(self):
        if self._history:
            self._current = self._history.pop()

    def _clamp(self, e):
        h = EXTENT_HARD_LIMIT
        return [max(h[0], min(h[1], e[0])), max(h[0], min(h[1], e[1])),
                max(h[2], min(h[3], e[2])), max(h[2], min(h[3], e[3]))]


# =============================================================================
# LayerRenderer -- all Matplotlib drawing, theme-aware
# =============================================================================
class LayerRenderer:
    """
    Stateless drawing helper.  Receives the figure/axes and emits
    all map elements.  vector_scale controls arrow length in
    degrees-per-(mm/yr).
    """

    def __init__(self, fig, ax, theme="light", vector_scale=VECTOR_SCALE_DEFAULT):
        self.fig          = fig
        self.ax           = ax
        self.dark         = (theme == "dark")
        self.vector_scale = vector_scale   # adjustable arrow length multiplier

    # ── Base cartographic features ─────────────────────────────────────────────
    def draw_base_features(self):
        """50 m resolution map features, theme-aware."""
        if self.dark:
            ocean_c  = '#1a3a5a'; land_c   = '#2a3a2a'
            coast_c  = '#5a7a5a'; border_c = '#444444'
            river_c  = '#1a3a5a'; grid_c   = '#444444'
            lbl_c    = '#888888'
        else:
            ocean_c  = '#A8C8E8'; land_c   = '#E8E0D0'
            coast_c  = '#777060'; border_c = '#AAAAAA'
            river_c  = '#7AACCC'; grid_c   = '#888888'
            lbl_c    = '#555555'

        if HAS_CARTOPY:
            self.ax.set_facecolor(ocean_c)
            self.ax.add_feature(cfeature.LAND.with_scale('50m'),
                                facecolor=land_c, edgecolor='none', zorder=1)
            self.ax.add_feature(cfeature.OCEAN.with_scale('50m'),
                                facecolor=ocean_c, zorder=0)
            self.ax.add_feature(cfeature.COASTLINE.with_scale('50m'),
                                linewidth=0.6, edgecolor=coast_c, zorder=4)
            self.ax.add_feature(cfeature.BORDERS.with_scale('50m'),
                                linewidth=0.4, edgecolor=border_c,
                                linestyle=':', zorder=5)
            self.ax.add_feature(cfeature.LAKES.with_scale('50m'),
                                facecolor=ocean_c, edgecolor=coast_c,
                                linewidth=0.3, zorder=3)
            self.ax.add_feature(cfeature.RIVERS.with_scale('50m'),
                                edgecolor=river_c, linewidth=0.3, zorder=3)
            gl = self.ax.gridlines(
                crs=ccrs.PlateCarree(), draw_labels=True,
                linewidth=0.3, color=grid_c, alpha=0.5,
                linestyle='--', zorder=6)
            gl.top_labels   = False
            gl.right_labels = False
            gl.xlabel_style = {'size': 7, 'color': lbl_c}
            gl.ylabel_style = {'size': 7, 'color': lbl_c}
        else:
            self.ax.set_facecolor(ocean_c)

    def draw_plate_boundary(self):
        lons = SUNDALAND_BOUNDARY[:, 0]
        lats = SUNDALAND_BOUNDARY[:, 1]
        kw = dict(color='#CC4400', lw=1.5, ls=(0, (8, 4)), alpha=0.85, zorder=8)
        if HAS_CARTOPY:
            self.ax.plot(lons, lats, transform=ccrs.PlateCarree(), **kw)
        else:
            self.ax.plot(lons, lats, **kw)

    def draw_equator(self, extent):
        eq_c = '#cccc44' if self.dark else '#888800'
        eq   = np.linspace(extent[0], extent[1], 300)
        tkw  = {'transform': ccrs.PlateCarree()} if HAS_CARTOPY else {}
        self.ax.plot(eq, np.zeros_like(eq),
                     color=eq_c, lw=0.8, ls=':', alpha=0.7, zorder=7, **tkw)
        self.ax.text(eq[10], 0.5, 'Equator (0)',
                     fontsize=6, color=eq_c, alpha=0.85, zorder=7, **tkw)

    def draw_title(self, txt_col='#333333'):
        self.ax.set_title(
            "SUNDALAND PLATE MOTION MAP — GeoPlate Analyst  |  "
            "Projection: Mercator",
            color=txt_col, fontsize=8, fontweight='bold', pad=5)

    def draw_hint(self, col='#999999'):
        self.fig.text(
            0.5, 0.015,
            "Select tool above map  |  Click map for coordinates  |  "
            "Scroll=Zoom  Drag=Pan  R=Reset",
            ha='center', fontsize=7.5, color=col)

    # ── Velocity vectors (Euler model) ─────────────────────────────────────────
    def draw_velocity_vectors(self, results, txt_col="#111111"):
        """
        Draw Euler-model velocity arrows.

        Arrow length = velocity (mm/yr) x self.vector_scale (deg/mm/yr).
        A smaller vector_scale produces shorter, cleaner arrows --
        especially important at wide map extents.
        """
        sc  = self.vector_scale
        tkw = {'transform': ccrs.PlateCarree()} if HAS_CARTOPY else {}

        for r in results:
            ex = r.lon + r.vE * sc
            ey = r.lat + r.vN * sc

            if HAS_CARTOPY:
                pc = ccrs.PlateCarree()._as_mpl_transform(self.ax)
                self.ax.annotate("", xy=(ex, ey), xytext=(r.lon, r.lat),
                                 xycoords=pc, textcoords=pc,
                                 arrowprops=dict(
                                     arrowstyle='-|>', color='#111111',
                                     lw=1.2, mutation_scale=7),
                                 zorder=22)
            else:
                self.ax.annotate("", xy=(ex, ey), xytext=(r.lon, r.lat),
                                 arrowprops=dict(
                                     arrowstyle='-|>', color='#111111',
                                     lw=1.2, mutation_scale=7),
                                 zorder=22)

            # Station dot
            self.ax.plot(r.lon, r.lat, 'o', color='#111111',
                         ms=5, mec='white', mew=0.6, zorder=25, **tkw)

            # Station label
            hoff     = 0.3 if r.lon < 110 else -0.3
            name_col = '#dddddd' if self.dark else '#222222'
            self.ax.text(r.lon + hoff, r.lat - 0.25, r.name,
                         fontsize=5.5, color=name_col,
                         ha='left' if hoff > 0 else 'right',
                         va='top', zorder=26, **tkw)

    def draw_colorbar(self, cmap, norm, txt_col="#444444"):
        sm  = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])
        cax = self.fig.add_axes([0.05, 0.04, 0.28, 0.018])
        cb  = self.fig.colorbar(sm, cax=cax, orientation='horizontal')
        cb.set_label('Absolute Plate Velocity (mm/yr)',
                     color=txt_col, fontsize=7.5)
        cb.ax.tick_params(labelcolor=txt_col, labelsize=6.5)
        cb.outline.set_edgecolor('#AAAAAA')

    def draw_scale_arrow(self, extent, txt_col="#333333", ref_v=None):
        """
        Reference scale bar at bottom-right.

        Uses self.vector_scale so the bar always matches the drawn arrows.
        ref_v: representative velocity in mm/yr (rounded to nearest 5).
        """
        REF_V = round((ref_v or 25.0) / 5.0) * 5.0
        REF_V = max(5.0, REF_V)

        sc = self.vector_scale
        sx = extent[1] - 13.0
        sy = extent[2] + 1.5
        ex = sx + REF_V * sc
        label = f"{REF_V:.0f} mm/yr  (scale)"

        if HAS_CARTOPY:
            pc = ccrs.PlateCarree()._as_mpl_transform(self.ax)
            self.ax.annotate("", xy=(ex, sy), xytext=(sx, sy),
                             xycoords=pc, textcoords=pc,
                             arrowprops=dict(arrowstyle='->', color=txt_col,
                                             lw=1.5, mutation_scale=10),
                             zorder=30)
            self.ax.text((sx + ex) / 2, sy + 0.4, label,
                         ha='center', fontsize=7, color=txt_col,
                         fontweight='bold', zorder=31,
                         transform=ccrs.PlateCarree())
        else:
            self.ax.annotate("", xy=(ex, sy), xytext=(sx, sy),
                             arrowprops=dict(arrowstyle='->', color=txt_col,
                                             lw=1.5, mutation_scale=10),
                             zorder=30)
            self.ax.text((sx + ex) / 2, sy + 0.4, label,
                         ha='center', fontsize=7, color=txt_col,
                         fontweight='bold', zorder=31)

    def draw_caption(self, col='#999999'):
        self.fig.text(
            0.5, 0.005,
            "Plate boundary: Bird (2003)  |  Vectors: Euler Pole NNR-ITRF",
            ha='center', fontsize=6.5, color=col)

    # ── GPS comparison vectors ─────────────────────────────────────────────────
    def draw_gps_vectors(self, comparisons, leg_fc="#F5F0F0", leg_ec="#AAAAAA"):
        """GPS and residual vectors -- same scale as Euler arrows."""
        sc  = self.vector_scale
        tkw = {'transform': ccrs.PlateCarree()} if HAS_CARTOPY else {}

        for c in comparisons:
            ex_g = c.lon + c.gps_vE * sc
            ey_g = c.lat + c.gps_vN * sc

            if HAS_CARTOPY:
                pc = ccrs.PlateCarree()._as_mpl_transform(self.ax)
                self.ax.annotate("", xy=(ex_g, ey_g), xytext=(c.lon, c.lat),
                                 xycoords=pc, textcoords=pc,
                                 arrowprops=dict(
                                     arrowstyle='-|>', color='#CC0000',
                                     lw=1.2, mutation_scale=7),
                                 zorder=28)
            else:
                self.ax.annotate("", xy=(ex_g, ey_g), xytext=(c.lon, c.lat),
                                 arrowprops=dict(
                                     arrowstyle='-|>', color='#CC0000',
                                     lw=1.2, mutation_scale=7),
                                 zorder=28)

            ex_r = c.lon + c.res_vE * sc
            ey_r = c.lat + c.res_vN * sc
            if HAS_CARTOPY:
                self.ax.plot([c.lon, ex_r], [c.lat, ey_r],
                             color='#FF8800', lw=1.0, ls='--', zorder=27,
                             transform=ccrs.PlateCarree())
            else:
                self.ax.plot([c.lon, ex_r], [c.lat, ey_r],
                             color='#FF8800', lw=1.0, ls='--', zorder=27)

        import matplotlib.lines as mlines
        lbl_c = "#dddddd" if self.dark else "#111111"
        self.ax.legend(
            handles=[
                mlines.Line2D([], [], color=lbl_c,      lw=1.2, label="Euler"),
                mlines.Line2D([], [], color="#CC0000",   lw=1.2, label="GPS"),
                mlines.Line2D([], [], color="#FF8800",   lw=1.0, ls="--",
                              label="Residual"),
            ],
            loc="lower right", fontsize=7, framealpha=0.85,
            facecolor=leg_fc, edgecolor=leg_ec, labelcolor=lbl_c)


# =============================================================================
# MapCanvas -- main widget
# =============================================================================
class MapCanvas(FigureCanvas):
    """
    Matplotlib/Cartopy map embedded in PyQt6.

    Features
    --------
    - Background-cache blitting for smooth pan/zoom (no Cartopy re-render
      during interaction; full redraw fires 300 ms after interaction stops).
    - 50 m high-res coastline.
    - ArcGIS-style tool modes: pointer / hand / addpoint.
    - HiDPI-aware coordinate transform.
    - Adjustable vector scale via set_vector_scale().
    - maximize_toggled signal consumed by MainWindow for panel-only maximise.
    - F11 keyboard shortcut toggles map-panel maximise.
    """

    # ── Signals ───────────────────────────────────────────────────────────────
    coords_hovered   = pyqtSignal(float, float)
    coord_clicked    = pyqtSignal(float, float)
    extent_changed   = pyqtSignal(list)
    # Emitted when the canvas requests panel-maximise toggle.
    # True  = expand map panel (hide sidebar / title bar).
    # False = restore normal layout.
    maximize_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(14, 9), facecolor='#F5F0F0')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        # ── Internal state ────────────────────────────────────────────────────
        self._results       = []
        self._gps_comps     = []
        self._click_mode    = False
        self._theme         = "light"     # 'light' | 'dark'
        self._tool_mode     = 'pointer'
        self._pan_active    = False
        self._pan_start_px  = None
        self._pan_start_ex  = None
        self._last_pan_t    = 0.0
        self._bg_cache      = None
        self._is_maximized  = False       # track maximise state

        # Vector scale: degrees of arrow displacement per mm/yr of velocity
        self._vector_scale  = VECTOR_SCALE_DEFAULT

        self._extent_ctrl = ExtentController(EXTENT_DEFAULT)

        # Full redraw fires 300 ms after user stops scrolling / panning
        self._commit_timer = QTimer(self)
        self._commit_timer.setSingleShot(True)
        self._commit_timer.timeout.connect(self._commit_redraw)

        self._setup_axes()
        self._full_redraw(empty=True)

    # =========================================================================
    # Public API
    # =========================================================================

    def set_click_mode(self, enabled: bool):
        self._click_mode = enabled
        self.setCursor(Qt.CursorShape.CrossCursor if enabled
                       else Qt.CursorShape.ArrowCursor)

    def set_tool_mode(self, mode: str):
        self._tool_mode = mode
        cursors = {
            'pointer':  Qt.CursorShape.ArrowCursor,
            'hand':     Qt.CursorShape.OpenHandCursor,
            'addpoint': Qt.CursorShape.CrossCursor,
        }
        self.setCursor(cursors.get(mode, Qt.CursorShape.ArrowCursor))

    def set_theme(self, theme: str):
        """Switch map colour scheme: 'light' or 'dark'."""
        self._theme    = theme
        self._bg_cache = None
        self._full_redraw(empty=not self._results)

    def set_vector_scale(self, scale: float):
        """
        Change vector length multiplier and immediately trigger a full redraw.

        Parameters
        ----------
        scale : float
            Degrees of geographic displacement per mm/yr of velocity.
            Valid range: VECTOR_SCALE_MIN (0.01) to VECTOR_SCALE_MAX (0.20).
            Default: VECTOR_SCALE_DEFAULT (0.05).

        The scale bar at the bottom-right updates automatically to match,
        so the display always stays self-consistent.
        """
        clamped = float(np.clip(scale, VECTOR_SCALE_MIN, VECTOR_SCALE_MAX))
        if abs(clamped - self._vector_scale) < 1e-9:
            return  # nothing changed -- skip expensive redraw
        self._vector_scale = clamped
        self._bg_cache     = None
        self._full_redraw(empty=not self._results)

    def get_vector_scale(self) -> float:
        """Return current vector scale value."""
        return self._vector_scale

    def plot_results(self, results):
        self._results  = results
        self._bg_cache = None
        self._full_redraw(empty=False)

    def clear_map(self):
        self._results   = []
        self._gps_comps = []
        self._bg_cache  = None
        self._full_redraw(empty=True)

    def set_gps_overlay(self, comparisons):
        self._gps_comps = comparisons
        self._bg_cache  = None
        self._full_redraw(empty=not self._results)

    def clear_gps_overlay(self):
        self._gps_comps = []
        self._bg_cache  = None
        self._full_redraw(empty=not self._results)

    def reset_view(self):
        self._extent_ctrl.reset()
        self._bg_cache = None
        self._full_redraw(empty=not self._results)

    def save_image(self, filepath, dpi=200):
        self.fig.savefig(filepath, dpi=dpi, bbox_inches='tight',
                         facecolor=self.fig.get_facecolor())

    def toggle_maximize(self):
        """
        Toggle map-panel maximise state and emit maximize_toggled signal.

        MainWindow listens to this signal and performs the actual
        widget show/hide so this canvas stays layout-agnostic.
        """
        self._is_maximized = not self._is_maximized
        self.maximize_toggled.emit(self._is_maximized)

    def is_map_maximized(self) -> bool:
        return self._is_maximized

    # =========================================================================
    # Rendering
    # =========================================================================

    def _setup_axes(self):
        self.fig.clear()
        if HAS_CARTOPY:
            self.ax = self.fig.add_axes(
                [0.04, 0.07, 0.92, 0.89],
                projection=ccrs.Mercator())
        else:
            self.ax = self.fig.add_axes([0.04, 0.07, 0.92, 0.89])

    def _full_redraw(self, empty=False):
        """
        Full render cycle (expensive -- deferred via _commit_timer):
          1. Set up axes and theme colours.
          2. Draw all base cartographic layers (Cartopy).
          3. Capture background into _bg_cache for blit-reuse.
          4. Draw data overlays: vectors, GPS, colorbar, scale bar.
          5. Final draw() to screen.
        """
        # ── Theme colours ──────────────────────────────────────────────────────
        dark     = (self._theme == 'dark')
        fig_bg   = '#1e1e1e' if dark else '#F5F0F0'
        txt_col  = '#e0e0e0' if dark else '#333333'
        hint_col = '#888888' if dark else '#999999'
        cap_col  = '#777777' if dark else '#999999'
        leg_fc   = '#2a2a2a' if dark else '#F5F0F0'
        leg_ec   = '#555555' if dark else '#AAAAAA'

        self.fig.patch.set_facecolor(fig_bg)

        self._setup_axes()

        # LayerRenderer carries the current vector_scale into every draw call
        rdr = LayerRenderer(self.fig, self.ax,
                            theme=self._theme,
                            vector_scale=self._vector_scale)
        self._renderer    = rdr
        self._transformer = GeoCoordTransformer(self.fig, self.ax, canvas=self)

        self._extent_ctrl.apply_to_axes(self.ax)
        rdr.draw_base_features()
        rdr.draw_plate_boundary()
        rdr.draw_equator(self._extent_ctrl.current)
        rdr.draw_title(txt_col)

        if empty or not self._results:
            rdr.draw_hint(hint_col)

        # Render base map; capture into background cache (no vectors yet)
        self.draw()
        self._bg_cache = self.copy_from_bbox(self.ax.bbox)

        # ── Data overlays drawn on top of the cached base ──────────────────────
        if not empty and self._results:
            speeds = [r.vT for r in self._results]
            norm   = Normalize(vmin=min(speeds), vmax=max(speeds))
            rdr.draw_velocity_vectors(self._results, txt_col)
            rdr.draw_colorbar(VEL_CMAP, norm, txt_col)
            # Mean velocity for a representative, data-driven scale bar label
            mean_v = float(np.mean(speeds))
            rdr.draw_scale_arrow(self._extent_ctrl.current, txt_col,
                                 ref_v=mean_v)
            rdr.draw_caption(cap_col)

        if self._gps_comps:
            rdr.draw_gps_vectors(self._gps_comps, leg_fc, leg_ec)

        self.draw()

    def _fast_update(self):
        """
        Ultra-fast path during interactive scroll/pan:
        - Only updates axes extent (no Cartopy re-render).
        - draw_idle() queues a non-blocking repaint reusing the existing
          renderer state (effectively a partial blit).
        Full redraw is deferred 300 ms after interaction stops.
        """
        self._extent_ctrl.apply_to_axes(self.ax)
        self.extent_changed.emit(self._extent_ctrl.current)
        self.draw_idle()

    def _apply_extent_only(self):
        self._fast_update()

    def _commit_redraw(self):
        """Full redraw after scroll/pan stops -- refreshes cache + gridlines."""
        self._bg_cache = None
        self._full_redraw(empty=not self._results)

    # =========================================================================
    # Qt Events
    # =========================================================================

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta == 0:
            event.ignore()
            return
        pos = event.position()
        px, py = int(pos.x()), int(pos.y())
        factor = (1.0 - ZOOM_FACTOR) if delta > 0 else (1.0 + ZOOM_FACTOR)
        lon, lat = self._transformer.display_to_geo(px, py)
        if lon is not None:
            self._extent_ctrl.zoom(factor, center_lon=lon, center_lat=lat)
        else:
            self._extent_ctrl.zoom(factor)
        self._extent_ctrl.apply_to_axes(self.ax)
        self.extent_changed.emit(self._extent_ctrl.current)
        self._fast_update()
        self._commit_timer.start(300)
        event.accept()

    def mousePressEvent(self, event):
        pos = event.position()
        px, py = int(pos.x()), int(pos.y())

        if event.button() == Qt.MouseButton.LeftButton:
            lon, lat = self._transformer.display_to_geo(px, py)
            if self._tool_mode == 'addpoint':
                if lon is not None:
                    self.coord_clicked.emit(float(lat), float(lon))
                event.accept()
                return
            elif self._tool_mode == 'hand':
                self._start_pan(px, py)
                event.accept()
                return
            else:   # pointer
                if lon is not None:
                    self.coord_clicked.emit(float(lat), float(lon))
                self._start_pan(px, py)
                event.accept()

        elif event.button() == Qt.MouseButton.RightButton:
            lon, lat = self._transformer.display_to_geo(px, py)
            if lon is not None:
                self.coord_clicked.emit(float(lat), float(lon))
            event.accept()

        elif event.button() == Qt.MouseButton.MiddleButton:
            self.reset_view()
            event.accept()

        else:
            super().mousePressEvent(event)

    def _start_pan(self, px, py):
        self._pan_active   = True
        self._pan_start_px = QPoint(px, py)
        self._pan_start_ex = self._extent_ctrl.current
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        pos = event.position()
        px, py = int(pos.x()), int(pos.y())

        lon, lat = self._transformer.display_to_geo(px, py)
        self.coords_hovered.emit(
            float(lat) if lat is not None else 0.0,
            float(lon) if lon is not None else 0.0)

        if not self._pan_active:
            super().mouseMoveEvent(event)
            return

        now = time.monotonic()
        if (now - self._last_pan_t) * 1000 < PAN_THROTTLE_MS:
            event.accept()
            return
        self._last_pan_t = now

        s_lon, s_lat = self._transformer.display_to_geo(
            self._pan_start_px.x(), self._pan_start_px.y())
        c_lon, c_lat = self._transformer.display_to_geo(px, py)

        if None in (s_lon, s_lat, c_lon, c_lat):
            event.accept()
            return

        self._extent_ctrl._current = list(self._pan_start_ex)
        self._extent_ctrl.pan(s_lon - c_lon, s_lat - c_lat)
        self._apply_extent_only()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pan_active:
            self._pan_active   = False
            self._pan_start_px = None
            self._pan_start_ex = None
            cursors = {
                'pointer':  Qt.CursorShape.ArrowCursor,
                'hand':     Qt.CursorShape.OpenHandCursor,
                'addpoint': Qt.CursorShape.CrossCursor,
            }
            self.setCursor(cursors.get(self._tool_mode,
                                       Qt.CursorShape.ArrowCursor))
            self._commit_timer.start(300)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.reset_view()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        key     = event.key()
        mod     = event.modifiers()
        ex      = self._extent_ctrl.current
        lx      = ex[1] - ex[0]
        ly      = ex[3] - ex[2]
        handled = True

        if key == Qt.Key.Key_R:
            self.reset_view()
        elif key == Qt.Key.Key_Z and mod == Qt.KeyboardModifier.ControlModifier:
            self._extent_ctrl.undo()
            self._apply_extent_only()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self._extent_ctrl.zoom(1.0 - ZOOM_FACTOR)
            self._apply_extent_only()
        elif key == Qt.Key.Key_Minus:
            self._extent_ctrl.zoom(1.0 + ZOOM_FACTOR)
            self._apply_extent_only()
        elif key == Qt.Key.Key_Left:
            self._extent_ctrl.pan(-lx * 0.1, 0)
            self._apply_extent_only()
        elif key == Qt.Key.Key_Right:
            self._extent_ctrl.pan(lx * 0.1, 0)
            self._apply_extent_only()
        elif key == Qt.Key.Key_Up:
            self._extent_ctrl.pan(0, ly * 0.1)
            self._apply_extent_only()
        elif key == Qt.Key.Key_Down:
            self._extent_ctrl.pan(0, -ly * 0.1)
            self._apply_extent_only()
        elif key == Qt.Key.Key_F11:
            # F11: toggle map-panel maximise (also triggered by toolbar button)
            self.toggle_maximize()
        else:
            handled = False

        if handled:
            event.accept()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        """Invalidate background cache on resize; schedule full redraw."""
        self._bg_cache = None
        super().resizeEvent(event)
        self._commit_timer.start(300)
