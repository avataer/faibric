#!/bin/bash

echo "🔍 Faibric System Check"
echo "======================="
echo ""

# Check Docker
echo "1️⃣ Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo ""
    echo "   Please start Docker Desktop:"
    echo "   - Open Docker Desktop app"
    echo "   - Wait for it to fully start (icon in menu bar)"
    echo ""
    exit 1
else
    echo "✅ Docker is running"
fi

# Check Docker Compose
echo ""
echo "2️⃣ Checking Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found!"
    echo "   Install it: https://docs.docker.com/compose/install/"
    exit 1
else
    echo "✅ Docker Compose found: $(docker-compose --version)"
fi

# Check .env file
echo ""
echo "3️⃣ Checking .env file..."
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating one..."
    cat > .env << 'EOF'
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=your-key-here

# Database
POSTGRES_DB=faibric_db
POSTGRES_USER=faibric_user
POSTGRES_PASSWORD=faibric_password

# Django
SECRET_KEY=dev-secret-key-change-in-production
DEBUG=1

# Redis
REDIS_URL=redis://redis:6379/0

# App Configuration
APP_SUBDOMAIN_BASE=localhost
EOF
    echo "✅ Created .env file - PLEASE ADD YOUR OPENAI_API_KEY!"
    echo ""
    echo "   Edit .env and set: OPENAI_API_KEY=sk-your-actual-key"
    echo ""
else
    echo "✅ .env file exists"
    
    # Check if OpenAI key is set
    if grep -q "OPENAI_API_KEY=your-key-here" .env || grep -q "OPENAI_API_KEY=$" .env; then
        echo "⚠️  OpenAI API key not configured!"
        echo "   Edit .env and set: OPENAI_API_KEY=sk-your-actual-key"
        echo ""
    elif grep -q "OPENAI_API_KEY=sk-" .env; then
        echo "✅ OpenAI API key is configured"
    fi
fi

# Check if containers are running
echo ""
echo "4️⃣ Checking running containers..."
RUNNING=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)
if [ "$RUNNING" -eq 0 ]; then
    echo "⚠️  No containers running"
    echo "   Run: docker-compose up -d"
else
    echo "✅ $RUNNING containers running"
    docker-compose ps
fi

echo ""
echo "======================="
echo "✅ System check complete!"
echo ""
echo "Next steps:"
echo "1. Make sure OpenAI API key is set in .env"
echo "2. Run: docker-compose up -d --build"
echo "3. Wait 30 seconds for services to start"
echo "4. Visit: http://localhost:5173"
echo ""

