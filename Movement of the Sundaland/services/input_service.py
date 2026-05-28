"""
services/input_service.py
File I/O services — CSV and Excel loading and Excel export.
Supports decimal comma (,) and decimal point (.).
"""

import os
import pandas as pd
import json
import numpy as np
from typing import List, Tuple, Optional

from models.data_models import ObservationPoint, PlateVelocity, ProjectData


# ── Column aliases ─────────────────────────────────────────────────────────────
LAT_ALIASES  = ['lat', 'latitude', 'lintang', 'y']
LON_ALIASES  = ['lon', 'lng', 'longitude', 'bujur', 'x']
NAME_ALIASES = ['name', 'nama', 'lokasi', 'location', 'kota', 'station',
                'id', 'site', 'stasiun']


def _find_column(df: pd.DataFrame, aliases: list) -> Optional[str]:
    for col in df.columns:
        if str(col).strip().lower() in aliases:
            return col
    return None


def _to_float(val) -> float:
    """Convert value to float, handling both comma and point decimals.

    Handles:
      - Decimal comma:   '-3,801'   → -3.801
      - Thousands dot:   '1.022.715' → 1022715.0  (multiple dots = thousands sep)
      - Thousands comma: '1,022,715' → 1022715.0  (multiple commas = thousands sep)
      - Mixed:           '1.022,50'  → 1022.5
    """
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    s = str(val).strip().replace(' ', '')

    dot_count   = s.count('.')
    comma_count = s.count(',')

    if comma_count > 1:
        # Multiple commas → thousands separator: '1,022,715' → '1022715'
        s = s.replace(',', '')
    elif dot_count > 1:
        # Multiple dots → thousands separator: '1.022.715' → '1022715'
        s = s.replace('.', '')
    elif comma_count == 1 and dot_count == 1:
        # Both present — order determines role
        if s.index(',') < s.index('.'):
            # comma before dot → thousands comma: '1,022.50' → '1022.50'
            s = s.replace(',', '')
        else:
            # dot before comma → thousands dot, decimal comma: '1.022,50' → '1022.50'
            s = s.replace('.', '').replace(',', '.')
    elif comma_count == 1 and dot_count == 0:
        # Single comma, no dot → decimal comma: '-3,801' → '-3.801'
        s = s.replace(',', '.')
    # else: single dot or no separator → pass through unchanged

    return float(s)


def _detect_swap(df: pd.DataFrame, lat_col: str, lon_col: str) -> bool:
    """
    Detect if lat and lon columns are swapped by checking value ranges.
    Returns True if the columns should be swapped.
    Latitude must be in [-90, 90]; longitude in [-180, 180].
    If the 'lat' column consistently has values outside ±90, it is actually longitude.
    """
    try:
        lat_vals = pd.to_numeric(df[lat_col], errors='coerce').dropna()
        lon_vals = pd.to_numeric(df[lon_col], errors='coerce').dropna()
        if len(lat_vals) == 0:
            return False
        # If majority of 'lat' values exceed ±90 → they are actually longitudes
        lat_out_of_range = (lat_vals.abs() > 90).sum() / len(lat_vals)
        lon_in_lat_range = (lon_vals.abs() <= 90).sum() / len(lon_vals)
        return lat_out_of_range > 0.5 and lon_in_lat_range > 0.5
    except Exception:
        return False


