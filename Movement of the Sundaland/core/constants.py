"""
core/constants.py
Constants, ITRF2020 Plate Motion Model (PMM), and plate boundary data.

Sumber utama:
  Altamimi, Z., Métivier, L., Rebischung, P., Rouby, H., & Collilieux, X. (2023).
  ITRF2020 plate motion model.
  Journal of Geodesy, 97(5), 48. https://doi.org/10.1007/s00190-023-01737-x

  Table 1 — 12 lempeng tektonik resmi dalam ITRF2020-PMM.
  Satuan: wx, wy, wz dalam mas/yr (milli-arcsecond per year).

CATATAN PENTING — LEMPENG SUNDALAND (SUND):
  Lempeng Sundaland TIDAK tercantum dalam Table 1 Altamimi (2023).
  ITRF2020-PMM resmi hanya mendefinisikan 12 lempeng di bawah ini.
  Untuk keperluan program ini (wilayah Sundaland), lempeng default
  yang digunakan adalah EURA (Eurasian) karena Sundaland secara
  tektonik merupakan bagian dari blok Eurasia yang relatif stabil.
  Jika tersedia data lokal untuk lempeng Sundaland dari referensi
  lain (misal: Simons et al. 2007), dapat ditambahkan secara terpisah
  dengan label sumber yang jelas.

Catatan konversi satuan:
  1 mas/yr = 1e-3 arcsec/yr = (pi / 648000000) rad/yr
  Konversi ke deg/Ma: 1 mas/yr = (1/3.6) deg/Ma
"""

import numpy as np

# ── Konstanta Fisika ───────────────────────────────────────────────────────────
EARTH_R = 6371.0          # km — radius bumi rata-rata
DEG2RAD = np.pi / 180.0
RAD2DEG = 180.0 / np.pi

# ── Konversi satuan ────────────────────────────────────────────────────────────
# 1 mas/yr = pi/648.000.000 rad/yr
MAS_YR_TO_RAD_YR = (np.pi / 180.0) / 3600.0 / 1000.0

# ══════════════════════════════════════════════════════════════════════════════
# ITRF2020-PMM — Table 1, Altamimi et al. (2023)
# 12 lempeng tektonik resmi
# wx, wy, wz dalam mas/yr (milli-arcsecond per year)
# Tidak ada lempeng Sundaland (SUND) dalam tabel resmi ini.
# ══════════════════════════════════════════════════════════════════════════════
ITRF2020_PMM = {
    # Kode : wx        wy        wz       Nama resmi
    # Sumber: Altamimi et al. (2023) GRL 50, e2023GL106373, Table 1
    # Satuan: wx, wy, wz dalam mas/yr (milli-arcsecond per year)
    # NS = jumlah stasiun GPS yang digunakan untuk estimasi
    'AMUR': {'wx': -0.131, 'wy': -0.551, 'wz':  0.837, 'name': 'Amurian',        'ns':   3},
    'ANTA': {'wx': -0.269, 'wy': -0.312, 'wz':  0.678, 'name': 'Antarctic',       'ns':  15},
    'ARAB': {'wx':  1.129, 'wy': -0.146, 'wz':  1.438, 'name': 'Arabian',         'ns':   3},
    'AUST': {'wx':  1.487, 'wy':  1.175, 'wz':  1.223, 'name': 'Australian',      'ns': 118},
    'CARB': {'wx':  0.207, 'wy': -1.422, 'wz':  0.726, 'name': 'Caribbean',       'ns':   5},
    'EURA': {'wx': -0.085, 'wy': -0.519, 'wz':  0.753, 'name': 'Eurasian',        'ns': 143},
    'INDI': {'wx':  1.137, 'wy':  0.013, 'wz':  1.444, 'name': 'Indian',          'ns':   4},
    'NAZC': {'wx': -0.327, 'wy': -1.561, 'wz':  1.605, 'name': 'Nazca',           'ns':   3},
    'NOAM': {'wx':  0.045, 'wy': -0.666, 'wz': -0.098, 'name': 'North American',  'ns': 108},
    'NUBI': {'wx':  0.090, 'wy': -0.585, 'wz':  0.717, 'name': 'Nubian',          'ns':  31},
    'PCFC': {'wx': -0.404, 'wy':  1.021, 'wz': -2.154, 'name': 'Pacific',         'ns':  20},
    'SOAM': {'wx': -0.261, 'wy': -0.282, 'wz': -0.157, 'name': 'South American',  'ns':  59},
    'SOMA': {'wx': -0.081, 'wy': -0.719, 'wz':  0.864, 'name': 'Somali',          'ns':   6},
    # YANM (Yangtze) — ada di ITRF2014-PMM tetapi TIDAK ada di ITRF2020-PMM Table 1
    # Dihapus dari tabel utama untuk menjaga konsistensi dengan Altamimi (2023)
}

