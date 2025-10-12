#!/bin/bash
# Restore PostgreSQL database from backup
# Usage: ./restore-postgres.sh <backup_file.sql.gz> [--yes]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
NAMESPACE="${NAMESPACE:-carpeta-ciudadana}"

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: Backup file required${NC}"
    echo "Usage: ./restore-postgres.sh <backup_file.sql.gz> [--yes]"
    exit 1
fi

BACKUP_FILE="$1"
SKIP_CONFIRM=false

# Parse remaining arguments
shift
while [[ $# -gt 0 ]]; do
  case $1 in
    --yes)
      SKIP_CONFIRM=true
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}=== PostgreSQL Restore ===${NC}"
echo "Backup file: $BACKUP_FILE"
echo "Namespace: $NAMESPACE"
echo ""

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
    exit 1
fi

# Verify checksum if available
CHECKSUM_FILE="$BACKUP_FILE.sha256"
if [ -f "$CHECKSUM_FILE" ]; then
    echo -e "${YELLOW}Verifying checksum...${NC}"
    if sha256sum -c "$CHECKSUM_FILE" &> /dev/null; then
        echo -e "${GREEN}✅ Checksum valid${NC}"
    else
        echo -e "${RED}Error: Checksum verification failed!${NC}"
        exit 1
    fi
    echo ""
fi

# Confirm before restoring
if [ "$SKIP_CONFIRM" = false ]; then
    echo -e "${RED}⚠️  WARNING: This will restore the database from backup${NC}"
    echo -e "${YELLOW}This will overwrite all current data!${NC}"
    read -p "Continue? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^yes$ ]]; then
        echo "Restore cancelled"
        exit 0
    fi
fi

# Get PostgreSQL credentials
echo -e "${YELLOW}Retrieving credentials...${NC}"
POSTGRES_HOST=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_HOST}' | base64 -d 2>/dev/null || echo "localhost")
POSTGRES_PASSWORD=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_PASSWORD}' | base64 -d)
POSTGRES_USER=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_USER}' | base64 -d 2>/dev/null || echo "postgres")
POSTGRES_DB=$(kubectl get secret postgresql-auth -n "$NAMESPACE" -o jsonpath='{.data.POSTGRESQL_DB}' | base64 -d 2>/dev/null || echo "carpeta_ciudadana")

# Restore database
echo -e "${YELLOW}Restoring database...${NC}"

gunzip -c "$BACKUP_FILE" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -U "$POSTGRES_USER" \
  -d "postgres" \
  --set ON_ERROR_STOP=on

echo -e "${GREEN}✅ Database restored${NC}"

# Verify restoration
echo -e "${YELLOW}Verifying restoration...${NC}"
TABLE_COUNT=$(PGPASSWORD="$POSTGRES_PASSWORD" psql \
  -h "$POSTGRES_HOST" \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

echo "Tables found: $TABLE_COUNT"

echo ""
echo -e "${GREEN}=== Restore completed successfully ===${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Verify application functionality"
echo "2. Check data integrity"
echo "3. Monitor logs for errors"

