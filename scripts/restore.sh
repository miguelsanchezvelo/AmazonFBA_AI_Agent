#!/bin/bash
# Database Restore Script
#
# Usage: ./scripts/restore.sh <backup_file>
# Example: ./scripts/restore.sh backups/postgres_20241105_120000.sql.gz

set -e

BACKUP_FILE=$1
COMPOSE_FILE="docker-compose.prod.yml"

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not specified"
    echo "Usage: ./scripts/restore.sh <backup_file>"
    echo ""
    echo "Available backups:"
    ls -lh backups/postgres_*.sql.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Load environment variables
if [ -f ".env.production" ]; then
    export $(cat .env.production | grep -v '^#' | xargs)
fi

echo "⚠️  WARNING: This will REPLACE the current database!"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
echo

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled"
    exit 0
fi

echo "🔄 Restoring database from backup..."
echo "=================================================="

# Decompress if needed
TEMP_FILE="/tmp/restore_temp.sql"
if [[ $BACKUP_FILE == *.gz ]]; then
    echo "Decompressing backup..."
    gunzip -c $BACKUP_FILE > $TEMP_FILE
else
    cp $BACKUP_FILE $TEMP_FILE
fi

# Restore database
echo "Restoring to database..."
docker-compose -f $COMPOSE_FILE exec -T postgres psql \
    -U ${POSTGRES_USER:-fba_user} \
    -d ${POSTGRES_DB:-fba_production} \
    < $TEMP_FILE

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully"
    rm -f $TEMP_FILE
else
    echo "❌ Database restore failed"
    rm -f $TEMP_FILE
    exit 1
fi

# Restart services
echo ""
echo "Restarting services..."
docker-compose -f $COMPOSE_FILE restart backend

echo ""
echo "=================================================="
echo "✅ Restore completed successfully!"
echo "=================================================="

