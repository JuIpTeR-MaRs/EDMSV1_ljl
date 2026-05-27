@echo off
setlocal EnableDelayedExpansion

:: EDMS Docker Build Script for Windows
:: This script prepares runtime files in bin/ directory and builds Docker images

set SCRIPT_DIR=%~dp0
set BIN_DIR=%SCRIPT_DIR%..\bin\
set DATA_DIR=%BIN_DIR%data\
set ENV_FILE=%BIN_DIR%.env
set COMPOSE_FILE=%SCRIPT_DIR%docker-compose.yml

echo ============================================
echo    EDMS Docker Build Script
echo ============================================
echo.

:: Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

:: Check if Docker is running
docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker daemon is not running
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

:: Check if docker-compose is available
where docker-compose >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set COMPOSE_CMD=docker-compose
) else (
    docker compose version >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set COMPOSE_CMD=docker compose
    ) else (
        echo ERROR: docker-compose is not installed
        pause
        exit /b 1
    )
)

:: Sync or create .env file in bin/ directory
if exist "%SCRIPT_DIR%.env" (
    echo Copying .env file from docker/ directory to bin/...
    copy /y "%SCRIPT_DIR%.env" "%ENV_FILE%" >nul
    echo [OK] Synced .env file
    echo.
) else (
    if not exist "%ENV_FILE%" (
        echo Creating .env file in bin/ directory from template...
        copy "%SCRIPT_DIR%.env.example" "%ENV_FILE%" >nul
        if exist "%ENV_FILE%" (
            echo [OK] Created .env file from template
            
            :: Auto-generate JWT_SECRET_KEY if empty
            for /f "tokens=2 delims==" %%a in ('findstr "JWT_SECRET_KEY=" "%ENV_FILE%"') do (
                set "CURRENT_JWT=%%a"
            )
            if "!CURRENT_JWT!"=="" (
                echo Auto-generating JWT_SECRET_KEY...
                set "JWT_KEY="
                for /l %%i in (1,1,32) do (
                    set /a "rand=!random! %% 16"
                    for %%j in (!rand!) do set "JWT_KEY=!JWT_KEY!0123456789abcdef:~%%j,1"
                )
                findstr /v "^JWT_SECRET_KEY=" "%ENV_FILE%" > "%ENV_FILE%.tmp"
                echo JWT_SECRET_KEY=!JWT_KEY! >> "%ENV_FILE%.tmp"
                move /y "%ENV_FILE%.tmp" "%ENV_FILE%" >nul
                echo [OK] JWT_SECRET_KEY generated
            )
            echo.
        ) else (
            echo ERROR: Failed to create .env file
            echo Source: %SCRIPT_DIR%.env.example
            echo Destination: %ENV_FILE%
            pause
            exit /b 1
        )
    ) else (
        echo [OK] .env file already exists in bin/ directory
        echo.
    )
)

:: Create data directory in bin/ directory if it doesn't exist
if not exist "%DATA_DIR%" (
    echo Creating data directory in bin/ directory...
    mkdir "%DATA_DIR%"
    mkdir "%DATA_DIR%\backend"
    echo [OK] Created data directory
    echo.
) else (
    echo [OK] Data directory already exists in bin/ directory
    echo.
)

:: Generate local SSL certificates if needed
echo Checking for SSL certificates...
set "ROOT_DIR=%SCRIPT_DIR%..\..\"
set "CERTS_DIR=%SCRIPT_DIR%certs"
set "BIN_CERTS_DIR=%BIN_DIR%certs"

mkdir "%CERTS_DIR%" 2>nul
mkdir "%BIN_CERTS_DIR%" 2>nul

