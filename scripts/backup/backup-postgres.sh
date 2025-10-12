#!/bin/bash
# Backup PostgreSQL database
# Usage: ./backup-postgres.sh [--retention-days 7]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
NAMESPACE="${NAMESPACE:-carpeta-ciudadana}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/postgres_backup_$TIMESTAMP.sql.gz"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}=== PostgreSQL Backup ===${NC}"
echo "Namespace: $NAMESPACE"
echo "Retention: $RETENTION_DAYS days"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Get PostgreSQL credentials from secret
echo -e "${YELLOW}Retrieving credentials...${NC}"
POSTGRES_HOST=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_HOST}' | base64 -d 2>/dev/null || echo "localhost")
POSTGRES_PASSWORD=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_PASSWORD}' | base64 -d)
POSTGRES_USER=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_USER}' | base64 -d 2>/dev/null || echo "postgres")
POSTGRES_DB=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_DB}' | base64 -d 2>/dev/null || echo "carpeta_ciudadana")

# Perform backup using pg_dump
echo -e "${YELLOW}Creating backup...${NC}"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  -h "$POSTGRES_HOST" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --verbose \
  --clean \
  --if-exists \
  --create \
  | gzip > "$BACKUP_FILE"

echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"

# Calculate size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Size: $BACKUP_SIZE"

# Calculate checksum
CHECKSUM=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')
echo "$CHECKSUM  $BACKUP_FILE" > "$BACKUP_FILE.sha256"
echo "Checksum: $CHECKSUM"

# Log backup
BACKUP_LOG="$BACKUP_DIR/backup.log"
echo "$(date +%Y-%m-%d_%H:%M:%S) - Backup created: $BACKUP_FILE (size: $BACKUP_SIZE, checksum: $CHECKSUM)" >> "$BACKUP_LOG"

# Clean old backups (retention)
echo -e "${YELLOW}Cleaning old backups (retention: $RETENTION_DAYS days)...${NC}"
find "$BACKUP_DIR" -name "postgres_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find "$BACKUP_DIR" -name "postgres_backup_*.sql.gz.sha256" -mtime +$RETENTION_DAYS -delete

REMAINING=$(ls -1 "$BACKUP_DIR"/postgres_backup_*.sql.gz 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Backups remaining: $REMAINING${NC}"

echo ""
echo -e "${GREEN}=== Backup completed successfully ===${NC}"

