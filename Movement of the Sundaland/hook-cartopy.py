# hook-cartopy.py
# PyInstaller hook untuk memastikan semua data Cartopy ikut terbundle
# Taruh file ini di folder yang sama dengan sundaland.spec

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('cartopy', includes=['**/*'])
hiddenimports = collect_submodules('cartopy')
