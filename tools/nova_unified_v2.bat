@echo off
setlocal
cd /d "%~dp0"
echo.
echo ========================================================
echo   NOVA SYSTEM AI - SIMPLISMART ARCHITECTURE
echo ========================================================
echo.
echo [1/2] Starting Nova API Core...
start "Nova API" /min python -B ..\interface\api.py
timeout /t 5 >nul

echo [2/2] Launching SimpliSmart HUD...
python -B ..\interface\gui.py

echo.
echo Closing background processes...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Nova API" >nul 2>&1
echo System Shutdown.
pause
