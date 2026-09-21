@echo off
echo ===================================
echo BALIKESIR SON DAKIKA HABER
echo ===================================
echo.
echo Kurulum baslatiliyor...
echo.

IF NOT EXIST "venv" (
    echo [1/6] Sanal ortam (venv) olusturuluyor...
    python -m venv venv
) ELSE (
    echo [1/6] Sanal ortam zaten mevcut.
)

echo.
echo [2/6] Bagimliliklar yukleniyor...
call venv\Scripts\python.exe -m pip install --upgrade pip
call venv\Scripts\pip.exe install -r requirements.txt

echo.
echo [3/6] Gerekli klasorler olusturuluyor...
IF NOT EXIST "data" mkdir data
IF NOT EXIST "data\media" mkdir data\media
IF NOT EXIST "logs" mkdir logs

echo.
echo [4/6] Veritabani (.env) ayarlari kontrol ediliyor...
IF NOT EXIST ".env" (
    copy .env.example .env
    echo Lutfen .env dosyasini kontrol edin ve bilgilerinizi girin.
) ELSE (
    echo .env dosyasi mevcut.
)

echo.
echo [5/6] Veritabani tablolari olusturuluyor...
call venv\Scripts\python.exe scripts\init_db.py

echo.
echo [6/6] Kurulum tamamlandi!
echo.
echo Sistemi baslatmak icin 'run.bat' dosyasina tiklayabilirsiniz.
pause
