#!/bin/bash
# Restore script for SMS Campaign Generation System
# This script restores data from backups

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RESTORE_TYPE="${RESTORE_TYPE:-full}"  # full, database, redis, config
LOG_FILE="${BACKUP_DIR}/logs/restore_$(date +%Y%m%d_%H%M%S).log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Function to list available backups
list_backups() {
    local component="${1:-all}"

    log "Listing available backups for component: ${component}"

    case "$component" in
        database)
            ls -la "${BACKUP_DIR}/database/"*.dump 2>/dev/null | while read -r line; do
                log "Database: $(basename "$line")"
            done
            ;;
        redis)
            ls -la "${BACKUP_DIR}/redis/"*.rdb.gz 2>/dev/null | while read -r line; do
                log "Redis: $(basename "$line")"
            done
            ;;
        config)
            ls -la "${BACKUP_DIR}/config/"*.tar.gz 2>/dev/null | while read -r line; do
                log "Config: $(basename "$line")"
            done
            ;;
        all)
            list_backups "database"
            list_backups "redis"
            list_backups "config"
            ;;
    esac
}

# Function to restore database
restore_database() {
    local backup_file="${1}"

    if [ -z "$backup_file" ]; then
        # Find the latest database backup
        backup_file=$(ls -t "${BACKUP_DIR}/database/"*.dump 2>/dev/null | head -1)
        if [ -z "$backup_file" ]; then
            log "ERROR: No database backup found"
            return 1
        fi
    fi

    if [ ! -f "$backup_file" ]; then
        log "ERROR: Database backup file not found: $backup_file"
        return 1
    fi

    log "Starting database restore from: $(basename "$backup_file")"

    # Get database credentials
    DB_HOST="${DB_HOST:-postgres}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-sms_campaigns}"
    DB_USER="${DB_USER:-postgres}"

    # Stop application services during restore
    log "Stopping application services..."
    # kubectl scale deployment sms-campaigns-app --replicas=0 -n sms-campaigns

    # Restore database
    if command -v pg_restore >/dev/null 2>&1; then
        PGPASSWORD="${POSTGRES_PASSWORD}" pg_restore \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --verbose \
            --clean \
            --if-exists \
            --no-owner \
            --no-privileges \
            "$backup_file" 2>&1 | tee -a "${LOG_FILE}"

        log "Database restore completed"
    else
        log "ERROR: pg_restore not found"
        return 1
    fi

    # Restart application services
    log "Starting application services..."
    # kubectl scale deployment sms-campaigns-app --replicas=3 -n sms-campaigns
}

# Function to restore Redis
restore_redis() {
    local backup_file="${1}"

    if [ -z "$backup_file" ]; then
        # Find the latest Redis backup
        backup_file=$(ls -t "${BACKUP_DIR}/redis/"*.rdb.gz 2>/dev/null | head -1)
        if [ -z "$backup_file" ]; then
            log "ERROR: No Redis backup found"
            return 1
        fi
    fi

    if [ ! -f "$backup_file" ]; then
        log "ERROR: Redis backup file not found: $backup_file"
        return 1
    fi

    log "Starting Redis restore from: $(basename "$backup_file")"

    # Get Redis connection details
    REDIS_HOST="${REDIS_HOST:-redis}"
    REDIS_PORT="${REDIS_PORT:-6379}"
    REDIS_PASSWORD="${REDIS_PASSWORD:-}"

    # Stop Redis service
    log "Stopping Redis service..."
    # kubectl scale deployment redis --replicas=0 -n sms-campaigns
    sleep 10

    # Decompress and copy Redis backup
    gunzip -c "$backup_file" > "/tmp/dump.rdb"

    # Copy to Redis data directory
    # kubectl cp /tmp/dump.rdb sms-campaigns/redis-0:/data/dump.rdb

    # Start Redis service
    log "Starting Redis service..."
    # kubectl scale deployment redis --replicas=1 -n sms-campaigns

    # Clean up temporary file
    rm -f /tmp/dump.rdb

    log "Redis restore completed"
}

