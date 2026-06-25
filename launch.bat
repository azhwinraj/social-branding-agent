@echo off
setlocal enabledelayedexpansion
set ROOT=%~dp0

echo Social Branding Agent
echo ---------------------

REM Check dependencies
where python >nul 2>&1 || (echo ERROR: python not found. Install Python 3.12+ from python.org && pause && exit /b 1)
where node >nul 2>&1 || (echo ERROR: node not found. Install Node.js 18+ from nodejs.org && pause && exit /b 1)
where uv >nul 2>&1 || (echo ERROR: uv not found. Run: powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex" && pause && exit /b 1)

REM First-run: install backend deps
if not exist "%ROOT%backend\.venv" (
    echo Installing backend dependencies (first run)...
    cd /d "%ROOT%backend"
    uv sync
    if errorlevel 1 (echo Backend install failed. && pause && exit /b 1)
    cd /d "%ROOT%"
)

REM First-run: install frontend deps
if not exist "%ROOT%frontend\node_modules" (
    echo Installing frontend dependencies (first run)...
    cd /d "%ROOT%frontend"
    npm install --silent
    if errorlevel 1 (echo Frontend install failed. && pause && exit /b 1)
    cd /d "%ROOT%"
)

REM First-run: bootstrap .env
if not exist "%ROOT%.env" (
    if exist "%ROOT%.env.example" (
        copy "%ROOT%.env.example" "%ROOT%.env" >nul
        echo.
        echo   .env created. Open it and add at least GROQ_API_KEY, then re-run this script.
        echo.
        pause
        exit /b 0
    )
)

REM Apply pending DB migrations
cd /d "%ROOT%backend"
uv run alembic upgrade head >nul 2>&1
cd /d "%ROOT%"

REM Start backend in new window
start "Backend" cmd /k "cd /d "%ROOT%backend" && uv run uvicorn app.main:app --reload --port 8000"

REM Start frontend in new window
start "Frontend" cmd /k "cd /d "%ROOT%frontend" && npm run dev"

REM Wait for backend then open browser
echo Waiting for backend to be ready...
:wait
timeout /t 2 /nobreak >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 goto wait

start "" "http://localhost:5173"
echo.
echo Running at http://localhost:5173
echo Close the Backend and Frontend windows to stop.