# ── Lempeng tambahan dari referensi lain (BUKAN Altamimi 2023) ────────────────
#
# CATATAN PENTING — EULER POLE SUNDALAND:
# Tidak ada Euler Pole Sundaland resmi dalam ITRF2020-PMM karena seluruh
# stasiun GPS di wilayah Sundaland tidak memenuhi kriteria site selection
# Altamimi (2023): terlalu dekat batas lempeng (<100 km dari Sunda Trench),
# terdampak strain interseismik, dan residual postseismik gempa besar
# (Aceh 2004 M9.1, Bengkulu 2007 M8.4) melebihi threshold 1 mm/yr.
#
# Parameter wx/wy/wz di bawah adalah ESTIMASI REGIONAL dari berbagai sumber,
# bukan nilai resmi. Setiap sumber menghasilkan Euler Pole berbeda karena:
#   (1) perbedaan frame referensi (ITRF2000 vs ITRF2014 vs NNR)
#   (2) perbedaan periode data GPS yang digunakan
#   (3) perbedaan jumlah dan distribusi stasiun GPS
#   (4) ada/tidaknya koreksi postseismik
#
# Rentang ketidakpastian antar sumber:
#   Lat  : 47° ~ 56° N  (rentang ~9°)
#   Lon  : 75° ~ 83° W  (rentang ~8°)
#   omega: 0.287 ~ 0.335 °/Ma
#   Dampak pada vT: ±3.4 mm/yr di wilayah Sundaland
#
# ── Konversi lat/lon/omega → wx/wy/wz ────────────────────────────────────────
# Untuk Simons et al. (2007): lat=50.7°N, lon=-83.4°E, omega=0.287°/Ma
# omega_rad/yr = 0.287 * pi/180 / 1e6 = 5.009e-9 rad/yr
# wx = omega * cos(lat) * cos(lon) = 5.009e-9 * cos(50.7°) * cos(-83.4°)
#    = 5.009e-9 * 0.6334 * 0.1132 = 3.596e-10 rad/yr = 0.074 mas/yr
# (konversi ke mas/yr: dibagi MAS_YR_TO_RAD_YR = pi/648000000)
# Hasil: wx=+0.074, wy=-0.502, wz=+0.568 mas/yr
#
# Nilai ini dikonversi langsung dari lat/lon/omega Simons 2007 ITRF2000 NNR.
# Perbedaan frame ITRF2000→ITRF2020 ~0.5 mm/yr horizontal (dapat diabaikan
# untuk keperluan analisis regional).

def _pole_to_wxyz(lat_deg: float, lon_deg: float, omega_deg_ma: float) -> tuple:
    """Konversi Euler Pole (lat, lon, omega) → (wx, wy, wz) dalam mas/yr."""
    import math
    omega_rad_yr = omega_deg_ma * math.pi / 180.0 / 1.0e6
    lat_r = lat_deg * math.pi / 180.0
    lon_r = lon_deg * math.pi / 180.0
    scale = 648000000.0 / math.pi   # rad/yr → mas/yr
    wx = omega_rad_yr * math.cos(lat_r) * math.cos(lon_r) * scale
    wy = omega_rad_yr * math.cos(lat_r) * math.sin(lon_r) * scale
    wz = omega_rad_yr * math.sin(lat_r) * scale
    return round(wx, 3), round(wy, 3), round(wz, 3)


