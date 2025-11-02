#!/bin/bash
# Backup script for SMS Campaign Generation System
# This script performs automated backups of database, configuration, and logs

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${BACKUP_DIR}/logs/backup_${TIMESTAMP}.log"

# Ensure backup directories exist
mkdir -p "${BACKUP_DIR}/database"
mkdir -p "${BACKUP_DIR}/config"
mkdir -p "${BACKUP_DIR}/logs"
mkdir -p "${BACKUP_DIR}/redis"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days"

    # Clean up database backups
    find "${BACKUP_DIR}/database" -name "*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete -print

    # Clean up config backups
    find "${BACKUP_DIR}/config" -name "*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete -print

    # Clean up log backups
    find "${BACKUP_DIR}/logs" -name "backup_*.log" -type f -mtime +${RETENTION_DAYS} -delete -print

    # Clean up redis backups
    find "${BACKUP_DIR}/redis" -name "*.rdb.gz" -type f -mtime +${RETENTION_DAYS} -delete -print

    log "Cleanup completed"
}

# Function to backup PostgreSQL database
backup_database() {
    log "Starting database backup"

    # Get database credentials from environment or secrets
    DB_HOST="${DB_HOST:-postgres}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-sms_campaigns}"
    DB_USER="${DB_USER:-postgres}"

    # Create database backup
    if command -v pg_dump >/dev/null 2>&1; then
        PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --no-password \
            --verbose \
            --clean \
            --if-exists \
            --create \
            --format=custom \
            --compress=9 \
            --file="${BACKUP_DIR}/database/database_${TIMESTAMP}.dump" 2>&1 | tee -a "${LOG_FILE}"

        # Also create SQL dump for portability
        PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --no-password \
            --verbose \
            --clean \
            --if-exists \
            --create \
            --schema-only \
            | gzip > "${BACKUP_DIR}/database/schema_${TIMESTAMP}.sql.gz" 2>&1 | tee -a "${LOG_FILE}"

        PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --no-password \
            --verbose \
            --data-only \
            --exclude-table-data='*._*' \
            | gzip > "${BACKUP_DIR}/database/data_${TIMESTAMP}.sql.gz" 2>&1 | tee -a "${LOG_FILE}"

        log "Database backup completed"
    else
        log "ERROR: pg_dump not found. Skipping database backup."
        return 1
    fi
}

# Function to backup Redis
backup_redis() {
    log "Starting Redis backup"

    REDIS_HOST="${REDIS_HOST:-redis}"
    REDIS_PORT="${REDIS_PORT:-6379}"
    REDIS_PASSWORD="${REDIS_PASSWORD:-}"

    # Trigger Redis BGSAVE if running as standalone
    if command -v redis-cli >/dev/null 2>&1; then
        if [ -n "${REDIS_PASSWORD}" ]; then
            redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" -a "${REDIS_PASSWORD}" BGSAVE
        else
            redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" BGSAVE
        fi

        # Wait for BGSAVE to complete
        sleep 5

        # Copy Redis RDB file and compress
        if [ -f "/var/lib/redis/dump.rdb" ]; then
            gzip -c "/var/lib/redis/dump.rdb" > "${BACKUP_DIR}/redis/redis_${TIMESTAMP}.rdb.gz"
            log "Redis backup completed"
        else
            log "WARNING: Redis RDB file not found at /var/lib/redis/dump.rdb"
        fi
    else
        log "ERROR: redis-cli not found. Skipping Redis backup."
        return 1
    fi
}

# Function to backup application configuration
backup_config() {
    log "Starting configuration backup"

    # Backup Kubernetes configurations
    if [ -d "/opt/k8s-configs" ]; then
        tar -czf "${BACKUP_DIR}/config/k8s-configs_${TIMESTAMP}.tar.gz" \
            -C "/opt/k8s-configs" . 2>&1 | tee -a "${LOG_FILE}"
    fi

    # Backup application configurations
    if [ -d "/app/config" ]; then
        tar -czf "${BACKUP_DIR}/config/app-config_${TIMESTAMP}.tar.gz" \
            -C "/app/config" . 2>&1 | tee -a "${LOG_FILE}"
    fi

    # Backup monitoring configurations
    if [ -d "/opt/monitoring" ]; then
        tar -czf "${BACKUP_DIR}/config/monitoring_${TIMESTAMP}.tar.gz" \
            -C "/opt/monitoring" . 2>&1 | tee -a "${LOG_FILE}"
    fi

    log "Configuration backup completed"
}

# Function to backup application logs
backup_logs() {
    log "Starting log backup"

    # Backup recent application logs
    if [ -d "/app/logs" ]; then
        find "/app/logs" -name "*.log" -mtime -7 -print0 | \
            tar -czf "${BACKUP_DIR}/logs/app-logs_${TIMESTAMP}.tar.gz" \
            --null -T - 2>&1 | tee -a "${LOG_FILE}"
    fi

    # Backup system logs
    if [ -d "/var/log" ]; then
        find "/var/log" -name "*.log" -mtime -1 -print0 | \
            tar -czf "${BACKUP_DIR}/logs/system-logs_${TIMESTAMP}.tar.gz" \
            --null -T - 2>&1 | tee -a "${LOG_FILE}"
    fi

    log "Log backup completed"
}

