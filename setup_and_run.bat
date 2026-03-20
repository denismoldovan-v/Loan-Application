@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AI Loan Intake Assistant

echo ========================================
echo   AI Loan Application Intake Assistant
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Brak Pythona. Zainstaluj Python 3.10+ z https://www.python.org/
  echo         Zaznacz "Add Python to PATH" przy instalacji.
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo [ERROR] Brak pliku requirements.txt w folderze: %cd%
  pause
  exit /b 1
)

if not exist "single_file_app.py" (
  echo [ERROR] Brak pliku single_file_app.py w folderze: %cd%
  pause
  exit /b 1
)

if not exist ".env" (
  echo Brak pliku .env — utworzymy go z Twoim kluczem OpenAI.
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$k = Read-Host 'Wklej klucz OpenAI API key (Enter = pusty, tryb fallback)'; if ([string]::IsNullOrWhiteSpace($k)) { Set-Content -LiteralPath '.env' -Value @('OPENAI_API_KEY=','OPENAI_MODEL=gpt-4.1-mini') -Encoding UTF8; Write-Host 'Zapisano pusty klucz — dziala fallback bez OpenAI.' } else { Set-Content -LiteralPath '.env' -Value @('OPENAI_API_KEY=' + $k, 'OPENAI_MODEL=gpt-4.1-mini') -Encoding UTF8 }"
  echo.
)

if not exist ".venv\Scripts\python.exe" (
  echo Tworzenie srodowiska wirtualnego .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Nie udalo sie utworzyc venv.
    pause
    exit /b 1
  )
)

echo Instalacja zaleznosci (pip)...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install nie powiodl sie.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$appPid=(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess); if($appPid){ exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Serwer juz dziala na porcie 8000. Otwieram przegladarke...
  start "" "http://localhost:8000/"
  pause
  exit /b 0
)

echo Otwieram przegladarke za chwile (http://localhost:8000/) ...
start "" cmd /c "ping 127.0.0.1 -n 4 >nul && start http://localhost:8000/"

echo Uruchamianie serwera (Ctrl+C aby zatrzymac)...
echo.
".venv\Scripts\python.exe" single_file_app.py
if errorlevel 1 pause
