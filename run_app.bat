@echo off
cd /d "%~dp0"
echo Starting AI Loan Application Intake Assistant...

rem If something is already listening on 8000, do not try to start again.
powershell -NoProfile -Command "$appPid=(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess); if($appPid){ exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo.
  echo Server is already running on port 8000.
  echo Open http://localhost:8000/ in your browser.
  exit /b 0
)

python single_file_app.py

