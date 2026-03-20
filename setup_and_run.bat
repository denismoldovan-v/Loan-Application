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
  echo [ERROR] Python not found. Install Python 3.10+ from https://www.python.org/
  echo         Enable "Add Python to PATH" during setup.
  pause
  exit /b 1
)

if not exist "requirements.txt" (
  echo [ERROR] requirements.txt not found in: %cd%
  pause
  exit /b 1
)

if not exist "single_file_app.py" (
  echo [ERROR] single_file_app.py not found in: %cd%
  pause
  exit /b 1
)

if not exist ".env" (
  echo No .env file yet — we will create it with your OpenAI API key.
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$k = Read-Host 'Paste OpenAI API key (Enter = empty, fallback mode)'; if ([string]::IsNullOrWhiteSpace($k)) { Set-Content -LiteralPath '.env' -Value @('OPENAI_API_KEY=','OPENAI_MODEL=gpt-4.1-mini') -Encoding UTF8; Write-Host 'Saved empty key — fallback mode without OpenAI.' } else { Set-Content -LiteralPath '.env' -Value @('OPENAI_API_KEY=' + $k, 'OPENAI_MODEL=gpt-4.1-mini') -Encoding UTF8 }"
  echo.
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv ...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv.
    pause
    exit /b 1
  )
)

echo Installing dependencies ^(pip^)...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

powershell -NoProfile -Command "$appPid=(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess); if($appPid){ exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Server already running on port 8000. Opening browser...
  start "" "http://localhost:8000/"
  pause
  exit /b 0
)

echo Opening browser shortly ^(http://localhost:8000/^) ...
start "" cmd /c "ping 127.0.0.1 -n 4 >nul && start http://localhost:8000/"

echo Starting server ^(Ctrl+C to stop^)...
echo.
".venv\Scripts\python.exe" single_file_app.py
if errorlevel 1 pause
