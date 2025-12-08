@echo off
setlocal enabledelayedexpansion

:: Set Project Root
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

echo ==========================================
echo      Nexus Core v2.0 - Launcher
echo ==========================================

:: ------------------------------------------------------------------
:: 1. FIND NPM
:: ------------------------------------------------------------------
set "NPM_EXEC=npm"

:: Check if npm is in PATH
where npm >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Found npm in PATH.
) else (
    echo [WARNING] npm not in PATH. Checking default install location...
    if exist "C:\Program Files\nodejs\npm.cmd" (
        set "NPM_EXEC=call "C:\Program Files\nodejs\npm.cmd""
        set "PATH=%PATH%;C:\Program Files\nodejs"
        echo [INFO] Using explicit path: !NPM_EXEC!
    ) else (
        echo [ERROR] Node.js not found. Please install from https://nodejs.org/
        pause
        exit /b
    )
)

:: ------------------------------------------------------------------
:: 2. BACKEND LAUNCH
:: ------------------------------------------------------------------
echo.
echo [BACKEND] Starting...
cd backend
if not exist "venv" (
    echo [BACKEND] Creating venv...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
)

:: Check for .env file or environment variable
set "API_KEY_SET=0"
if exist "%PROJECT_ROOT%backend\.env" (
    echo [INFO] Found .env file in backend directory.
    set "API_KEY_SET=1"
) else (
    if defined GEMINI_API_KEY (
        echo [INFO] GEMINI_API_KEY found in environment.
        set "API_KEY_SET=1"
    ) else (
        echo [WARNING] GEMINI_API_KEY not found. Please create backend\.env file or set GEMINI_API_KEY environment variable.
        echo [WARNING] LLM features will be disabled. See README.md for setup instructions.
    )
)

:: Use /D to set working directory safely
start "Nexus Backend" /D "%PROJECT_ROOT%backend" cmd /k "venv\Scripts\activate && uvicorn main:app --reload"

:: ------------------------------------------------------------------
:: 3. FRONTEND LAUNCH
:: ------------------------------------------------------------------
echo.
echo [FRONTEND] Starting...
cd "%PROJECT_ROOT%frontend"

if not exist "node_modules" (
    echo [FRONTEND] Installing dependencies...
    
    :: Use call to ensure control returns to this script
    echo [EXEC] call !NPM_EXEC! install
    call !NPM_EXEC! install
    
    :: Check success by looking for the folder, as exit codes can be flaky with warnings
    if not exist "node_modules" (
        echo [ERROR] npm install failed. node_modules folder not created.
        pause
        exit /b
    ) else (
        echo [SUCCESS] Dependencies installed.
    )
)

echo [FRONTEND] Launching Server...
:: We construct the run command carefully
set "FRONTEND_CMD=%NPM_EXEC% run dev"

start "Nexus Frontend" /D "%PROJECT_ROOT%frontend" cmd /k "!FRONTEND_CMD! || pause"

:: ------------------------------------------------------------------
:: 4. BROWSER LAUNCH
:: ------------------------------------------------------------------
cd "%PROJECT_ROOT%"
echo.
echo [INFO] Waiting for servers...
timeout /t 5 > nul
start http://localhost:5173

echo.
echo ==========================================
echo Nexus Core is running.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo ==========================================
pause
