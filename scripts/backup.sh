#!/bin/bash
# Database Backup Script
#
# Usage: ./scripts/backup.sh [backup_name]
# Example: ./scripts/backup.sh pre-deployment

set -e

BACKUP_NAME=${1:-$(date +%Y%m%d_%H%M%S)}
BACKUP_DIR="./backups"
COMPOSE_FILE="docker-compose.prod.yml"

# Load environment variables
if [ -f ".env.production" ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

echo "📦 Creating database backup: $BACKUP_NAME"
echo "=================================================="

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
echo "Backing up PostgreSQL database..."
docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump \
    -U ${POSTGRES_USER:-fba_user} \
    -d ${POSTGRES_DB:-fba_production} \
    --clean --if-exists \
    > $BACKUP_DIR/postgres_${BACKUP_NAME}.sql

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL backup created: $BACKUP_DIR/postgres_${BACKUP_NAME}.sql"
    
    # Compress backup
    gzip -f $BACKUP_DIR/postgres_${BACKUP_NAME}.sql
    echo "✅ Backup compressed: $BACKUP_DIR/postgres_${BACKUP_NAME}.sql.gz"
else
    echo "❌ PostgreSQL backup failed"
    exit 1
fi

# Backup Redis (optional)
echo ""
echo "Backing up Redis data..."
docker-compose -f $COMPOSE_FILE exec -T redis redis-cli \
    --rdb $BACKUP_DIR/redis_${BACKUP_NAME}.rdb \
    SAVE

if [ $? -eq 0 ]; then
    echo "✅ Redis backup created"
else
    echo "⚠ Redis backup failed (non-critical)"
fi

# Calculate backup size
BACKUP_SIZE=$(du -sh $BACKUP_DIR/postgres_${BACKUP_NAME}.sql.gz | cut -f1)

echo ""
echo "=================================================="
echo "✅ Backup completed successfully!"
echo "=================================================="
echo ""
echo "Backup details:"
echo "  File: postgres_${BACKUP_NAME}.sql.gz"
echo "  Size: $BACKUP_SIZE"
echo "  Location: $BACKUP_DIR"
echo ""
echo "To restore this backup:"
echo "  ./scripts/restore.sh postgres_${BACKUP_NAME}.sql.gz"
echo ""

# Clean up old backups (keep last 30 days)
find $BACKUP_DIR -name "postgres_*.sql.gz" -mtime +30 -delete
echo "Old backups cleaned (retention: 30 days)"

