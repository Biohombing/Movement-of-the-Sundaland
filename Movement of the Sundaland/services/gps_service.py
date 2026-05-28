"""
services/gps_service.py
Load GPS satellite measurement data from CSV or Excel.
Supports decimal comma (,) and decimal point (.).

Expected columns (case-insensitive):
  name/station/site  — point name
  lat/latitude       — latitude  (degrees)
  lon/longitude      — longitude (degrees)
  vN/v_north         — North velocity (mm/yr)
  vE/v_east          — East  velocity (mm/yr)
"""

import os
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional


@dataclass
class GPSPoint:
    name: str
    lat:  float
    lon:  float
    vN:   float   # mm/yr
    vE:   float   # mm/yr

    @property
    def vT(self) -> float:
        return float(np.hypot(self.vN, self.vE))

    @property
    def azimuth(self) -> float:
        return float(np.degrees(np.arctan2(self.vE, self.vN))) % 360.0


# ── Aliases ────────────────────────────────────────────────────────────────────
_NAME = ['name', 'nama', 'station', 'lokasi', 'location', 'id',
         'kota', 'site', 'sta', 'code', 'stasiun']
_LAT  = ['lat', 'latitude', 'lintang', 'y']
_LON  = ['lon', 'lng', 'longitude', 'bujur', 'x']
_VN   = ['vn', 'v_north', 'vn_mm', 'vel_n', 'north', 'vn(mm/yr)']
_VE   = ['ve', 'v_east',  've_mm', 'vel_e', 'east',  've(mm/yr)']


def _col(df: pd.DataFrame, aliases: list) -> Optional[str]:
    for c in df.columns:
        if str(c).strip().lower().replace(' ', '_') in aliases:
            return c
    return None


def _to_float(val) -> float:
    """Convert to float, handling comma/dot decimal and thousands separators."""
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    s = str(val).strip().replace(' ', '')

    dot_count   = s.count('.')
    comma_count = s.count(',')

    if comma_count > 1:
        s = s.replace(',', '')
    elif dot_count > 1:
        s = s.replace('.', '')
    elif comma_count == 1 and dot_count == 1:
        if s.index(',') < s.index('.'):
            s = s.replace(',', '')
        else:
            s = s.replace('.', '').replace(',', '.')
    elif comma_count == 1 and dot_count == 0:
        s = s.replace(',', '.')

    return float(s)


def _parse_horizontal(df: pd.DataFrame) -> Tuple[List[GPSPoint], List[str]]:
    df.columns = [str(c).strip() for c in df.columns]
    name_col = _col(df, _NAME)
    lat_col  = _col(df, _LAT)
    lon_col  = _col(df, _LON)
    vn_col   = _col(df, _VN)
    ve_col   = _col(df, _VE)

    missing = []
    if not lat_col: missing.append('lat')
    if not lon_col: missing.append('lon')
    if not vn_col:  missing.append('vN')
    if not ve_col:  missing.append('vE')
    if missing:
        raise ValueError(
            f"Required columns not found: {missing}\n"
            f"Available columns: {list(df.columns)}\n"
            f"Required headers: name, lat, lon, vN, vE\n"
            f"Example:\n"
            f"  name     | lat    | lon     | vN    | vE\n"
            f"  Bengkulu | -3.801 | 102.271 | 24.52 | 12.13"
        )

    # Auto-detect swapped lat/lon
    warnings = []
    try:
        lat_vals = pd.to_numeric(df[lat_col], errors='coerce').dropna()
        if len(lat_vals) > 0:
            if (lat_vals.abs() > 90).sum() / len(lat_vals) > 0.5:
                lat_col, lon_col = lon_col, lat_col
                warnings.append(
                    "⚠ Lat/Lon columns appear swapped — automatically corrected."
                )
    except Exception:
        pass

    points = []
    for i, row in df.iterrows():
        try:
            name = str(row[name_col]).strip() if name_col else f"GPS-{i+1}"
            if name.lower() in ('nan', 'none', ''):
                name = f"GPS-{i+1}"
            lat = _to_float(row[lat_col])
            lon = _to_float(row[lon_col])
            vN  = _to_float(row[vn_col])
            vE  = _to_float(row[ve_col])
            if not (-90 <= lat <= 90):
                warnings.append(f"Row {i+1} skipped: lat={lat} out of range")
                continue
            if not (-180 <= lon <= 180):
                warnings.append(f"Row {i+1} skipped: lon={lon} out of range")
                continue
            points.append(GPSPoint(name=name, lat=lat, lon=lon, vN=vN, vE=vE))
        except Exception as e:
            warnings.append(f"Row {i+1} error: {e}")
    return points, warnings


def load_gps_csv(filepath: str) -> Tuple[List[GPSPoint], List[str]]:
    """Load GPS data from CSV (auto-detects comma/semicolon separator)."""
    try:
        df = pd.read_csv(filepath, sep=',', encoding='utf-8')
        if len(df.columns) <= 1:
            df = pd.read_csv(filepath, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, sep=',', encoding='latin-1')
        if len(df.columns) <= 1:
            df = pd.read_csv(filepath, sep=';', encoding='latin-1')
    return _parse_horizontal(df)


def load_gps_excel(filepath: str) -> Tuple[List[GPSPoint], List[str]]:
    """Load GPS data from Excel (.xlsx or .xls)."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.xls':
            # Legacy format — requires xlrd
            df = pd.read_excel(filepath, sheet_name=0, engine='xlrd')
        else:
            # Modern .xlsx / .xlsm — use openpyxl
            df = pd.read_excel(filepath, sheet_name=0, engine='openpyxl')
    except Exception:
        # Last-resort fallback: let pandas pick the engine
        df = pd.read_excel(filepath, sheet_name=0)
    return _parse_horizontal(df)


def create_gps_template(filepath: str) -> None:
    """Create a sample GPS data template Excel file."""
    data = pd.DataFrame({
        'name': ['Bengkulu', 'Jakarta', 'Medan', 'Surabaya'],
        'lat':  [-3.801,    -6.210,     3.590,  -7.250],
        'lon':  [102.271,   106.850,   98.670,  112.750],
        'vN':   [24.52,     23.20,     18.70,   22.57],
        'vE':   [12.13,     11.38,      9.40,   10.75],
    })
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        data.to_excel(writer, sheet_name='GPS Data', index=False)
        ws = writer.sheets['GPS Data']
        for col in ws.columns:
            w = max(len(str(c.value or '')) for c in col) + 4
            ws.column_dimensions[col[0].column_letter].width = w
