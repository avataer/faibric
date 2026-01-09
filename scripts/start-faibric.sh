#!/bin/bash

echo "🚀 Faibric - Quick Start"
echo "========================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check Docker
echo "1️⃣ Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running!"
    echo ""
    echo "   Please start Docker Desktop and try again."
    exit 1
fi
print_success "Docker is running"

# Check .env
echo ""
echo "2️⃣ Checking environment..."
if [ ! -f .env ]; then
    print_warning "No .env file found. Creating from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success "Created .env file"
        print_warning "Please edit .env and add your OPENAI_API_KEY"
        echo "   Get your key from: https://platform.openai.com/api-keys"
        exit 1
    else
        print_error "No .env.example found!"
        exit 1
    fi
fi

# Check OpenAI key
if grep -q "OPENAI_API_KEY=your-key-here" .env || grep -q "OPENAI_API_KEY=$" .env; then
    print_warning "OpenAI API key not configured!"
    echo "   Edit .env and set: OPENAI_API_KEY=sk-your-actual-key"
    echo ""
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "OpenAI API key configured"
fi

# Stop existing containers
echo ""
echo "3️⃣ Stopping existing containers..."
docker-compose down > /dev/null 2>&1
print_success "Cleaned up"

# Build and start
echo ""
echo "4️⃣ Building and starting services..."
echo "   (This may take a few minutes on first run)"
docker-compose up -d --build

if [ $? -eq 0 ]; then
    print_success "Services started"
else
    print_error "Failed to start services"
    echo "   Check logs with: docker-compose logs"
    exit 1
fi

# Wait for services
echo ""
echo "5️⃣ Waiting for services to be ready..."
echo "   (30 seconds)"
for i in {30..1}; do
    echo -ne "   $i seconds remaining...\r"
    sleep 1
done
echo -ne "   \r"
print_success "Services should be ready"

# Check service status
echo ""
echo "6️⃣ Service status:"
docker-compose ps

# Verify frontend
echo ""
echo "7️⃣ Checking frontend..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 > /dev/null 2>&1; then
    print_success "Frontend is responding"
else
    print_warning "Frontend might still be compiling..."
    echo "   Check: docker-compose logs frontend"
fi

# Verify backend
echo ""
echo "8️⃣ Checking backend..."
if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
    print_success "Backend is responding"
else
    print_warning "Backend might not be ready yet"
    echo "   Check: docker-compose logs backend"
fi

# Final instructions
echo ""
echo "========================"
echo "🎉 Startup Complete!"
echo ""
echo "Next steps:"
echo ""
echo "1. Create a user (if you haven't already):"
echo "   docker-compose exec backend python manage.py createsuperuser"
echo ""
echo "2. Open the app:"
echo "   http://localhost:5173"
echo ""
echo "3. Login and go to /create to build your first app!"
echo ""
echo "Useful commands:"
echo "  • View logs: docker-compose logs -f"
echo "  • Stop: docker-compose down"
echo "  • Restart: ./start-faibric.sh"
echo ""

