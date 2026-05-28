# 📦 Cara Build Sundaland Motion Pro → File .EXE

Panduan lengkap untuk mengubah aplikasi Python menjadi file `.exe`
yang bisa langsung dijalankan tanpa install Python.

---

## ✅ Prasyarat

- Python 3.10 atau lebih baru sudah terinstall
- Koneksi internet (untuk download PyInstaller dan dependensi)
- Sistem operasi: **Windows 10/11** (untuk menghasilkan .exe)

Cek Python:
```
python --version
```

---

## 🚀 Cara Build (Windows) — PALING MUDAH

### Langkah 1 — Buka folder project

Pastikan kamu berada di dalam folder `sundaland_motion_pro/`
yang berisi file `main.py`, `BUILD.bat`, `sundaland.spec`, dll.

### Langkah 2 — Double-click BUILD.bat

Cari file **`BUILD.bat`** di dalam folder, lalu **double-click**.

Script ini akan otomatis:
1. Mengecek Python
2. Menginstall PyInstaller
3. Menginstall semua dependensi dari `requirements.txt`
4. Membangun file `.exe`
5. Membuka folder `dist/` yang berisi hasil build

⏳ Proses ini membutuhkan **3–10 menit** tergantung kecepatan internet dan komputer.

### Langkah 3 — Ambil file .exe

Setelah selesai, file `.exe` ada di:
```
sundaland_motion_pro/
└── dist/
    └── SundalandMotionPro.exe   ← ini yang dibagikan ke orang lain
```

---

## 🖥️ Cara Build Manual (via Command Prompt)

Kalau BUILD.bat tidak mau jalan, lakukan secara manual:

```bash
# Buka CMD di folder sundaland_motion_pro, lalu:

# Step 1: Install PyInstaller
pip install pyinstaller

# Step 2: Install semua dependensi
pip install -r requirements.txt

# Step 3: Build
pyinstaller sundaland.spec --clean --noconfirm
```

---

## 🍎 Cara Build di Linux / macOS

```bash
# Di terminal, masuk ke folder project:
cd sundaland_motion_pro

# Beri izin eksekusi
chmod +x build.sh

# Jalankan
bash build.sh
```

Hasil build ada di `dist/SundalandMotionPro` (tanpa ekstensi di Linux/Mac).

---

## 📁 Struktur Setelah Build

```
sundaland_motion_pro/
├── dist/
│   └── SundalandMotionPro.exe   ← FILE HASIL BUILD
├── build/                        ← file sementara (bisa dihapus)
├── main.py
├── sundaland.spec
├── BUILD.bat
└── ...
```

---

## 📤 Cara Distribusi ke Orang Lain

Cukup copy **satu file saja**:
```
SundalandMotionPro.exe
```

Kirim via USB, Google Drive, email, atau platform lainnya.

Pengguna tinggal **double-click** file tersebut — tidak perlu install Python,
tidak perlu install library apapun.

---

## ❗ Troubleshooting Build

### Error: `ModuleNotFoundError` saat build

Pastikan semua library sudah terinstall:
```bash
pip install -r requirements.txt
```

### Error terkait Cartopy

Cartopy kadang butuh install via Conda:
```bash
conda install -c conda-forge cartopy pyinstaller
pyinstaller sundaland.spec --clean
```

### File .exe jalan tapi muncul error saat dibuka

Coba build dengan mode `--console` dulu untuk lihat error:

Edit `sundaland.spec`, ubah baris:
```python
console=False   →   console=True
```
Lalu build ulang. Jendela hitam akan muncul dan menampilkan pesan error.

### Antivirus memblokir .exe

Ini normal untuk file .exe hasil PyInstaller. Tambahkan ke whitelist antivirus,
atau gunakan code signing certificate untuk distribusi komersial.

### Ukuran file terlalu besar

Ukuran normal untuk aplikasi ini: **150–400 MB**.
Ini wajar karena Python runtime + semua library ikut terbundle.

Untuk mengurangi ukuran:
1. Pastikan UPX terinstall: https://upx.github.io/
2. UPX sudah diaktifkan di `sundaland.spec` (`upx=True`)

---

## 🔄 Build Ulang Setelah Ada Perubahan Kode

Setiap kali ada perubahan pada kode Python, kamu harus build ulang:

```bash
# Hapus hasil build lama dulu
rmdir /s /q build dist

# Build ulang
pyinstaller sundaland.spec --clean --noconfirm
```

Atau cukup jalankan lagi `BUILD.bat`.
