# Rollback Plan for CSV to PostgreSQL Migration

## Overview

This document describes the rollback procedure if the CSV to PostgreSQL migration needs to be reversed.

## Prerequisites

1. **Database Backup**: Ensure a backup exists before migration
   - Backup location: `backups/pre_migration_YYYYMMDD_HHMMSS.sql`
   - Created with: `pg_dump -U fba_user -d fba_db > backup_file.sql`

2. **CSV Files**: Original CSV files are preserved in `data/` directory

## Rollback Methods

### Method 1: Restore from Backup (Recommended)

If a database backup was created before migration:

```bash
# 1. Stop the application
# 2. Drop current database
dropdb -U fba_user fba_db

# 3. Recreate database
createdb -U fba_user fba_db

# 4. Restore from backup
psql -U fba_user -d fba_db < backups/pre_migration_YYYYMMDD_HHMMSS.sql

# 5. Verify data
psql -U fba_user -d fba_db -c "SELECT COUNT(*) FROM products;"
```

### Method 2: Revert Alembic Migrations

If you want to keep the database structure but remove migrated data:

```bash
# 1. Rollback to before migration
cd backend/database/migrations
alembic downgrade 001_initial_schema

# 2. Drop all tables
alembic downgrade base

# 3. Recreate schema (if needed)
alembic upgrade head
```

### Method 3: Manual Data Cleanup

If you need to remove only migrated data:

```sql
-- Connect to database
psql -U fba_user -d fba_db

-- Delete all migrated data
DELETE FROM inventory;
DELETE FROM analyses;
DELETE FROM supplier_products;
DELETE FROM suppliers;
DELETE FROM products;
DELETE FROM events;
DELETE FROM api_cache;

-- Reset sequences (if using auto-increment)
-- Not applicable for UUID primary keys
```

## Verification After Rollback

After rollback, verify:

1. **Database State**:
   ```sql
   SELECT COUNT(*) FROM products;
   SELECT COUNT(*) FROM analyses;
   SELECT COUNT(*) FROM suppliers;
   SELECT COUNT(*) FROM inventory;
   ```

2. **CSV Files**: Verify original CSV files still exist in `data/` directory

3. **Application**: Restart application and verify it works with CSV data again

## Rollback Script

A rollback script can be created:

```bash
#!/bin/bash
# rollback_migration.sh

BACKUP_FILE="backups/pre_migration_$(date +%Y%m%d_%H%M%S).sql"

if [ -f "$BACKUP_FILE" ]; then
    echo "Restoring from backup: $BACKUP_FILE"
    dropdb -U fba_user fba_db
    createdb -U fba_user fba_db
    psql -U fba_user -d fba_db < "$BACKUP_FILE"
    echo "Rollback completed successfully"
else
    echo "Backup file not found: $BACKUP_FILE"
    echo "Please restore manually or use Alembic downgrade"
fi
```

## Prevention

To prevent the need for rollback:

1. **Always create backup before migration**
2. **Test migration on staging/dev environment first**
3. **Validate data integrity after migration**
4. **Keep CSV files as backup until migration is verified**

## Notes

- UUID primary keys means no sequence reset needed
- Foreign key constraints will cascade delete related records
- Consider transaction rollback if migration is done in single transaction

