@echo off
:: =============================================================================
:: BUILD.bat
:: Script build otomatis untuk Sundaland Motion Pro → .exe
:: Jalankan dengan double-click atau dari Command Prompt
:: =============================================================================

title Sundaland Motion Pro - Build EXE
color 0A

echo.
echo  ============================================================
echo   SUNDALAND MOTION PRO - BUILD SCRIPT
echo   Membangun aplikasi menjadi file .exe ...
echo  ============================================================
echo.

:: ── Cek Python tersedia ───────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python tidak ditemukan!
    echo  Silakan install Python 3.10+ dari https://python.org
    pause
    exit /b 1
)

echo  [OK] Python ditemukan
python --version

:: ── Install PyInstaller jika belum ada ───────────────────────────────────────
echo.
echo  [1/4] Mengecek PyInstaller ...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Menginstall PyInstaller ...
    pip install pyinstaller
    if errorlevel 1 (
        echo  [ERROR] Gagal install PyInstaller!
        pause
        exit /b 1
    )
)
echo  [OK] PyInstaller siap

:: ── Install semua dependensi ─────────────────────────────────────────────────
echo.
echo  [2/4] Menginstall semua dependensi ...
pip install -r requirements.txt
if errorlevel 1 (
    echo  [PERINGATAN] Beberapa package mungkin gagal install.
    echo  Lanjutkan build ...
)
echo  [OK] Dependensi selesai

:: ── Bersihkan build lama ─────────────────────────────────────────────────────
echo.
echo  [3/4] Membersihkan build sebelumnya ...
if exist "build" rmdir /s /q "build"
if exist "dist"  rmdir /s /q "dist"
echo  [OK] Folder build dibersihkan

:: ── Jalankan PyInstaller ─────────────────────────────────────────────────────
echo.
echo  [4/4] Membangun file .exe ...
echo  (Proses ini membutuhkan 3-10 menit, mohon tunggu ...)
echo.

pyinstaller sundaland.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo  ============================================================
    echo  [ERROR] Build GAGAL!
    echo  Coba jalankan: python -m PyInstaller sundaland.spec
    echo  atau lihat pesan error di atas.
    echo  ============================================================
    pause
    exit /b 1
)

:: ── Selesai ──────────────────────────────────────────────────────────────────
echo.
echo  ============================================================
echo  [SUKSES] Build selesai!
echo.
echo  File .exe tersedia di:
echo  dist\SundalandMotionPro.exe
echo.
echo  Ukuran file:
dir "dist\SundalandMotionPro.exe" | findstr "SundalandMotionPro"
echo  ============================================================
echo.

:: Buka folder dist otomatis
explorer dist

pause
