#!/bin/bash
# Deployment script for Movie Maverick
# Usage: ./scripts/deploy.sh [environment]

set -e  # Exit on error

ENVIRONMENT=${1:-production}

echo "🚀 Deploying Movie Maverick to $ENVIRONMENT..."

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check required environment variables
required_vars=("SECRET_KEY" "POSTGRES_PASSWORD" "TMDB_API_KEY" "GEMINI_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Error: $var is not set in .env file"
        exit 1
    fi
done

echo "✅ Environment variables validated"

# Build Docker images
echo "🔨 Building Docker images..."
docker-compose build

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down

# Start services
echo "🚀 Starting services..."
docker-compose up -d

# Wait for database to be ready
echo "⏳ Waiting for database..."
sleep 10

# Run database migrations
echo "📊 Running database migrations..."
docker-compose exec web flask db upgrade

# Check health
echo "🏥 Checking application health..."
sleep 5
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Application is healthy!"
else
    echo "❌ Application health check failed"
    docker-compose logs web
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo "📝 Application is running at http://localhost:5000"
echo "📊 View logs with: docker-compose logs -f"
