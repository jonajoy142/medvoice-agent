#!/bin/bash
set -e

echo "Starting MedVoice AI - Full System..."
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Start backend in background
echo "Starting backend server..."
cd "$ROOT_DIR/backend"
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 5

# Check if backend is healthy
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# Start frontend
echo "Starting frontend..."
cd "$ROOT_DIR/frontend"

if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

echo ""
echo "🎉 MedVoice AI is starting up!"
echo ""
echo "📍 Frontend: http://localhost:3000"
echo "📍 Backend API: http://localhost:8000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
