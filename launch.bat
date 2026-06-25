@echo off
set ROOT=%~dp0
echo Starting Social Branding Agent...
echo cd /d "%ROOT%backend" > "%TEMP%\sba_back.bat"
echo uv run uvicorn app.main:app --reload --port 8000 >> "%TEMP%\sba_back.bat"
echo cd /d "%ROOT%frontend" > "%TEMP%\sba_front.bat"
echo npm run dev >> "%TEMP%\sba_front.bat"
start "SBA Backend" cmd /k "%TEMP%\sba_back.bat"
start "SBA Frontend" cmd /k "%TEMP%\sba_front.bat"
echo Waiting 15 seconds for servers to start...
timeout /t 15 /nobreak >nul
start "" "http://localhost:5173"
echo.
echo Running at http://localhost:5173
echo Close the SBA Backend and SBA Frontend windows to stop.
pause
