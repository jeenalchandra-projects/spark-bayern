#!/bin/bash
# =============================================================================
# deploy.sh — One-command local setup script
# =============================================================================
# WHAT THIS DOES:
# Checks your setup, copies the .env file, and starts all services.
#
# HOW TO RUN:
#   chmod +x deploy.sh   (makes it executable — do this once)
#   ./deploy.sh          (runs it)
# =============================================================================

set -e  # Stop if any command fails

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║          SPARK-Bayern — Local Setup                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# --- Check Docker ---
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not running."
    echo "   Please open Docker Desktop and wait for it to start."
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is installed but not running."
    echo "   Please open Docker Desktop and wait for the whale icon to appear."
    exit 1
fi

echo "✓ Docker is running"

# --- Check .env file ---
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo ""
        echo "📋 Created .env from .env.example"
        echo ""
        echo "⚠️  IMPORTANT: You must edit .env and fill in:"
        echo "   LLM_API_KEY=your-requesty-api-key"
        echo "   DEMO_ACCESS_CODE=your-chosen-passphrase"
        echo ""
        echo "   Edit the file: open .env"
        echo "   Then run this script again."
        exit 1
    else
        echo "❌ No .env file found. Please create one from .env.example"
        exit 1
    fi
fi

# --- Check .env has been filled in ---
if grep -q "YOUR_REQUESTY_API_KEY_HERE" .env; then
    echo ""
    echo "⚠️  Your .env file still has placeholder values."
    echo "   Please edit .env and replace:"
    echo "   LLM_API_KEY=YOUR_REQUESTY_API_KEY_HERE"
    echo "   DEMO_ACCESS_CODE=YOUR_CHOSEN_PASSPHRASE_HERE"
    echo ""
    exit 1
fi

echo "✓ .env file found and configured"

# --- Build and start ---
echo ""
echo "🔨 Building Docker images (first time takes 3-5 minutes)..."
echo ""
docker compose build

echo ""
echo "🚀 Starting services..."
echo ""
docker compose up -d

# --- Wait for health checks ---
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# --- Check all services ---
check_service() {
    local name=$1
    local url=$2
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "  ✓ $name is running"
    else
        echo "  ⚠ $name may still be starting... (check: docker compose logs $name)"
    fi
}

check_service "API Gateway" "http://localhost:8000/health"
check_service "Quality Service" "http://localhost:8001/health"
check_service "Translation Service" "http://localhost:8003/health"
check_service "Frontend" "http://localhost:3000"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  SPARK-Bayern is running!                            ║"
echo "║                                                      ║"
echo "║  Frontend:    http://localhost:3000                  ║"
echo "║  API Docs:    http://localhost:8000/docs             ║"
echo "║  RAG Service: http://localhost:8002/docs             ║"
echo "║                                                      ║"
echo "║  To stop:  docker compose down                       ║"
echo "║  Logs:     docker compose logs -f                    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
