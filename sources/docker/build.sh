#!/bin/bash

# EDMS Docker Build Script for Linux/macOS
# This script prepares runtime files in bin/ directory and builds Docker images

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BIN_DIR="$(dirname "$SCRIPT_DIR")/bin/"
DATA_DIR="$BIN_DIR/data"
ENV_FILE="$BIN_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

echo "============================================"
echo "   EDMS Docker Build Script"
echo "============================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    echo "Please install Docker from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "ERROR: Docker daemon is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "[OK] Docker is running"
echo ""

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "ERROR: docker-compose is not installed"
    exit 1
fi

# Sync or create .env file from project root
ROOT_ENV_FILE="$SCRIPT_DIR/../../.env"
ROOT_ENV_EXAMPLE="$SCRIPT_DIR/../../.env.example"

if [ ! -f "$ROOT_ENV_FILE" ]; then
    if [ -f "$ROOT_ENV_EXAMPLE" ]; then
        echo "Creating .env file in project root from template..."
        cp "$ROOT_ENV_EXAMPLE" "$ROOT_ENV_FILE"
        echo "[OK] Created .env file in project root"
        
        # Auto-generate JWT_SECRET_KEY if empty
        if grep -q "^JWT_SECRET_KEY=$" "$ROOT_ENV_FILE" || ! grep -q "^JWT_SECRET_KEY=" "$ROOT_ENV_FILE"; then
            echo "Auto-generating JWT_SECRET_KEY..."
            JWT_KEY=$(openssl rand -hex 32)
            grep -v "^JWT_SECRET_KEY=" "$ROOT_ENV_FILE" > "$ROOT_ENV_FILE.tmp" || true
            echo "JWT_SECRET_KEY=$JWT_KEY" >> "$ROOT_ENV_FILE.tmp"
            mv "$ROOT_ENV_FILE.tmp" "$ROOT_ENV_FILE"
            echo "[OK] JWT_SECRET_KEY generated"
        fi
    else
        echo "ERROR: Project root .env.example template not found!"
        exit 1
    fi
fi

echo "Copying .env file from project root directory to bin/..."
cp "$ROOT_ENV_FILE" "$ENV_FILE"
echo "Copying .env file from project root directory to docker/..."
cp "$ROOT_ENV_FILE" "$SCRIPT_DIR/.env"
echo "[OK] Synced .env file to bin/ and docker/ directories"
echo ""

# Create data directory in bin/ directory if it doesn't exist
if [ ! -d "$DATA_DIR" ]; then
    echo "Creating data directory in bin/ directory..."
    mkdir -p "$DATA_DIR/backend"
    echo "[OK] Created data directory"
    echo ""
else
    echo "[OK] Data directory already exists in bin/ directory"
    echo ""
fi

# Generate local SSL certificates if needed
echo "Checking for SSL certificates..."
ROOT_DIR="$SCRIPT_DIR/../.."
CERTS_DIR="$SCRIPT_DIR/certs"
BIN_CERTS_DIR="$BIN_DIR/certs"

mkdir -p "$CERTS_DIR"
mkdir -p "$BIN_CERTS_DIR"

if [ ! -f "$CERTS_DIR/fullchain.pem" ]; then
    if [ -f "$ROOT_DIR/localhost+2.pem" ]; then
        echo "[SSL] Found local development certificates in root, copying them..."
        cp "$ROOT_DIR/localhost+2.pem" "$CERTS_DIR/fullchain.pem"
        cp "$ROOT_DIR/localhost+2-key.pem" "$CERTS_DIR/privkey.pem"
    else
        MKCERT_PATH=""
        if [ -f "$ROOT_DIR/mkcert" ]; then
            MKCERT_PATH="$ROOT_DIR/mkcert"
        elif [ -f "$ROOT_DIR/mkcert.exe" ]; then
            MKCERT_PATH="$ROOT_DIR/mkcert.exe"
        elif command -v mkcert &> /dev/null; then
            MKCERT_PATH="mkcert"
        fi

        if [ ! -z "$MKCERT_PATH" ]; then
            echo "[SSL] Generating local certificates using $MKCERT_PATH..."
            (cd "$CERTS_DIR" && "$MKCERT_PATH" localhost 127.0.0.1 ::1)
            if [ -f "$CERTS_DIR/localhost+2.pem" ]; then
                mv "$CERTS_DIR/localhost+2.pem" "$CERTS_DIR/fullchain.pem"
                mv "$CERTS_DIR/localhost+2-key.pem" "$CERTS_DIR/privkey.pem"
                echo "[SSL] Local SSL certificates generated successfully in certs/ directory"
            else
                echo "[SSL] Warning: mkcert ran but did not output expected files"
            fi
        else
            echo "[SSL] Warning: mkcert not found. You will need to manually place fullchain.pem and privkey.pem in certs/ directory."
        fi
    fi