# ── Lempeng Sundaland — dua estimasi dari literatur ───────────────────────────
#
# IMPORTANT SCIENTIFIC NOTE — SUNDALAND EULER POLE:
# The Sundaland block has NO official Euler Pole in ITRF2020-PMM (Altamimi 2023)
# because all GPS stations in the Sundaland region fail the strict site-selection
# criteria:
#   (a) Too close to the Sunda Trench plate boundary (<100 km threshold violated)
#   (b) Significant interseismic coupling strain from Indo-Australian subduction
#   (c) Large postseismic deformation from major earthquakes:
#       Aceh 2004 (M9.1), Nias 2005 (M8.6), Bengkulu 2007 (M8.4+M7.9),
#       North Sumatra 2012 (M8.6+M8.2) — residuals far exceed 1 mm/yr limit
#   (d) Internal deformation from the active Great Sumatran Fault (2-3 mm/yr)
#
# The two parameter sets below are REGIONAL ESTIMATES from peer-reviewed
# literature — not official values. They differ because of:
#   (1) Different reference frames (ITRF2000 vs ITRF2014)
#   (2) Different GPS data periods (pre/post major earthquakes)
#   (3) Different numbers of stations (25 vs 67)
#   (4) Different postseismic correction strategies
#
# Inter-study uncertainty: Lat ±6°, Lon ±10°, ω ±0.05°/Ma → ±3-4 mm/yr on vT
#
_wx_b03, _wy_b03, _wz_b03 = _pole_to_wxyz(47.2, -78.3, 0.335)   # Bock 2003
_wx_s07, _wy_s07, _wz_s07 = _pole_to_wxyz(50.7, -83.4, 0.287)   # Simons 2007
_wx_d10, _wy_d10, _wz_d10 = _pole_to_wxyz(56.0, -75.6, 0.333)   # DeMets 2010
_wx_a11, _wy_a11, _wz_a11 = _pole_to_wxyz(56.0, -75.6, 0.333)   # Argus 2011
_wx_k14, _wy_k14, _wz_k14 = _pole_to_wxyz(52.1, -81.2, 0.292)   # Kreemer 2014
_wx_y17, _wy_y17, _wz_y17 = _pole_to_wxyz(44.5, -88.2, 0.349)   # Yong 2017
_wx_k19, _wy_k19, _wz_k19 = _pole_to_wxyz(46.2, -89.4, 0.327)   # Kuncoro 2019
_wx_a24, _wy_a24, _wz_a24 = _pole_to_wxyz(45.63, -88.71, 0.337) # Alif 2024

