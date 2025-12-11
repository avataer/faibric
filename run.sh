#!/bin/bash

# Faibric - Complete Setup and Start Script
# This script will set up and run your Faibric platform

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  🎨 FAIBRIC - AI-Powered No-Code Platform"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker and try again"
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Navigate to project directory
cd "$(dirname "$0")"

# Step 1: Environment setup
echo "📝 Step 1: Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   ✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: You need to add your OpenAI API key!"
    echo ""
    echo "   1. Get your API key from: https://platform.openai.com/api-keys"
    echo "   2. Edit .env file and replace 'your_openai_api_key_here'"
    echo "   3. Run this script again"
    echo ""
    echo "   Quick edit: nano .env"
    echo ""
    exit 0
else
    if grep -q "your_openai_api_key_here" .env; then
        echo "⚠️  WARNING: OpenAI API key not configured!"
        echo "   The AI features won't work without a valid API key."
        echo "   Edit .env and add your OpenAI API key, then run this script again."
        echo ""
        read -p "   Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    else
        echo "   ✓ Environment configured"
    fi
fi
echo ""

# Step 2: Clean up old containers
echo "🧹 Step 2: Cleaning up old containers..."
docker-compose down -v 2>/dev/null || true
echo "   ✓ Cleanup complete"
echo ""

# Step 3: Build and start services
echo "🏗️  Step 3: Building Docker images..."
echo "   This may take 5-10 minutes on first run..."
echo ""
docker-compose build --no-cache

echo ""
echo "🚀 Step 4: Starting services..."
docker-compose up -d

echo ""
echo "⏳ Step 5: Waiting for services to initialize..."
echo "   This usually takes 30-60 seconds..."

# Wait for PostgreSQL
echo -n "   Waiting for PostgreSQL."
for i in {1..30}; do
    if docker-compose exec -T postgres pg_isready -U faibric_user > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

# Wait for backend
echo -n "   Waiting for Django backend."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/auth/login/ > /dev/null 2>&1; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

echo ""
echo "✅ Services are running!"
echo ""

# Step 6: Database setup
echo "📊 Step 6: Setting up database..."
docker-compose exec -T backend python manage.py migrate
echo "   ✓ Database migrations complete"
echo ""

# Step 7: Check service status
echo "🔍 Step 7: Service Status"
echo ""
docker-compose ps
echo ""

# Final instructions
echo "═══════════════════════════════════════════════════════════"
echo "  ✨ FAIBRIC IS READY!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🌐 Access Points:"
echo "   • Frontend:  http://localhost:5173"
echo "   • Backend:   http://localhost:8000"
echo "   • API Docs:  http://localhost:8000/api/"
echo "   • Admin:     http://localhost:8000/admin"
echo ""
echo "👤 Next: Create an admin user"
echo "   docker-compose exec backend python manage.py createsuperuser"
echo ""
echo "📚 Documentation:"
echo "   • Quick Start:  START-HERE.md"
echo "   • Full Docs:    README.md"
echo "   • Summary:      PROJECT-COMPLETE.md"
echo ""
echo "🛠️  Useful Commands:"
echo "   • View logs:    docker-compose logs -f"
echo "   • Stop:         docker-compose down"
echo "   • Restart:      docker-compose restart"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Happy building! 🎨🚀"
echo ""