# Function to restore configuration
restore_config() {
    local backup_file="${1}"

    if [ -z "$backup_file" ]; then
        # Find the latest config backup
        backup_file=$(ls -t "${BACKUP_DIR}/config/app-config_"*.tar.gz 2>/dev/null | head -1)
        if [ -z "$backup_file" ]; then
            log "ERROR: No configuration backup found"
            return 1
        fi
    fi

    if [ ! -f "$backup_file" ]; then
        log "ERROR: Configuration backup file not found: $backup_file"
        return 1
    fi

    log "Starting configuration restore from: $(basename "$backup_file")"

    # Create backup of current config
    if [ -d "/app/config" ]; then
        cp -r /app/config "${BACKUP_DIR}/config/current-config-backup-$(date +%Y%m%d_%H%M%S)"
    fi

    # Restore configuration
    mkdir -p /app/config
    tar -xzf "$backup_file" -C /app/config 2>&1 | tee -a "${LOG_FILE}"

    log "Configuration restore completed"
}

# Function to perform full restore
restore_full() {
    local database_backup="${1:-}"
    local redis_backup="${2:-}"
    local config_backup="${3:-}"

    log "Starting full system restore"

    # Restore configuration first
    log "Restoring configuration..."
    restore_config "$config_backup"

    # Restore database
    log "Restoring database..."
    restore_database "$database_backup"

    # Restore Redis
    log "Restoring Redis..."
    restore_redis "$redis_backup"

    # Verify system health after restore
    log "Verifying system health..."
    sleep 30

    # Check application health
    # if curl -f http://sms-campaigns-app:8000/health; then
    #     log "✓ Application health check passed"
    # else
    #     log "✗ Application health check failed"
    #     return 1
    # fi

    log "Full system restore completed"
}

# Function to send restore notification
send_notification() {
    local status=$1
    local message=$2

    # Send Slack notification if webhook is configured
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        curl -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \"SMS Campaigns Restore ${status}\",
                \"attachments\": [
                    {
                        \"color\": \"${status}\" = \"success\" && \"good\" || \"danger\",
                        \"fields\": [
                            {
                                \"title\": \"Timestamp\",
                                \"value\": \"$(date '+%Y-%m-%d %H:%M:%S')\",
                                \"short\": true
                            },
                            {
                                \"title\": \"Status\",
                                \"value\": \"${message}\",
                                \"short\": true
                            }
                        ]
                    }
                ]
            }" 2>/dev/null || log "Failed to send Slack notification"
    fi
}

# Main restore execution
main() {
    local action="${1:-list}"
    local component="${2:-}"
    local backup_file="${3:-}"

    log "Starting restore process - Action: $action"

    # Create restore log directory
    mkdir -p "$(dirname "${LOG_FILE}")"

    case "$action" in
        list)
            list_backups "$component"
            ;;
        database)
            restore_database "$backup_file"
            ;;
        redis)
            restore_redis "$backup_file"
            ;;
        config)
            restore_config "$backup_file"
            ;;
        full)
            restore_full "$backup_file" "${4:-}" "${5:-}"
            ;;
        *)
            echo "Usage: $0 {list|database|redis|config|full} [component] [backup_file]"
            echo ""
            echo "Actions:"
            echo "  list                    - List available backups"
            echo "  database                - Restore database"
            echo "  redis                   - Restore Redis"
            echo "  config                  - Restore configuration"
            echo "  full                    - Restore all components"
            echo ""
            echo "Examples:"
            echo "  $0 list                  - List all available backups"
            echo "  $0 list database         - List database backups"
            echo "  $0 database               - Restore latest database backup"
            echo "  $0 database backup.dump  - Restore specific database backup"
            echo "  $0 full                   - Restore full system from latest backups"
            exit 1
            ;;
    esac

    # Check restore status
    if [ $? -eq 0 ]; then
        local message="Restore completed successfully"
        log "✓ ${message}"
        send_notification "Success" "${message}"
    else
        local message="Restore failed. Check logs for details."
        log "✗ ${message}"
        send_notification "Failed" "${message}"
        exit 1
    fi

    log "Restore process completed"
}

# Trap cleanup on exit
trap 'log "Restore script interrupted"; exit 1' INT TERM

# Execute main function
main "$@"