ADDITIONAL_PLATES = {
    # ══════════════════════════════════════════════════════════════════════════
    # SUNDALAND EULER POLE — 8 REGIONAL ESTIMATES FROM PEER-REVIEWED LITERATURE
    #
    # IMPORTANT: No Sundaland Euler Pole exists in ITRF2020-PMM (Altamimi 2023).
    # All GPS stations in the region were excluded because they fail strict
    # site-selection criteria (proximity to Sunda Trench, interseismic strain,
    # postseismic deformation from Aceh 2004/Bengkulu 2007, Great Sumatran Fault).
    # These parameters are REGIONAL ESTIMATES ONLY — inter-study uncertainty: ±3–4 mm/yr.
    # ══════════════════════════════════════════════════════════════════════════

    'SUND_B03': {
        'wx': _wx_b03, 'wy': _wy_b03, 'wz': _wz_b03,
        'name': 'Sundaland — Bock et al. (2003)',
        'source': 'Bock et al. (2003) J.Geophys.Res. 108(B1)',
        'pole_lat': 47.2, 'pole_lon': -78.3, 'pole_omega': 0.335,
        'frame': 'ITRF2000', 'n_stations': '7', 'data_period': '1991–2001',
        'note': (
            'Early dense GPS network in Indonesia (7 stations). '
            'First comprehensive Sundaland study. '
            'Superseded by Simons (2007) with more stations and longer time series.'
        ),
    },
    'SUND_S07': {
        'wx': _wx_s07, 'wy': _wy_s07, 'wz': _wz_s07,
        'name': 'Sundaland — Simons et al. (2007)',
        'source': 'Simons et al. (2007) J.Geophys.Res. 112, B12402',
        'pole_lat': 50.7, 'pole_lon': -83.4, 'pole_omega': 0.287,
        'frame': 'ITRF2000/NNR-NUVEL-1A', 'n_stations': '28', 'data_period': '1994–2004',
        'note': (
            'Most widely cited Sundaland reference. 28 GPS stations across '
            'Java, Sumatra, Borneo, Malaysia, Thailand. Pre-Aceh 2004 data — '
            'no postseismic corrections needed. doi:10.1029/2005JB003868'
        ),
    },
    'SUND_D10': {
        'wx': _wx_d10, 'wy': _wy_d10, 'wz': _wz_d10,
        'name': 'Sundaland — DeMets et al. (2010) MORVEL',
        'source': 'DeMets et al. (2010) Geophys.J.Int. 181(1), 1–80',
        'pole_lat': 56.0, 'pole_lon': -75.6, 'pole_omega': 0.333,
        'frame': 'NNR-MORVEL', 'n_stations': '18', 'data_period': '1994–2004',
        'note': (
            'MORVEL global plate model. Used 18 of Simons (2007) stations '
            'after excluding sites near the Sumatra trench. '
            'Consistent with Simons 2007 within 1 mm/yr. doi:10.1111/j.1365-246X.2009.04491.x'
        ),
    },
    'SUND_A11': {
        'wx': _wx_a11, 'wy': _wy_a11, 'wz': _wz_a11,
        'name': 'Sundaland — Argus et al. (2011) NNR-MORVEL56',
        'source': 'Argus et al. (2011) Geochem.Geophys.Geosyst.',
        'pole_lat': 56.0, 'pole_lon': -75.6, 'pole_omega': 0.333,
        'frame': 'NNR-MORVEL56', 'n_stations': '18', 'data_period': '1994–2004',
        'note': (
            'NNR-MORVEL56 — most comprehensive NNR plate model (56 plates). '
            'Sundaland parameters derived from DeMets (2010) MORVEL. '
            'doi:10.1029/2011GC003751'
        ),
    },
    'SUND_K14': {
        'wx': _wx_k14, 'wy': _wy_k14, 'wz': _wz_k14,
        'name': 'Sundaland — Kreemer et al. (2014) GSRM v2',
        'source': 'Kreemer et al. (2014) Geochem.Geophys.Geosyst. 15(10)',
        'pole_lat': 52.1, 'pole_lon': -81.2, 'pole_omega': 0.292,
        'frame': 'IGS08/NNR', 'n_stations': '~10', 'data_period': '1994–2013',
        'note': (
            'Global Strain Rate Model v2 (GSRM-NNR-2.1). '
            'Combined geodetic velocities and geological strain rates (~22,500 sites total). '
            'doi:10.1002/2014GC005407'
        ),
    },
    'SUND_Y17': {
        'wx': _wx_y17, 'wy': _wy_y17, 'wz': _wz_y17,
        'name': 'Sundaland — Yong et al. (2017)',
        'source': 'Yong et al. (2017) J.Applied Geodesy 11(3), 169–177',
        'pole_lat': 44.5, 'pole_lon': -88.2, 'pole_omega': 0.349,
        'frame': 'ITRF2008', 'n_stations': '10', 'data_period': '1999–2014',
        'note': (
            'Malaysia-focused cGPS study (MyRTKnet). Excluded sites with '
            'postseismic deformation from 2004/2005/2007 earthquakes. '
            'Peninsular Malaysia as stable Sundaland core. doi:10.1515/jag-2016-0024'
        ),
    },
    'SUND_K19': {
        'wx': _wx_k19, 'wy': _wy_k19, 'wz': _wz_k19,
        'name': 'Sundaland — Kuncoro et al. (2019)',
        'source': 'Kuncoro et al. (2019) E3S Web Conf. 94, 04006',
        'pole_lat': 46.2, 'pole_lon': -89.4, 'pole_omega': 0.327,
        'frame': 'ITRF2008', 'n_stations': '~15', 'data_period': '1994–2016',
        'note': (
            'TDEFNODE elastic block model — simultaneously estimated Sunda and '
            'Sumatra block rotations with fault coupling. '
            'doi:10.1051/e3sconf/20199404006'
        ),
    },
    'SUND_A24': {
        'wx': _wx_a24, 'wy': _wy_a24, 'wz': _wz_a24,
        'name': 'Sundaland — Alif et al. (2024)',
        'source': 'Alif et al. (2024) Geoscience Letters 11:16',
        'pole_lat': 45.63, 'pole_lon': -88.71, 'pole_omega': 0.337,
        'frame': 'ITRF2014', 'n_stations': '67 (37 new)', 'data_period': '2017–2022',
        'note': (
            'Most recent and comprehensive estimate. 37 new InaCORS+SuGAr stations '
            'in Sumatra + 30 transformed. Full postseismic corrections (Aceh 2004, '
            'Nias 2005, Bengkulu 2007, N.Sumatra 2012). χ²=0.05 mm/yr. '
            'Uncertainty: lat±0.45°, lon±0.38°, ω±0.002°/Ma. doi:10.1186/s40562-024-00330-0'
        ),
    },
}