def _df_to_points(df: pd.DataFrame) -> Tuple[List[ObservationPoint], List[str]]:
    """Convert DataFrame to ObservationPoint list."""
    # Normalize column names
    df.columns = [str(c).strip() for c in df.columns]

    lat_col  = _find_column(df, LAT_ALIASES)
    lon_col  = _find_column(df, LON_ALIASES)
    name_col = _find_column(df, NAME_ALIASES)

    if not lat_col or not lon_col:
        raise ValueError(
            f"Latitude/Longitude columns not found.\n"
            f"Available columns: {list(df.columns)}\n"
            f"Required headers: name, lat, lon  (case-insensitive)\n"
            f"Accepted aliases: lat/latitude/lintang, lon/longitude/bujur\n"
            f"Example:\n"
            f"  name     | lat    | lon\n"
            f"  Bengkulu | -3.801 | 102.271"
        )

    # Auto-detect swapped lat/lon columns
    warnings = []
    swapped  = _detect_swap(df, lat_col, lon_col)
    if swapped:
        lat_col, lon_col = lon_col, lat_col
        warnings.append(
            "⚠ Lat/Lon columns appear to be swapped in the file "
            "(latitude values exceeded ±90°). Columns were automatically "
            "corrected — please verify your data."
        )

    points = []
    for i, row in df.iterrows():
        try:
            name = str(row[name_col]).strip() if name_col else f"Point {i+1}"
            if name.lower() in ('nan', 'none', ''):
                name = f"Point {i+1}"
            lat = _to_float(row[lat_col])
            lon = _to_float(row[lon_col])
            pt  = ObservationPoint(name=name, lat=lat, lon=lon)
            ok, msg = pt.validate()
            if ok:
                points.append(pt)
            else:
                warnings.append(f"Row {i+1} skipped: {msg}")
        except Exception as e:
            warnings.append(f"Row {i+1} error: {e}")

    return points, warnings


def load_csv(filepath: str) -> Tuple[List[ObservationPoint], List[str]]:
    """Load observation points from CSV (supports comma and semicolon separators)."""
    # Try comma separator first, then semicolon
    try:
        df = pd.read_csv(filepath, sep=',', encoding='utf-8')
        if len(df.columns) <= 1:
            # Likely semicolon-separated
            df = pd.read_csv(filepath, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, sep=',', encoding='latin-1')
        if len(df.columns) <= 1:
            df = pd.read_csv(filepath, sep=';', encoding='latin-1')
    return _df_to_points(df)


def load_excel(filepath: str, sheet: Optional[str] = None) -> Tuple[List[ObservationPoint], List[str]]:
    """Load observation points from Excel (.xlsx or .xls)."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.xls':
            df = pd.read_excel(filepath, sheet_name=sheet or 0, engine='xlrd')
        else:
            df = pd.read_excel(filepath, sheet_name=sheet or 0, engine='openpyxl')
    except Exception:
        df = pd.read_excel(filepath, sheet_name=sheet or 0)
    return _df_to_points(df)


# ── Exporters ──────────────────────────────────────────────────────────────────

RESULT_COLUMNS = {
    'name'   : 'Location',
    'lat'    : 'Latitude (°)',
    'lon'    : 'Longitude (°)',
    'vN'     : 'vN (mm/yr)',
    'vE'     : 'vE (mm/yr)',
    'vT'     : 'V Total (mm/yr)',
    'azimuth': 'Azimuth (°)',
    'compass': 'Direction',
}


def export_excel(results: List[PlateVelocity], filepath: str,
                 euler_info: dict = None) -> None:
    records = [r.to_dict() for r in results]
    df = pd.DataFrame(records).rename(columns=RESULT_COLUMNS)
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Calculation Results', index=False)
        if euler_info:
            meta = pd.DataFrame([{"Parameter": k, "Value": v}
                                  for k, v in euler_info.items()])
            meta.to_excel(writer, sheet_name='Euler Pole Info', index=False)
        ws = writer.sheets['Calculation Results']
        for col in ws.columns:
            w = max(len(str(cell.value or '')) for cell in col) + 2
            ws.column_dimensions[col[0].column_letter].width = min(w, 30)


def export_csv(results: List[PlateVelocity], filepath: str) -> None:
    records = [r.to_dict() for r in results]
    df = pd.DataFrame(records).rename(columns=RESULT_COLUMNS)
    df.to_csv(filepath, index=False, float_format='%.4f')


# ── Project Save / Load ────────────────────────────────────────────────────────

def save_project(project: ProjectData, filepath: str) -> None:
    data = {
        'version': project.version,
        'notes'  : project.notes,
        'points' : [{'name': p.name, 'lat': p.lat, 'lon': p.lon}
                    for p in project.points],
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_project(filepath: str) -> ProjectData:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    project = ProjectData(notes=data.get('notes', ''),
                          version=data.get('version', '1.0'))
    for p in data.get('points', []):
        project.add_point(ObservationPoint(p['name'], p['lat'], p['lon']))
    return project
