# Quick Setup Guide

## Prerequisites
- Docker & Docker Compose
- OpenAI API key

## Setup Steps

1. **Clone/Navigate to project**
   ```bash
   cd ~/Code/Faibric
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Add your OPENAI_API_KEY
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Create superuser**
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

5. **Access the app**
   - Frontend: http://localhost:5173
   - Admin: http://localhost:8000/admin

## That's it! 🚀

For more details, see README.md