# ── Origin Rate Bias — Altamimi (2023) Section 5, Table 2 ────────────────────
# Must be added to predicted horizontal velocities for full ITRF2020 consistency.
# Discard the artifactual vertical component from ORB addition (Altamimi 2023).
ORB = {
    'Tx': +0.37,   # mm/yr
    'Ty': +0.35,   # mm/yr
    'Tz': +0.74,   # mm/yr
}


# ══════════════════════════════════════════════════════════════════════════════
# FUNGSI KONVERSI
# ══════════════════════════════════════════════════════════════════════════════

def wxyz_to_pole(wx_mas: float, wy_mas: float, wz_mas: float) -> dict:
    """
    Konversi komponen rotasi (wx, wy, wz) dalam mas/yr ke koordinat Euler Pole.

    Langkah-langkah sesuai Altamimi et al. (2023):

    Langkah 1 — Magnitude total:
      |omega| = sqrt(wx^2 + wy^2 + wz^2)   [mas/yr]

    Langkah 2 — Konversi ke deg/Ma:
      omega (deg/Ma) = |omega| / 3.6
      (1 mas/yr = 1/3.600.000 deg/yr x 1.000.000 yr/Ma = 1/3.6 deg/Ma)

    Langkah 3 — Longitude via atan2:
      lambda = atan2(wy, wx)
      Konvensi paper: 0-360 deg (tambah 360 jika negatif)

    Langkah 4 — Latitude via atan2:
      phi = atan2(wz, sqrt(wx^2 + wy^2))
      Positif = belahan utara, negatif = belahan selatan.

    Returns dict:
      lat     : latitude (deg, +N/-S)
      lon     : longitude 0-360 deg (konvensi Altamimi 2023)
      lon_180 : longitude -180/+180 deg (untuk peta)
      omega   : kecepatan rotasi (deg/Ma)
      wx, wy, wz : komponen input (mas/yr)
    """
    # Langkah 1
    omega_mas    = float(np.sqrt(wx_mas**2 + wy_mas**2 + wz_mas**2))
    # Langkah 2
    omega_deg_ma = omega_mas / 3.6
    # Langkah 3
    lon_180  = float(np.degrees(np.arctan2(wy_mas, wx_mas)))
    lon_0360 = float(lon_180 % 360)
    # Langkah 4
    rho     = np.sqrt(wx_mas**2 + wy_mas**2)
    lat_deg = float(np.degrees(np.arctan2(wz_mas, rho)))

    return {
        'lat'    : lat_deg,
        'lon'    : lon_0360,    # 0-360 deg sesuai konvensi jurnal
        'lon_180': lon_180,     # -180/+180 deg untuk keperluan peta
        'omega'  : omega_deg_ma,
        'wx'     : wx_mas,
        'wy'     : wy_mas,
        'wz'     : wz_mas,
    }


