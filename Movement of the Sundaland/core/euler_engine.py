"""
core/euler_engine.py
Euler Pole plate velocity calculation — ITRF2020 framework.

Referensi:
  Altamimi, Z. et al. (2023). ITRF2020 plate motion model.
  Journal of Geodesy, 97(5), 48.
  https://doi.org/10.1007/s00190-023-01737-x

Alur perhitungan (per titik):
  1. wx/wy/wz (mas/yr) dari ITRF2020-PMM → ω vektor (rad/yr) via wxyz_to_pole()
  2. Titik koordinat (lat,lon) → ECEF r (km)
  3. v_ECEF = ω × r  (cross product, mm/yr)
  4. Terapkan ORB (Origin Rate Bias): v += [Tx, Ty, Tz] (mm/yr)
  5. Proyeksi v_ECEF ke komponen toposentrik North (vN) dan East (vE)
"""

import numpy as np
from .constants import (
    EARTH_R, DEG2RAD, RAD2DEG,
    EULER_POLE, ORB, ITRF2020_PMM, ADDITIONAL_PLATES,
    get_plate_pole, wxyz_to_pole,
    MAS_YR_TO_RAD_YR,
)


# ── ECEF Helpers ──────────────────────────────────────────────────────────────

def geo_to_ecef(lat_deg: float, lon_deg: float) -> np.ndarray:
    """
    Konversi koordinat geografis (lat, lon) → vektor posisi ECEF (km).
    Menggunakan bola sempurna radius EARTH_R.
    """
    lat = lat_deg * DEG2RAD
    lon = lon_deg * DEG2RAD
    return EARTH_R * np.array([
        np.cos(lat) * np.cos(lon),
        np.cos(lat) * np.sin(lon),
        np.sin(lat),
    ])


def omega_vector_from_wxyz(wx_mas: float,
                            wy_mas: float,
                            wz_mas: float) -> np.ndarray:
    """
    Konversi komponen rotasi wx/wy/wz (mas/yr) → vektor ω (rad/yr) ECEF.

    1 mas/yr = (π / 648 000 000) rad/yr  = MAS_YR_TO_RAD_YR
    """
    scale = MAS_YR_TO_RAD_YR
    return np.array([wx_mas * scale,
                     wy_mas * scale,
                     wz_mas * scale])


def topo_unit_vectors(lat_deg: float,
                      lon_deg: float) -> tuple:
    """
    Vektor satuan toposentrik North dan East di titik (lat, lon).

    North : -sin(lat)cos(lon), -sin(lat)sin(lon),  cos(lat)
    East  : -sin(lon),          cos(lon),            0
    """
    lat = lat_deg * DEG2RAD
    lon = lon_deg * DEG2RAD
    north = np.array([
        -np.sin(lat) * np.cos(lon),
        -np.sin(lat) * np.sin(lon),
         np.cos(lat),
    ])
    east = np.array([-np.sin(lon), np.cos(lon), 0.0])
    return north, east


# ── Main Velocity Function ────────────────────────────────────────────────────

