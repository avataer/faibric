#!/bin/bash
# Start Faibric locally for development
# Client websites will still deploy to Render.com

set -e

echo "🚀 Starting Faibric Local Development"
echo "======================================"

# Check for required env vars
if [ ! -f ".env" ]; then
    echo "❌ Missing .env file. Copy from .env.example and fill in values."
    exit 1
fi

# Load env vars
export $(cat .env | grep -v '^#' | xargs)

# Check critical vars
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ANTHROPIC_API_KEY not set in .env"
    exit 1
fi

if [ -z "$RENDER_API_KEY" ]; then
    echo "⚠️  RENDER_API_KEY not set - client deploys won't work"
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN not set - client deploys won't work"
fi

echo ""
echo "Starting services..."
echo ""

# Start PostgreSQL and Redis with Docker
docker-compose -f docker-compose.local.yml up -d

# Wait for DB
echo "Waiting for PostgreSQL..."
sleep 3

# Run migrations
cd backend
python manage.py migrate --noinput

# Start backend (in background)
echo "Starting backend on http://localhost:8000"
python manage.py runserver 0.0.0.0:8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
echo "Starting frontend on http://localhost:5173"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "======================================"
echo "✅ Faibric running locally!"
echo ""
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo ""
echo "   Client websites deploy to Render.com"
echo ""
echo "Press Ctrl+C to stop"
echo "======================================"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker-compose stop db redis; exit 0" SIGINT SIGTERM
wait


