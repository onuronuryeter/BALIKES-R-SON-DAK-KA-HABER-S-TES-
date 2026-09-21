@echo off
chcp 65001 >nul
title BALIKESİR SON DAKİKA HABER — Yerel Sunucu

echo.
echo ============================================================
echo   BALIKESİR SON DAKİKA HABER - Yerel Geliştirme Sunucusu
echo ============================================================
echo.

:: Proje kök dizini (run.bat'ın bulunduğu yer)
set PROJECT_DIR=%~dp0

:: Virtual environment kontrolü
if exist "%PROJECT_DIR%venv\Scripts\activate.bat" (
    echo [OK] Virtual environment bulundu: venv
    call "%PROJECT_DIR%venv\Scripts\activate.bat"
) else (
    echo [!] Virtual environment bulunamadı.
    echo     Kurmak icin: python -m venv venv
    echo                  venv\Scripts\activate
    echo                  pip install -r requirements.txt
    echo.
    echo [!] Sistem Python ile devam ediliyor...
)

:: .env kontrolü
if not exist "%PROJECT_DIR%.env" (
    echo.
    echo [UYARI] .env dosyasi bulunamadi!
    echo         copy .env.example .env  komutunu calistirin.
    echo.
    echo Devam ediliyor (varsayilan ayarlar kullanilacak)...
)

:: data dizinleri
if not exist "%PROJECT_DIR%data" mkdir "%PROJECT_DIR%data"
if not exist "%PROJECT_DIR%data\media" mkdir "%PROJECT_DIR%data\media"
if not exist "%PROJECT_DIR%logs" mkdir "%PROJECT_DIR%logs"

echo.
echo [OK] Proje : %PROJECT_DIR%
echo [OK] Uvicorn baslatiliyor...
echo.
echo Ana Sayfa : http://127.0.0.1:8000
echo Admin     : http://127.0.0.1:8000/admin
echo API Docs  : http://127.0.0.1:8000/api/docs
echo Health    : http://127.0.0.1:8000/health
echo.
echo Durdurmak icin: CTRL+C
echo ============================================================
echo.

:: Uvicorn'u başlat (auto-reload development için)
cd /d "%PROJECT_DIR%"
"%PROJECT_DIR%venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --log-level info

echo.
echo [!] Sunucu durduruldu.
pause