def compute_plate_velocity(
    pt_lat : float,
    pt_lon : float,
    ep_lat : float = None,
    ep_lon : float = None,
    omega  : float = None,
    wx_mas : float = None,
    wy_mas : float = None,
    wz_mas : float = None,
    apply_orb: bool = True,
) -> dict:
    """
    Hitung kecepatan lempeng Sundaland di titik koordinat tertentu.

    CARA 1 — Dari wx/wy/wz (DIREKOMENDASIKAN, lebih akurat):
        compute_plate_velocity(-3.80, 102.27,
                               wx_mas=0.461, wy_mas=-0.547, wz_mas=0.948)

    CARA 2 — Dari lat/lon/omega (kompatibilitas dengan dialog lama):
        compute_plate_velocity(-3.80, 102.27,
                               ep_lat=55.07, ep_lon=-49.92, omega=0.287)

    Jika tidak ada parameter tambahan, digunakan default EULER_POLE
    dari ITRF2020-PMM (SUND) di constants.py.

    Parameter
    ---------
    pt_lat, pt_lon : koordinat titik pengamatan (derajat)
    wx_mas, wy_mas, wz_mas : komponen rotasi lempeng (mas/yr) — Cara 1
    ep_lat, ep_lon, omega  : Euler Pole lat/lon/omega (°, °, °/Ma) — Cara 2
    apply_orb : bool — terapkan Origin Rate Bias (default True, sesuai Altamimi 2023)

    Returns
    -------
    dict: vN, vE, vT (mm/yr), azimuth (°), compass (str)
    """

    # ── Tentukan ω vektor ─────────────────────────────────────────────────────
    if wx_mas is not None and wy_mas is not None and wz_mas is not None:
        # Cara 1: langsung dari wx/wy/wz mas/yr (ITRF2020-PMM)
        omega_vec = omega_vector_from_wxyz(wx_mas, wy_mas, wz_mas)

    elif ep_lat is not None and ep_lon is not None and omega is not None:
        # Cara 2: konversi lat/lon/omega ke wx/wy/wz
        # lon bisa dalam konvensi 0-360° atau -180/+180° — normalkan ke -180/+180°
        lon_norm = ((ep_lon + 180) % 360) - 180   # pastikan -180 s/d +180
        omega_rad_yr = omega * DEG2RAD / 1.0e6
        lat_r = ep_lat * DEG2RAD
        lon_r = lon_norm * DEG2RAD
        omega_vec = omega_rad_yr * np.array([
            np.cos(lat_r) * np.cos(lon_r),
            np.cos(lat_r) * np.sin(lon_r),
            np.sin(lat_r),
        ])

    else:
        # Default: gunakan EURA dari ITRF2020-PMM (resmi per Altamimi 2023)
        # Sundaland tidak memiliki Euler Pole resmi — lihat constants.py
        pmm = ITRF2020_PMM['EURA']
        omega_vec = omega_vector_from_wxyz(
            pmm['wx'], pmm['wy'], pmm['wz'])

    # ── v_ECEF = ω × r ────────────────────────────────────────────────────────
    r     = geo_to_ecef(pt_lat, pt_lon)            # km
    v_xyz = np.cross(omega_vec, r) * 1.0e6         # mm/yr

    # ── Terapkan Origin Rate Bias (Altamimi 2023, Section 5) ─────────────────
    if apply_orb:
        # ORB diberikan dalam mm/yr, sesuai tanda konvensi ITRF
        orb_vec = np.array([ORB['Tx'], ORB['Ty'], ORB['Tz']])  # mm/yr
        v_xyz  = v_xyz + orb_vec

    # ── Proyeksi ke komponen toposentrik North dan East ───────────────────────
    north, east = topo_unit_vectors(pt_lat, pt_lon)

    vN = float(np.dot(v_xyz, north))
    vE = float(np.dot(v_xyz, east))
    vT = float(np.hypot(vN, vE))
    az = float(np.degrees(np.arctan2(vE, vN))) % 360.0

    return {
        'vN'     : vN,
        'vE'     : vE,
        'vT'     : vT,
        'azimuth': az,
        'compass': azimuth_to_compass(az),
    }


def compute_from_plate(pt_lat: float,
                       pt_lon: float,
                       plate_code: str = 'EURA',
                       apply_orb: bool = True) -> dict:
    """
    Hitung kecepatan untuk lempeng tertentu berdasarkan kode ITRF2020-PMM
    atau ADDITIONAL_PLATES (misal: SUND_S07, SUND_A24).

    Parameters
    ----------
    plate_code : kode lempeng (EURA, AUST, SUND_S07, SUND_A24, dll)
    """
    # Cari di ITRF2020_PMM dulu, lalu ADDITIONAL_PLATES
    all_plates = {**ITRF2020_PMM, **ADDITIONAL_PLATES}
    if plate_code not in all_plates:
        raise ValueError(
            f"Plate '{plate_code}' tidak ditemukan. "
            f"Tersedia: {list(all_plates.keys())}"
        )
    pmm = all_plates[plate_code]
    return compute_plate_velocity(
        pt_lat, pt_lon,
        wx_mas=pmm['wx'], wy_mas=pmm['wy'], wz_mas=pmm['wz'],
        apply_orb=apply_orb,
    )


def azimuth_to_compass(az: float) -> str:
    """Konversi azimuth desimal (0–360°) ke 16-titik kompas."""
    dirs = [
        'North', 'North-NorthEast', 'NorthEast', 'East-NorthEast',
        'East',  'East-SouthEast',  'SouthEast', 'South-SouthEast',
        'South', 'South-SouthWest', 'SouthWest', 'West-SouthWest',
        'West',  'West-NorthWest',  'NorthWest', 'North-NorthWest',
    ]
    return dirs[int((az + 11.25) / 22.5) % 16]


def batch_compute(points: list,
                  plate_code: str = 'EURA') -> list:
    """
    Hitung kecepatan untuk daftar titik [(name, lat, lon), ...].
    """
    return [compute_from_plate(lat, lon, plate_code)
            for _, lat, lon in points]
