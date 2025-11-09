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
echo IMPORTANT: Using LOCAL configuration only
echo (Azure configurations are disabled)
echo.

REM Clear all Azure-related environment variables for this session
REM This ensures no Azure resources will be accessed
set COSMOS_DB_URI=
set COSMOS_DB_NAME=
set AZURE_STORAGE_ACCOUNT_NAME=
set AZURE_STORAGE_ACCOUNT_KEY=
set AZURE_STORAGE_CONTAINER_NAME=
set AZURE_STORAGE_CONNECTION_STRING=

REM Set local MongoDB configuration explicitly
set MONGO_URI=mongodb://localhost:27017/tododb

REM Set Flask to development/local mode
set FLASK_ENV=development
set FLASK_DEBUG=True
set PORT=5000

REM Allow CORS for local development
set CORS_ORIGINS=*

REM Start Flask backend (minimized) with local environment
start "Flask Backend" /min cmd /k "cd backend && python app.py"

REM Start Vue frontend (minimized) on port 8080
start "Vue Frontend" /min cmd /k "cd frontend && npm run serve -- --host 0.0.0.0 --port 8080"

echo Servers initiating...
echo Closing this window in 3 seconds...
timeout /t 3 /nobreak >nul
exit