if not exist "%CERTS_DIR%\fullchain.pem" (
    if exist "%ROOT_DIR%localhost+2.pem" (
        echo [SSL] Found local development certificates in root, copying them...
        copy "%ROOT_DIR%localhost+2.pem" "%CERTS_DIR%\fullchain.pem" >nul
        copy "%ROOT_DIR%localhost+2-key.pem" "%CERTS_DIR%\privkey.pem" >nul
    ) else (
        set "MKCERT_PATH="
        if exist "%ROOT_DIR%mkcert.exe" (
            set "MKCERT_PATH=%ROOT_DIR%mkcert.exe"
        ) else (
            where mkcert >nul 2>nul
            if %ERRORLEVEL% EQU 0 set "MKCERT_PATH=mkcert"
        )

        if not "!MKCERT_PATH!"=="" (
            echo [SSL] Generating local certificates using !MKCERT_PATH!...
            pushd "%CERTS_DIR%"
            "!MKCERT_PATH!" localhost 127.0.0.1 ::1
            if exist "localhost+2.pem" (
                move /y "localhost+2.pem" "fullchain.pem" >nul
                move /y "localhost+2-key.pem" "privkey.pem" >nul
                echo [SSL] Local SSL certificates generated successfully in certs/ directory
            ) else (
                echo [SSL] Warning: mkcert ran but did not output expected files
            )
            popd
        ) else (
            echo [SSL] Warning: mkcert.exe not found. You will need to manually place fullchain.pem and privkey.pem in certs/ directory.
        )
    )
) else (
    echo [SSL] SSL certificates already exist in certs/ directory
)

:: Copy certs to bin/certs/ directory for runtime deployment
if exist "%CERTS_DIR%\fullchain.pem" (
    echo Copying certificates to bin/certs/ directory...
    copy "%CERTS_DIR%\fullchain.pem" "%BIN_CERTS_DIR%\fullchain.pem" >nul
    copy "%CERTS_DIR%\privkey.pem" "%BIN_CERTS_DIR%\privkey.pem" >nul
    echo [SSL] Certificates copied to bin/certs/ directory
)
echo.

:: Build Docker images
echo Building Docker images...
echo This may take a while on first run...
echo.
%COMPOSE_CMD% -f "%COMPOSE_FILE%" build
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build Docker images
    pause
    exit /b 1
)

:: Export images to bin/images/ directory
echo.
echo Exporting Docker images to bin/images/ directory...
mkdir "%BIN_DIR%images" 2>nul
docker save edms-backend:latest -o "%BIN_DIR%images/edms-backend.tar"
if %ERRORLEVEL% EQU 0 (
    echo [OK] Exported edms-backend.tar
) else (
    echo ERROR: Failed to export edms-backend
    pause
    exit /b 1
)

docker save edms-frontend:latest -o "%BIN_DIR%images/edms-frontend.tar"
if %ERRORLEVEL% EQU 0 (
    echo [OK] Exported edms-frontend.tar
) else (
    echo ERROR: Failed to export edms-frontend
    pause
    exit /b 1
)

:: Copy docker-compose.yml to bin/ directory for runtime
echo Copying docker-compose.yml to bin/ directory...
copy "%COMPOSE_FILE%" "%BIN_DIR%docker-compose.yml" >nul
if exist "%BIN_DIR%docker-compose.yml" (
    echo [OK] docker-compose.yml copied to bin/ directory
) else (
    echo ERROR: Failed to copy docker-compose.yml
    pause
    exit /b 1
)

:: Copy frontend configuration for SSL to bin/ directory
echo Copying frontend SSL configuration to bin/ directory...
mkdir "%BIN_DIR%frontend" 2>nul
copy "%SCRIPT_DIR%frontend\nginx.ssl.conf" "%BIN_DIR%frontend\nginx.ssl.conf" >nul
if exist "%BIN_DIR%frontend\nginx.ssl.conf" (
    echo [OK] Nginx SSL configuration copied to bin/ directory
) else (
    echo ERROR: Failed to copy Nginx SSL configuration
    pause
    exit /b 1
)

echo.
echo ============================================
echo    EDMS Build Complete!
echo ============================================
echo.
echo Runtime files created in:
echo   %BIN_DIR%
echo.
echo Files:
echo   - .env (environment configuration)
echo   - data/ (persistent data)
echo.
echo Next steps:
echo   1. Run bin\Windows\start.bat to start the services
echo   2. Access the application at http://localhost
echo.
echo To rebuild:
echo   Run this script again
echo.
echo To clean up:
echo   %COMPOSE_CMD% -f "%COMPOSE_FILE%" down -v
echo.

pause
