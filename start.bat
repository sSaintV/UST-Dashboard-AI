@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM start.bat — Windows development launcher for UST Reception AI Dashboard
REM ─────────────────────────────────────────────────────────────────────────────
setlocal

echo.
echo  UST Reception AI Insight Dashboard — Windows Dev Launcher
echo  ----------------------------------------------------------
echo.

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%backend
set FRONTEND_DIR=%SCRIPT_DIR%frontend

REM ── Environment Path ─────────────────────────────────────────────────────────
REM Hardcode paths to Python and Node to ensure they are available
set PATH=C:\Users\genaiuser\AppData\Local\Python\bin;C:\Program Files\nodejs;%PATH%

REM ── Backend ──────────────────────────────────────────────────────────────────
echo [1/4] Installing Python dependencies...
python -m pip install -q -r "%BACKEND_DIR%\requirements.txt"

echo [2/4] Starting FastAPI backend on 127.0.0.1:8000...
start "UST-Backend" cmd /k "cd /d "%BACKEND_DIR%" && python -m uvicorn main:app --host 127.0.0.1 --port 8000"

REM Brief pause so backend can bind before frontend requests
timeout /t 3 /nobreak >nul

REM ── Frontend ─────────────────────────────────────────────────────────────────
echo [3/4] Installing Node dependencies...
cd /d "%FRONTEND_DIR%"
call npm install --prefer-offline

echo [4/4] Starting Next.js dev server on http://localhost:3000...
start "UST-Frontend" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo  Dashboard : http://localhost:3000
echo  API docs  : http://127.0.0.1:8000/docs
echo.
echo  Two terminal windows opened for backend + frontend.
echo  Close them to stop the services.
echo.

endlocal
