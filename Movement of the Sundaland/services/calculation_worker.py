"""
services/calculation_worker.py
Background worker untuk kalkulasi kecepatan lempeng.

PERBAIKAN:
- Menggunakan wx/wy/wz langsung (Cara 1, lebih akurat) bukan lat/lon/omega
- ORB (Origin Rate Bias) selalu diterapkan sesuai Altamimi (2023)
- finished signal selalu di-emit (finally block) untuk re-enable UI
- Guard abort sebelum emit result_ready (FIX-13)
"""

import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal

from core.constants  import EULER_POLE, ITRF2020_PMM, ADDITIONAL_PLATES
from core.euler_engine import compute_plate_velocity
from models.data_models import ObservationPoint, PlateVelocity


class CalculationWorker(QThread):
    progress     = pyqtSignal(int, int)     # current, total
    result_ready = pyqtSignal(list)         # List[PlateVelocity]
    error        = pyqtSignal(str)
    finished     = pyqtSignal()             # always emitted at end

    def __init__(
        self,
        points   : list,
        # ── Cara 1: wx/wy/wz langsung dari ITRF2020-PMM (DIREKOMENDASIKAN) ──
        wx_mas   : float = None,
        wy_mas   : float = None,
        wz_mas   : float = None,
        # ── Cara 2: lat/lon/omega (kompatibilitas dialog lama) ───────────────
        ep_lat   : float = None,
        ep_lon   : float = None,
        omega    : float = None,
        apply_orb: bool  = True,
        parent   = None,
    ):
        super().__init__(parent)
        self.points    = points
        self.apply_orb = apply_orb
        self._abort    = False

        # Prioritas: wx/wy/wz → lat/lon/omega → default SUND
        if wx_mas is not None and wy_mas is not None and wz_mas is not None:
            # Cara 1 — langsung dari wx/wy/wz
            self.wx_mas = wx_mas
            self.wy_mas = wy_mas
            self.wz_mas = wz_mas
            self._use_wxyz = True
        elif ep_lat is not None and ep_lon is not None and omega is not None:
            # Cara 2 — konversi ke wx/wy/wz agar konsisten
            # omega °/Ma → rad/yr → wx/wy/wz mas/yr
            from core.constants import DEG2RAD, MAS_YR_TO_RAD_YR
            omega_rad_yr = omega * DEG2RAD / 1e6
            lat_r = ep_lat * DEG2RAD
            lon_r = ep_lon * DEG2RAD
            omega_vec = omega_rad_yr * np.array([
                np.cos(lat_r) * np.cos(lon_r),
                np.cos(lat_r) * np.sin(lon_r),
                np.sin(lat_r),
            ])
            # rad/yr → mas/yr
            self.wx_mas = float(omega_vec[0] / MAS_YR_TO_RAD_YR)
            self.wy_mas = float(omega_vec[1] / MAS_YR_TO_RAD_YR)
            self.wz_mas = float(omega_vec[2] / MAS_YR_TO_RAD_YR)
            self._use_wxyz = True
        else:
            # Default — EURA dari ITRF2020-PMM (resmi)
            # Untuk Sundaland gunakan SUND_S07 atau SUND_A24 dari dialog
            eura = ITRF2020_PMM['EURA']
            self.wx_mas = eura['wx']
            self.wy_mas = eura['wy']
            self.wz_mas = eura['wz']
            self._use_wxyz = True

    def abort(self):
        self._abort = True

    def run(self):
        results = []
        try:
            total = len(self.points)
            for i, pt in enumerate(self.points):
                if self._abort:
                    break
                r = compute_plate_velocity(
                    pt.lat, pt.lon,
                    wx_mas=self.wx_mas,
                    wy_mas=self.wy_mas,
                    wz_mas=self.wz_mas,
                    apply_orb=self.apply_orb,
                )
                results.append(PlateVelocity(
                    name    = pt.name,
                    lat     = pt.lat,
                    lon     = pt.lon,
                    vN      = r['vN'],
                    vE      = r['vE'],
                    vT      = r['vT'],
                    azimuth = r['azimuth'],
                    compass = r['compass'],
                ))
                self.progress.emit(i + 1, total)

            # FIX-13: Hanya emit result jika tidak di-abort
            if not self._abort:
                self.result_ready.emit(results)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()
