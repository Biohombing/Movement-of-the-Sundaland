#!/bin/bash
# =============================================================================
# build.sh
# Script build untuk Linux / macOS → binary executable
# Jalankan: bash build.sh
# =============================================================================

set -e   # Berhenti jika ada error

echo ""
echo "============================================================"
echo " SUNDALAND MOTION PRO - BUILD SCRIPT (Linux/Mac)"
echo "============================================================"
echo ""

# ── Cek Python ────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 tidak ditemukan!"
    exit 1
fi
echo "[OK] $(python3 --version)"

# ── Install PyInstaller ───────────────────────────────────────────────────────
echo ""
echo "[1/4] Mengecek PyInstaller ..."
python3 -c "import PyInstaller" 2>/dev/null || pip3 install pyinstaller
echo "[OK] PyInstaller siap"

# ── Install dependensi ────────────────────────────────────────────────────────
echo ""
echo "[2/4] Menginstall dependensi ..."
pip3 install -r requirements.txt
echo "[OK] Dependensi selesai"

# ── Bersihkan build lama ──────────────────────────────────────────────────────
echo ""
echo "[3/4] Membersihkan build sebelumnya ..."
rm -rf build dist
echo "[OK] Folder build dibersihkan"

# ── Build ─────────────────────────────────────────────────────────────────────
echo ""
echo "[4/4] Membangun executable ..."
echo "(Proses ini membutuhkan 3-10 menit ...)"
echo ""

pyinstaller sundaland.spec --clean --noconfirm

echo ""
echo "============================================================"
echo "[SUKSES] Build selesai!"
echo ""
echo "File executable tersedia di: dist/SundalandMotionPro"
echo ""
ls -lh dist/SundalandMotionPro 2>/dev/null || echo "(file ditemukan di folder dist/)"
echo "============================================================"
