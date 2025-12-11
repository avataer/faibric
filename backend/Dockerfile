FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . /app/

# Create directories and collect static files
RUN mkdir -p /app/media /app/staticfiles
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 10000

# Run migrations and start server with gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn faibric_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2"]

