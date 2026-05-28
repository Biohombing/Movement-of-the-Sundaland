# 🌏 Sundaland Motion Pro — v1.0

Aplikasi desktop profesional untuk perhitungan **gerak lempeng Sundaland** berbasis Euler Pole (Simons et al., 2007).

---

## 🚀 Cara Menjalankan

### 1. Install dependensi

```bash
pip install -r requirements.txt
```

### 2. Jalankan aplikasi

```bash
python main.py
```

---

## ✨ Fitur Utama

| Fitur | Keterangan |
|---|---|
| 📍 Input Manual | Form dialog dengan validasi otomatis |
| 📊 Load Excel / CSV | Auto-detect kolom lat/lon |
| 🗺 Load Shapefile | Extract koordinat dari Point/Polygon/Line |
| 🏙 Data Default | 8 kota Sundaland langsung siap pakai |
| ▶ Hitung Kecepatan | Worker thread — UI tidak freeze |
| 🗺 Peta Cartopy | Mercator, batas lempeng, vektor kecepatan |
| 📍 Klik Peta | Tambah titik langsung dengan klik di peta |
| 📋 Tabel Hasil | vN, vE, V Total, Azimuth, Arah (16-mata) |
| 🧭 Diagram Rose | Visualisasi arah gerakan seluruh titik |
| 💾 Export Excel | Dengan sheet metadata Euler Pole |
| 📄 Export CSV | Format flat, siap diolah lanjut |
| 🖼 Simpan Peta | PNG resolusi tinggi (200 dpi) |
| 💾 Simpan Proyek | Format JSON (.smp), restore session |
| 🌐 Euler Pole | Parameter bisa diubah dari GUI |

---

## 🗂 Struktur Proyek

```
sundaland_motion_pro/
├── main.py                  ← Entry point
├── requirements.txt
├── core/
│   ├── constants.py         ← Euler Pole, konstanta fisika
│   └── euler_engine.py      ← Matematika murni: v = ω × r
├── models/
│   └── data_models.py       ← @dataclass: ObservationPoint, PlateVelocity, …
├── services/
│   ├── input_service.py     ← Load CSV/Excel/SHP, export, save/load project
│   └── calculation_worker.py← QThread worker
├── visualization/
│   └── map_canvas.py        ← Cartopy + Matplotlib embedded in Qt
├── ui/
│   ├── main_window.py       ← Jendela utama, orkestrasi semua panel
│   ├── input_panel.py       ← Tabel input + tombol aksi
│   ├── result_panel.py      ← Tabel hasil + Diagram Rose
│   ├── dialogs.py           ← AddPoint, EulerPole, About dialogs
│   └── style.qss            ← Dark scientific stylesheet
└── assets/
    └── create_sample_excel.py
```

---

## 📐 Arsitektur

```
Multi Input System  (CSV / Excel / SHP / Manual / Klik Peta)
        ↓
  ObservationPoint  (@dataclass)
        ↓
  CalculationWorker (QThread)  ←── Tidak memblok UI
        ↓
  PlateVelocity     (@dataclass)  ←── v = ω × r
        ↓
  ┌──────────────┬──────────────┐
  │  ResultPanel  │  MapCanvas   │
  │  (Tabel+Rose) │  (Cartopy)   │
  └──────────────┴──────────────┘
        ↓
  Export: Excel / CSV / PNG / .smp
```

---

## 📚 Referensi

- Simons et al. (2007) *J. Geophys. Res.* 112, B12402
- Bird P. (2003) *Geochem. Geophys. Geosyst.* 4(3):1027

---

## 📋 Format File Input

### CSV / Excel
Wajib punya kolom (nama tidak case-sensitive):

| Kolom Latitude | Kolom Longitude | Kolom Nama (opsional) |
|---|---|---|
| `lat` / `latitude` / `lintang` | `lon` / `longitude` / `bujur` | `name` / `nama` / `lokasi` |

### Shapefile
Semua geometry didukung:
- **Point** → koordinat langsung
- **Polygon** → centroid
- **LineString** → midpoint

CRS otomatis dikonversi ke WGS84 (EPSG:4326).
