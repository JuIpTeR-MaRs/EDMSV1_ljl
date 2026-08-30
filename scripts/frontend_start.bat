@echo off
REM Start EDMS frontend service (manual deployment)
echo Starting EDMS frontend service...

REM Set root directory
set "ROOT_DIR=%~dp0..\"
cd /d "%ROOT_DIR%"

REM Check and generate local SSL certificates if missing
if not exist "certs\localhost+2.pem" if not exist "localhost+2.pem" (
    if exist "tools\mkcert\mkcert.exe" (
        echo ============================================================
        echo [SSL] Local development certificates not found.
        echo [SSL] Generating certificates using mkcert.exe in certs/...
        if not exist "certs" mkdir certs
        cd certs
        ..\tools\mkcert\mkcert.exe localhost 127.0.0.1 ::1
        cd ..
        echo [SSL] Certificates generated successfully.
        echo ============================================================
        echo.
    ) else if exist "mkcert.exe" (
        echo [SSL] Generating certificates using mkcert.exe...
        mkcert.exe localhost 127.0.0.1 ::1
    ) else (
        echo [SSL] mkcert.exe not found. Frontend will run in HTTP mode.
        echo.
    )
)

cd "%ROOT_DIR%sources\frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing npm dependencies...
    
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