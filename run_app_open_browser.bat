@echo off
cd /d "%~dp0"
echo Starting AI Loan Application Intake Assistant...
rem Open browser only; the app itself will be started below.
rem If something is already listening on 8000, don't start a new server.
powershell -NoProfile -Command "$appPid=(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess); if($appPid){ exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Server is already running on port 8000.
  start http://localhost:8000/
  exit /b 0
)

start http://localhost:8000/
python single_file_app.py

