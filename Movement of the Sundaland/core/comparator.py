"""
core/comparator.py
Compare Euler-predicted plate velocities with GPS satellite measurements.

Residual formula:
    residual_vN = vN_GPS  - vN_Euler
    residual_vE = vE_GPS  - vE_Euler
    residual_vT = sqrt(residual_vN² + residual_vE²)

A positive residual means GPS is faster than Euler prediction.
A negative residual means GPS is slower than Euler prediction.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Optional

from models.data_models import PlateVelocity
from services.gps_service import GPSPoint
from core.euler_engine import azimuth_to_compass


@dataclass
class ComparisonResult:
    """Full comparison for one matched point."""
    name: str
    lat:  float
    lon:  float

    # Euler-predicted
    euler_vN: float
    euler_vE: float
    euler_vT: float
    euler_az: float

    # GPS-measured
    gps_vN: float
    gps_vE: float
    gps_vT: float
    gps_az: float

    # Residual  (GPS − Euler)
    res_vN: float
    res_vE: float
    res_vT: float
    res_az: float        # azimuth of residual vector
    res_compass: str

    @property
    def agreement_pct(self) -> float:
        """
        How close GPS is to Euler prediction (100% = perfect match).
        Capped at 0–100 %.
        """
        if self.euler_vT == 0:
            return 0.0
        pct = (1.0 - self.res_vT / self.euler_vT) * 100.0
        return max(0.0, min(100.0, pct))

    @property
    def match_label(self) -> str:
        p = self.agreement_pct
        if p >= 90: return "Excellent"
        if p >= 75: return "Good"
        if p >= 50: return "Moderate"
        return "Poor"


def compare(
    euler_results: List[PlateVelocity],
    gps_points:    List[GPSPoint],
    max_dist_deg:  float = 0.5,
) -> tuple[List[ComparisonResult], List[str]]:
    """
    Match Euler results with GPS points by name (primary) or
    nearest location (fallback, within max_dist_deg).

    Returns
    -------
    (comparisons, warnings)
      comparisons : list of ComparisonResult for matched pairs
      warnings    : list of unmatched point names
    """
    comparisons: List[ComparisonResult] = []
    warnings:    List[str]              = []

    # Build name lookup for GPS
    gps_by_name = {g.name.lower(): g for g in gps_points}

    for e in euler_results:
        gps = gps_by_name.get(e.name.lower())

        # Fallback: nearest GPS point within tolerance
        # FIX #6: Gunakan koreksi cosine latitude agar jarak akurat di semua lintang.
        # Tanpa koreksi, 1° longitude di lintang tinggi dianggap sama jauhnya dengan
        # 1° longitude di equator, padahal sebenarnya jauh lebih pendek.
        if gps is None:
            best_dist = max_dist_deg
            for g in gps_points:
                dlat = g.lat - e.lat
                dlon = (g.lon - e.lon) * np.cos(np.radians(e.lat))
                d = np.hypot(dlat, dlon)
                if d < best_dist:
                    best_dist = d
                    gps = g

        if gps is None:
            warnings.append(
                f"No GPS match for '{e.name}' "
                f"(lat={e.lat:.3f}, lon={e.lon:.3f})"
            )
            continue

        # Residual  =  GPS  −  Euler
        res_vN = gps.vN - e.vN
        res_vE = gps.vE - e.vE
        res_vT = float(np.hypot(res_vN, res_vE))
        res_az = float(np.degrees(np.arctan2(res_vE, res_vN))) % 360.0

        comparisons.append(ComparisonResult(
            name     = e.name,
            lat      = e.lat,
            lon      = e.lon,
            euler_vN = e.vN,
            euler_vE = e.vE,
            euler_vT = e.vT,
            euler_az = e.azimuth,
            gps_vN   = gps.vN,
            gps_vE   = gps.vE,
            gps_vT   = gps.vT,
            gps_az   = gps.azimuth,
            res_vN   = res_vN,
            res_vE   = res_vE,
            res_vT   = res_vT,
            res_az   = res_az,
            res_compass = azimuth_to_compass(res_az),
        ))

    return comparisons, warnings


def summary_stats(comparisons: List[ComparisonResult]) -> dict:
    """Return basic statistics over all comparison results."""
    if not comparisons:
        return {}
    res_vTs = [c.res_vT for c in comparisons]
    return {
        'n':           len(comparisons),
        'mean_res_vT': float(np.mean(res_vTs)),
        'std_res_vT':  float(np.std(res_vTs)),
        'max_res_vT':  float(np.max(res_vTs)),
        'min_res_vT':  float(np.min(res_vTs)),
        'mean_agree':  float(np.mean([c.agreement_pct for c in comparisons])),
    }