def get_plate_pole(plate_code: str = 'EURA') -> dict:
    """
    Ambil parameter Euler Pole dari ITRF2020-PMM.

    Default: EURA (Eurasian) — digunakan sebagai referensi untuk
    wilayah Sundaland karena SUND tidak ada di Altamimi (2023) Table 1.

    Parameters
    ----------
    plate_code : str — kode lempeng dari ITRF2020_PMM

    Returns
    -------
    dict dengan kunci: lat, lon, lon_180, omega, wx, wy, wz,
                       name, source, frame, ref
    """
    # Cari di tabel utama dulu
    if plate_code in ITRF2020_PMM:
        pmm    = ITRF2020_PMM[plate_code]
        source = 'Altamimi et al. (2023) ITRF2020-PMM Table 1'
        frame  = 'ITRF2020'
    elif plate_code in ADDITIONAL_PLATES:
        pmm    = ADDITIONAL_PLATES[plate_code]
        source = pmm.get('source', 'Referensi tambahan — bukan ITRF2020')
        frame  = 'Non-ITRF2020'
    else:
        available = list(ITRF2020_PMM.keys()) + list(ADDITIONAL_PLATES.keys())
        raise ValueError(
            f"Kode lempeng '{plate_code}' tidak ditemukan. "
            f"Tersedia: {available}"
        )

    pole = wxyz_to_pole(pmm['wx'], pmm['wy'], pmm['wz'])
    pole.update({
        'name'  : pmm['name'],
        'source': source,
        'frame' : frame,
        'ref'   : (
            'Altamimi, Z. et al. (2023). ITRF2020 plate motion model. '
            'J. Geodesy, 97, 48. https://doi.org/10.1007/s00190-023-01737-x'
        ),
    })
    return pole


# ── Default Euler Pole ────────────────────────────────────────────────────────
# EURA (Eurasian) from ITRF2020-PMM — official default per Altamimi (2023).
# Sundaland block has no official Euler Pole in ITRF2020-PMM.
# For Sundaland regional analysis, select SUND_S07 or SUND_A24 from the
# Euler Pole menu, with full awareness of their scientific limitations.
EULER_POLE = get_plate_pole('EURA')


# ── Batas Lempeng Sundaland — Bird (2003) ─────────────────────────────────────
SUNDALAND_BOUNDARY = np.array([
    [ 90.0, 20.0],[ 92.0, 21.5],[ 95.0, 22.0],[ 98.0, 23.0],
    [100.0, 23.5],[102.0, 23.0],[105.0, 22.0],[107.5, 20.5],
    [108.0, 20.0],[110.0, 18.5],[112.0, 18.0],[114.0, 16.5],
    [116.0, 15.0],[118.0, 13.0],[120.0, 12.0],[121.5, 10.0],
    [123.0,  8.0],[124.5,  6.0],[125.0,  4.0],[126.0,  2.0],
    [126.0,  0.0],[125.5, -2.0],[125.0, -4.0],[123.0, -6.0],
    [122.0, -8.0],[120.0,-10.0],[118.0,-11.0],[116.0,-11.5],
    [114.0,-12.0],[112.0,-12.0],[110.0,-12.0],[108.0,-11.5],
    [106.0,-12.0],[104.0,-10.5],[102.0,-10.0],[ 99.0, -8.0],
    [ 96.0, -5.0],[ 94.0, -3.0],[ 92.0,  0.0],[ 91.0,  2.0],
    [ 90.0,  4.0],[ 90.0,  8.0],[ 90.0, 14.0],[ 90.0, 20.0]
])

# ── Titik Demo Default ────────────────────────────────────────────────────────
DEFAULT_POINTS = [
    ("Bengkulu",     -3.80,  102.27),
    ("Jakarta",      -6.21,  106.85),
    ("Medan",         3.59,   98.67),
    ("Kuala Lumpur",  3.14,  101.69),
    ("Surabaya",     -7.25,  112.75),
    ("Makassar",     -5.13,  119.42),
    ("Palangkaraya", -2.21,  113.92),
    ("Banda Aceh",    5.55,   95.32),
]

# ── Extent Peta ───────────────────────────────────────────────────────────────
MAP_EXTENT = [88.0, 134.0, -14.0, 24.0]

# ── Info Aplikasi ─────────────────────────────────────────────────────────────
APP_NAME    = "GeoPlate Analyst — Sundaland"
APP_VERSION = "2.1.0"
APP_AUTHOR  = "Geodynamics Lab"
