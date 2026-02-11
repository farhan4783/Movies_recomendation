#!/bin/bash
# Database backup script for Movie Maverick
# Usage: ./scripts/backup.sh

set -e

BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/moviemaverick_$TIMESTAMP.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

echo "📦 Creating database backup..."

# Get database credentials from .env
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_DB=${POSTGRES_DB:-moviemaverick}

# Create backup
docker-compose exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

echo "✅ Backup created: ${BACKUP_FILE}.gz"

# Keep only last 7 backups
echo "🧹 Cleaning old backups..."
ls -t $BACKUP_DIR/*.gz | tail -n +8 | xargs -r rm

echo "✅ Backup completed successfully!"
