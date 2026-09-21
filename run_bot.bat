@echo off
echo ===================================================
echo BALIKESIR SON DAKIKA HABER - UZAKTAN HABER BOTU
echo ===================================================

echo [1/3] Sanal ortam (venv) aktif ediliyor...
call venv\Scripts\activate.bat

echo [2/3] Haber cekme ve gonderim botu baslatiliyor...
echo.
python scripts\pc_worker.py

echo.
echo Islem tamamlandi.
pause
