#!/bin/bash
# Database initialization script
# Usage: ./scripts/init_db.sh

set -e

echo "🗄️  Initializing database..."

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 5

# Initialize Flask-Migrate
echo "📝 Initializing Flask-Migrate..."
docker-compose exec web flask db init || echo "Migration folder already exists"

# Create initial migration
echo "📝 Creating initial migration..."
docker-compose exec web flask db migrate -m "Initial migration"

# Apply migrations
echo "📊 Applying migrations..."
docker-compose exec web flask db upgrade

# Create initial data (achievements, etc.)
echo "🎯 Creating initial data..."
docker-compose exec web python -c "
from app import app
from model import db
from utils.achievements import initialize_achievements

with app.app_context():
    initialize_achievements()
    print('✅ Initial data created')
"

echo "✅ Database initialization completed!"
