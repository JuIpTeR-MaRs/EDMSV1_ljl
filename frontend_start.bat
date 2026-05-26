@echo off
REM Start EDMS frontend service (manual deployment)
echo Starting EDMS frontend service...

REM Change to frontend directory
cd /d "%~dp0"

REM Check and generate local SSL certificates if missing
if not exist "localhost+2.pem" (
    if exist "mkcert.exe" (
        echo ============================================================
        echo [SSL] Local development certificates not found.
        echo [SSL] Generating certificates using mkcert.exe...
        mkcert.exe localhost 127.0.0.1 ::1
        echo [SSL] Certificates generated successfully.
        echo [SSL] IMPORTANT: If this is the first time on this device,
        echo       please run "mkcert.exe -install" in an ADMINISTRATOR
        echo       terminal to make your system trust these certificates.
        echo ============================================================
        echo.
    ) else (
        echo [SSL] mkcert.exe not found. Frontend will run in HTTP mode.
        echo.
    )
)

cd sources\frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing npm dependencies...
    
    REM Check if cnpm is available, otherwise use npm with legacy peer deps
    where cnpm >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo Using cnpm...
        cnpm install
    ) else (
        echo Using npm with --legacy-peer-deps...
        npm install --legacy-peer-deps
    )
    
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install dependencies!
        pause
        exit /b %ERRORLEVEL%
    )
)

REM Start Vue development server
echo Starting Vue frontend on http://localhost:5173

where cnpm >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Using cnpm run dev...
    cnpm run dev
) else (
    echo Using npm run dev...
    npm run dev
)

if %ERRORLEVEL% NEQ 0 (
    echo Frontend failed to start!
    pause
    exit /b %ERRORLEVEL%
)