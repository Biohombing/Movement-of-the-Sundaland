# -*- mode: python ; coding: utf-8 -*-
# =============================================================================
# sundaland.spec
# PyInstaller specification file untuk Sundaland Motion Pro
#
# Cara pakai:
#   pyinstaller sundaland.spec
#
# Output: dist/SundalandMotionPro.exe
# =============================================================================

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# ── Kumpulkan semua data files yang dibutuhkan ────────────────────────────────

datas = []

# Cartopy: butuh data shapefile internal (coastline, borders, dll)
try:
    import cartopy
    cartopy_dir = os.path.dirname(cartopy.__file__)
    datas += [(os.path.join(cartopy_dir, 'data'), 'cartopy/data')]
    datas += [(os.path.join(cartopy_dir, 'io'),   'cartopy/io')]
    # Cartopy shapefiles (Natural Earth)
    import cartopy.io.shapereader as shp
    ne_dir = shp.natural_earth.__module__
    datas += collect_data_files('cartopy')
except ImportError:
    pass

# Matplotlib: data fonts dan style
datas += collect_data_files('matplotlib')

# UI stylesheet
datas += [('ui/style.qss', 'ui')]

# ── Hidden imports (library yang tidak terdeteksi otomatis) ───────────────────

hiddenimports = []

# Cartopy submodules
hiddenimports += collect_submodules('cartopy')

# Matplotlib backends
hiddenimports += [
    'matplotlib.backends.backend_qtagg',
    'matplotlib.backends.backend_agg',
]

# PyQt6 modules
hiddenimports += [
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
]

# Pandas & Excel
hiddenimports += [
    'pandas',
    'openpyxl',
    'openpyxl.styles',
    'openpyxl.utils',
]

# Numpy & Scipy (dipakai Cartopy internal)
hiddenimports += [
    'numpy',
    'numpy.core._multiarray_umath',
    'scipy',
    'scipy.special',
    'scipy.spatial',
]

# Shapely (dipakai Cartopy)
hiddenimports += collect_submodules('shapely')

# ── Analysis ──────────────────────────────────────────────────────────────────

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude yang tidak dipakai (kurangi ukuran file)
        'tkinter',
        'wx',
        'PySide2',
        'PySide6',
        'PyQt5',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        'PIL',          # Pillow tidak dipakai
        'cv2',          # OpenCV tidak dipakai
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SundalandMotionPro',          # Nama file .exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                            # Kompres dengan UPX (kurangi ukuran)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                       # False = tidak ada jendela terminal hitam
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',            # Uncomment jika ada file icon .ico
)
