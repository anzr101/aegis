@echo off
REM AEGIS - one-command setup + launch (Windows)
cd /d "%~dp0"

echo.
echo   AEGIS - Campaign Intelligence - Ezor Media
echo   -------------------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo   x Python not found. Install Python 3.9+ and re-run.
  exit /b 1
)

if not exist ".venv" (
  echo   - Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo   - Installing dependencies (first run only)...
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

if not exist ".env" (
  copy .env.example .env >nul
  echo   - Created .env (DEMO mode). Add an Anthropic key for LIVE AI.
)

echo.
echo   Ready. Opening http://localhost:8000
echo   (Ctrl+C to stop)
echo.
uvicorn backend.main:app --host 0.0.0.0 --port 8000