# Function to backup environment variables and secrets
backup_environment() {
    log "Starting environment backup"

    # Backup environment variables (excluding secrets)
    env | grep -v -E "(PASSWORD|SECRET|KEY|TOKEN)" > "${BACKUP_DIR}/config/environment_${TIMESTAMP}.txt"

    # Create backup metadata
    cat > "${BACKUP_DIR}/metadata_${TIMESTAMP}.json" << EOF
{
    "timestamp": "${TIMESTAMP}",
    "hostname": "$(hostname)",
    "backup_type": "automated",
    "components": {
        "database": $(test -f "${BACKUP_DIR}/database/database_${TIMESTAMP}.dump" && echo "true" || echo "false"),
        "redis": $(test -f "${BACKUP_DIR}/redis/redis_${TIMESTAMP}.rdb.gz" && echo "true" || echo "false"),
        "config": $(test -f "${BACKUP_DIR}/config/app-config_${TIMESTAMP}.tar.gz" && echo "true" || echo "false"),
        "logs": $(test -f "${BACKUP_DIR}/logs/app-logs_${TIMESTAMP}.tar.gz" && echo "true" || echo "false")
    },
    "version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "docker_images": "$(docker images --format 'table {{.Repository}}:{{.Tag}}' | grep sms-campaigns || echo 'none')"
}
EOF

    log "Environment backup completed"
}

# Function to verify backup integrity
verify_backup() {
    log "Starting backup verification"

    local verification_failed=false

    # Verify database backup
    if [ -f "${BACKUP_DIR}/database/database_${TIMESTAMP}.dump" ]; then
        if [ -s "${BACKUP_DIR}/database/database_${TIMESTAMP}.dump" ]; then
            log "✓ Database backup verified"
        else
            log "✗ Database backup is empty"
            verification_failed=true
        fi
    else
        log "✗ Database backup not found"
        verification_failed=true
    fi

    # Verify Redis backup
    if [ -f "${BACKUP_DIR}/redis/redis_${TIMESTAMP}.rdb.gz" ]; then
        if gzip -t "${BACKUP_DIR}/redis/redis_${TIMESTAMP}.rdb.gz" 2>/dev/null; then
            log "✓ Redis backup verified"
        else
            log "✗ Redis backup is corrupted"
            verification_failed=true
        fi
    else
        log "✗ Redis backup not found"
        verification_failed=true
    fi

    # Verify config backup
    if [ -f "${BACKUP_DIR}/config/app-config_${TIMESTAMP}.tar.gz" ]; then
        if tar -tzf "${BACKUP_DIR}/config/app-config_${TIMESTAMP}.tar.gz" >/dev/null 2>&1; then
            log "✓ Configuration backup verified"
        else
            log "✗ Configuration backup is corrupted"
            verification_failed=true
        fi
    else
        log "✗ Configuration backup not found"
        verification_failed=true
    fi

    if [ "$verification_failed" = true ]; then
        log "✗ Backup verification failed"
        return 1
    else
        log "✓ All backups verified successfully"
        return 0
    fi
}

# Function to send backup notification
send_notification() {
    local status=$1
    local message=$2

    # Send Slack notification if webhook is configured
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        curl -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-type: application/json' \
            --data "{
                \"text\": \"SMS Campaigns Backup ${status}\",
                \"attachments\": [
                    {
                        \"color\": \"${status}\" = \"success\" && \"good\" || \"danger\",
                        \"fields\": [
                            {
                                \"title\": \"Timestamp\",
                                \"value\": \"${TIMESTAMP}\",
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

    # Send email notification if configured
    if [ -n "${BACKUP_EMAIL}" ] && command -v mail >/dev/null 2>&1; then
        echo "${message}" | mail -s "SMS Campaigns Backup ${status}" "${BACKUP_EMAIL}" 2>/dev/null || \
            log "Failed to send email notification"
    fi
}

# Main backup execution
main() {
    log "Starting backup process"

    # Create backup log
    mkdir -p "$(dirname "${LOG_FILE}")"

    # Track backup start time
    local start_time=$(date +%s)

    # Execute backup functions
    local backup_status=0

    backup_database || backup_status=1
    backup_redis || backup_status=1
    backup_config || backup_status=1
    backup_logs || backup_status=1
    backup_environment || backup_status=1

    # Verify backups
    if ! verify_backup; then
        backup_status=1
    fi

    # Calculate backup duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Cleanup old backups
    cleanup_old_backups

    # Generate backup summary
    local backup_size=$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1 || echo "unknown")

    if [ $backup_status -eq 0 ]; then
        local message="Backup completed successfully in ${duration}s. Size: ${backup_size}"
        log "✓ ${message}"
        send_notification "Success" "${message}"
    else
        local message="Backup failed after ${duration}s. Check logs for details."
        log "✗ ${message}"
        send_notification "Failed" "${message}"
        exit 1
    fi

    log "Backup process completed"
}

# Trap cleanup on exit
trap 'log "Backup script interrupted"; exit 1' INT TERM

# Execute main function
main "$@"