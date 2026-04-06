#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║          SPARK-Bayern — Local Setup                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

if ! command -v docker &> /dev/null || ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Open Docker Desktop and try again."
    exit 1
fi
echo "✓ Docker is running"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "📋 Created .env from .env.example"
    echo "⚠️  Edit .env and set LLM_API_KEY and DEMO_ACCESS_CODE, then run again."
    exit 1
fi

if grep -q "YOUR_REQUESTY_API_KEY_HERE" .env; then
    echo "⚠️  .env still has placeholder values. Please edit it first."
    exit 1
fi
echo "✓ .env configured"

echo ""
echo "🔨 Building (first run takes ~5 minutes)..."
docker compose build

echo ""
echo "🚀 Starting services..."
docker compose up -d

echo ""
echo "⏳ Waiting for backend to initialise (loads BayBO — ~30s)..."
sleep 15

echo ""
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✓ Backend is running"
else
    echo "  ⏳ Backend still loading... check with: docker compose logs backend"
fi
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✓ Frontend is running"
fi

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Frontend:  http://localhost:3000                    ║"
echo "║  API docs:  http://localhost:8000/docs               ║"
echo "║  Stop:      docker compose down                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
