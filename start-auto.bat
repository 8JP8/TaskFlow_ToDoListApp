@echo off
title MongoDB-Flask-Vue Auto-Launcher
echo ==============================================
echo   Starting MongoDB-Flask-Vue Demo
echo   Servers initiating... please wait
echo ==============================================
echo.
echo Flask backend and Vue frontend will start minimized.
echo You can access the app from any storage in the network.
echo.
echo To find your server IP, run: ipconfig
echo.

REM Start Flask backend (minimized)
start "Flask Backend" /min cmd /k "cd backend && python app.py"

REM Start Vue frontend (minimized)
start "Vue Frontend" /min cmd /k "cd frontend && npm run serve -- --host 0.0.0.0"

echo Servers initiating...
echo Closing this window in 3 seconds...
timeout /t 3 /nobreak >nul
exit