else
    echo "[SSL] SSL certificates already exist in certs/ directory"
fi

# Copy certs to bin/certs/ directory for runtime deployment
if [ -f "$CERTS_DIR/fullchain.pem" ]; then
    echo "Copying certificates to bin/certs/ directory..."
    cp "$CERTS_DIR/fullchain.pem" "$BIN_CERTS_DIR/fullchain.pem"
    cp "$CERTS_DIR/privkey.pem" "$BIN_CERTS_DIR/privkey.pem"
    echo "[SSL] Certificates copied to bin/certs/ directory"
fi
echo ""

# Build Docker images
echo "Building Docker images..."
echo "This may take a while on first run..."
echo ""
$COMPOSE_CMD -f "$COMPOSE_FILE" build
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build Docker images"
    exit 1
fi

# Export images to bin/images/ directory
echo ""
echo "Exporting Docker images to bin/images/ directory..."
mkdir -p "$BIN_DIR/images"
docker save edms-backend:latest -o "$BIN_DIR/images/edms-backend.tar"
if [ $? -eq 0 ]; then
    echo "[OK] Exported edms-backend.tar"
else
    echo "ERROR: Failed to export edms-backend"
    exit 1
fi

docker save edms-frontend:latest -o "$BIN_DIR/images/edms-frontend.tar"
if [ $? -eq 0 ]; then
    echo "[OK] Exported edms-frontend.tar"
else
    echo "ERROR: Failed to export edms-frontend"
    exit 1
fi

# Copy docker-compose.yml to bin/ directory for runtime
echo "Copying docker-compose.yml to bin/ directory..."
cp "$COMPOSE_FILE" "$BIN_DIR/docker-compose.yml"
if [ -f "$BIN_DIR/docker-compose.yml" ]; then
    echo "[OK] docker-compose.yml copied to bin/ directory"
else
    echo "ERROR: Failed to copy docker-compose.yml"
    exit 1
fi

# Copy frontend configuration for SSL to bin/ directory
echo "Copying frontend SSL configuration to bin/ directory..."
mkdir -p "$BIN_DIR/frontend"
cp "$SCRIPT_DIR/frontend/nginx.ssl.conf" "$BIN_DIR/frontend/nginx.ssl.conf"
if [ -f "$BIN_DIR/frontend/nginx.ssl.conf" ]; then
    echo "[OK] Nginx SSL configuration copied to bin/ directory"
else
    echo "ERROR: Failed to copy Nginx SSL configuration"
    exit 1
fi

echo ""
echo "============================================"
echo "   EDMS Build Complete!"
echo "============================================"
echo ""
echo "Runtime files created in:"
echo "  $BIN_DIR"
echo ""
echo "Files:"
echo "  - .env (environment configuration)"
echo "  - data/ (persistent data)"
echo ""
echo "Next steps:"
echo "  1. Run bin/Linux/start.sh to start the services"
echo "  2. Access the application at http://localhost"
echo ""
echo "To rebuild:"
echo "  Run this script again"
echo ""
echo "To clean up:"
echo "  $COMPOSE_CMD -f \"$COMPOSE_FILE\" down -v"
echo ""

# Wait for user to see the message
read -p "Press Enter to continue..."
