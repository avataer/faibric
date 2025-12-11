#!/bin/bash
set -e

echo "🚀 Starting Faibric..."
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your OpenAI API key!"
    echo "   Open .env and replace 'your_openai_api_key_here' with your actual key"
    echo ""
fi

# Clean up old containers
echo "🧹 Cleaning up old containers..."
docker-compose down -v 2>/dev/null || true
echo ""

# Build and start services
echo "🏗️  Building and starting services..."
echo "   This may take a few minutes on first run..."
echo ""
docker-compose up -d --build

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to start..."
sleep 10

# Check if backend is up
echo ""
echo "🔍 Checking service status..."
docker-compose ps

echo ""
echo "✅ Services started!"
echo ""
echo "Next steps:"
echo "1. Run migrations:"
echo "   docker-compose exec backend python manage.py migrate"
echo ""
echo "2. Create superuser:"
echo "   docker-compose exec backend python manage.py createsuperuser"
echo ""
echo "3. Access the application:"
echo "   - Frontend: http://localhost:5173"
echo "   - Backend API: http://localhost:8000"
echo "   - Admin Panel: http://localhost:8000/admin"
echo ""
echo "📝 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"
echo ""

