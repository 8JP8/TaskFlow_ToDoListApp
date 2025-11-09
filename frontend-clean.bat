@echo off
echo ==============================================
echo   Frontend Clean and Reinstall Script
echo ==============================================
echo.
echo This will clean and reinstall all npm dependencies
echo.

cd frontend

echo Step 1: Removing node_modules...
if exist node_modules (
    rmdir /s /q node_modules
    echo   [OK] node_modules removed
) else (
    echo   [INFO] node_modules not found
)

echo.
echo Step 2: Removing package-lock.json...
if exist package-lock.json (
    del package-lock.json
    echo   [OK] package-lock.json removed
) else (
    echo   [INFO] package-lock.json not found
)

echo.
echo Step 3: Cleaning npm cache...
call npm cache clean --force
echo   [OK] npm cache cleaned

echo.
echo Step 4: Reinstalling all dependencies...
echo   This may take a few minutes...
call npm install --legacy-peer-deps

echo.
echo Step 5: Verifying critical packages...
call npm list @vue/cli-plugin-babel --depth=0 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   [OK] @vue/cli-plugin-babel is installed
) else (
    echo   [WARNING] @vue/cli-plugin-babel may not be installed correctly
    echo   Attempting to reinstall...
    call npm install @vue/cli-plugin-babel@~5.0.0 --save-dev --legacy-peer-deps
)

echo.
echo ==============================================
echo   Installation Complete!
echo ==============================================
echo.
echo You can now run the application with start-auto.bat
echo.
pause

