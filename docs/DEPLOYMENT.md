# SMS Campaign Generation System - Deployment Guide

## Overview

This comprehensive guide covers deploying the SMS Campaign Generation System in production environments using Docker Compose and Kubernetes. The system is designed for high availability, scalability, and maintainability.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Docker Compose Deployment](#docker-compose-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Database Setup](#database-setup)
6. [Monitoring and Observability](#monitoring-and-observability)
7. [Backup and Recovery](#backup-and-recovery)
8. [Security Configuration](#security-configuration)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

#### Minimum Requirements
- **CPU**: 4 cores
- **Memory**: 8GB RAM
- **Storage**: 100GB SSD
- **Network**: 1Gbps

#### Recommended Requirements
- **CPU**: 8 cores
- **Memory**: 16GB RAM
- **Storage**: 500GB SSD
- **Network**: 10Gbps

### Software Dependencies

- Docker Engine 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+ (for K8s deployment)
- kubectl 1.24+
- Helm 3.0+ (optional)

### External Services

- **PostgreSQL**: 15+ (or use managed service)
- **Redis**: 7+ (or use managed service)
- **OpenAI API**: Valid API key with sufficient quota
- **Domain Name**: For SSL certificates
- **Load Balancer**: For production traffic

## Environment Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```bash
# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json

# Database Configuration
DATABASE_URL=postgresql://user:password@postgres:5432/sms_campaigns
POSTGRES_DB=sms_campaigns
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your_redis_password

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7

# Security Configuration
SECRET_KEY=your_very_secure_secret_key_here
ALLOWED_HOSTS=api.yourdomain.com
CORS_ORIGINS=https://app.yourdomain.com

# Performance Configuration
MAX_WORKERS=4
ENABLE_RATE_LIMITING=true
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_TIME_WINDOW=60

# Monitoring Configuration
ENABLE_METRICS=true
METRICS_PORT=9090

# Domain Configuration
DOMAIN=api.yourdomain.com
LETSENCRYPT_EMAIL=admin@yourdomain.com

# Notification Configuration
SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
BACKUP_EMAIL=alerts@yourdomain.com

# Docker Configuration
REGISTRY=ghcr.io
IMAGE_NAME=your-org/sms-campaigns
VERSION=latest

# Scale Configuration
APP_REPLICAS=3
```

### Configuration Files

#### Production Configuration (`config/production.json`)

```json
{
  "environment": "production",
  "debug": false,
  "log_level": "INFO",
  "log_format": "json",
  "max_workers": 4,
  "enable_metrics": true,
  "enable_rate_limiting": true,
  "rate_limit_max_requests": 100,
  "rate_limit_time_window": 60,
  "cors_origins": ["https://app.yourdomain.com"],
  "allowed_hosts": ["api.yourdomain.com"],
  "database_pool_size": 20,
  "database_max_overflow": 30,
  "redis_max_connections": 20,
  "openai_model": "gpt-4-turbo-preview",
  "openai_max_tokens": 4000,
  "openai_temperature": 0.7,
  "enable_auto_correction": true,
  "enable_flow_validation": true,
  "validation_timeout_ms": 30000,
  "llm_timeout_ms": 60000
}
```

## Docker Compose Deployment

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/sms-campaigns.git
   cd sms-campaigns
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

3. **Start services**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Initialize database**
   ```bash
   docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head
   ```

5. **Verify deployment**
   ```bash
   curl -f https://api.yourdomain.com/health
   ```

### Service Management

#### Scale Application
```bash
# Scale to 5 replicas
docker-compose -f docker-compose.prod.yml up -d --scale app=5
```

#### Update Application
```bash
# Pull new image
docker-compose -f docker-compose.prod.yml pull app

# Restart with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps app
```

#### View Logs
```bash
# Application logs
docker-compose -f docker-compose.prod.yml logs -f app

# All services logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Backup Data
```bash
# Run backup script
./scripts/backup.sh
```

### Production Considerations

#### Resource Limits
- **Application**: 1-2 CPU cores, 512MB-1GB RAM per container
- **PostgreSQL**: 2-4 CPU cores, 4-8GB RAM
- **Redis**: 0.5-1 CPU cores, 512MB-1GB RAM
- **Monitoring**: 0.5-1 CPU core, 512MB RAM per service

#### Health Checks
All services include comprehensive health checks:
- **Liveness**: Detects container failures
- **Readiness**: Detects service readiness
- **Startup**: Handles initialization delays

#### Security Hardening
- **Non-root users** in all containers
- **Read-only filesystems** where possible
- **Resource limits** to prevent DoS
- **Network isolation** using Docker networks
- **Secrets management** for sensitive data

## Kubernetes Deployment

### Prerequisites

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (replace base64 values)
kubectl apply -f k8s/secrets.yaml

# Create configmaps
kubectl apply -f k8s/configmaps.yaml
```

### Deploy Services

```bash
# Deploy core services
kubectl apply -f k8s/deployments.yaml

# Deploy services and ingress
kubectl apply -f k8s/services.yaml
kubectl apply -f k8s/ingress.yaml

# Deploy monitoring
kubectl apply -f k8s/monitoring.yaml
```

### Using Helm

```bash
# Install dependencies
helm dependency update helm/sms-campaigns

# Deploy application
helm install sms-campaigns helm/sms-campaigns \
  --namespace sms-campaigns \
  --create-namespace \
  --values helm/values-prod.yaml

# Upgrade deployment
helm upgrade sms-campaigns helm/sms-campaigns \
  --namespace sms-campaigns \
  --values helm/values-prod.yaml
```

### Kubernetes Operations

#### Scale Deployment
```bash
# Scale application
kubectl scale deployment sms-campaigns-app --replicas=5 -n sms-campaigns

# Scale with autoscaler
kubectl apply -f k8s/autoscaler.yaml
```

#### Rolling Updates
```bash
# Update image
kubectl set image deployment/sms-campaigns-app \
  app=ghcr.io/your-org/sms-campaigns:v1.2.0 \
  -n sms-campaigns

# Monitor rollout
kubectl rollout status deployment/sms-campaigns-app -n sms-campaigns
```

#### Debug Issues
```bash
# Check pod status
kubectl get pods -n sms-campaigns

# View pod logs
kubectl logs -f deployment/sms-campaigns-app -n sms-campaigns

# Execute in pod
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- /bin/bash

# Port forward for debugging
kubectl port-forward svc/sms-campaigns-app 8000:8000 -n sms-campaigns
```

## Database Setup

### PostgreSQL Configuration

#### Optimized Settings
```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = '0.9';
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = '100';
ALTER SYSTEM SET random_page_cost = '1.1';
ALTER SYSTEM SET effective_io_concurrency = '200';

-- Reload configuration
SELECT pg_reload_conf();
```

#### Monitoring Setup
```sql
-- Create monitoring user
CREATE USER monitoring WITH PASSWORD 'monitoring_password';
GRANT SELECT ON pg_stat_database TO monitoring;
GRANT SELECT ON pg_stat_activity TO monitoring;
GRANT SELECT ON pg_stat_statements TO monitoring;
```

#### Backup Configuration
```bash
# Set up WAL archiving
archive_mode = on
archive_command = 'cp %p /backups/postgres/archive/%f'
wal_level = replica
max_wal_senders = 3
```

### Redis Configuration

#### Redis Settings
```conf
# Memory optimization
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
rename-command CONFIG "CONFIG_b840c2e8e9b9c1b8a8a8a8a8a8a8a8a"
```

#### Monitoring Setup
```bash
# Enable monitoring
INFO memory
INFO clients
INFO stats
INFO replication
INFO cpu
```

## Monitoring and Observability

### Prometheus Configuration

#### Key Metrics
- **Application Metrics**: Request rate, response time, error rate
- **Business Metrics**: Campaign generation rate, validation success rate
- **Infrastructure Metrics**: CPU, memory, disk, network
- **Database Metrics**: Connection count, query performance
- **Redis Metrics**: Memory usage, hit rate, connection count

#### Alert Rules
Critical alerts:
- Application down (>1 minute)
- Error rate > 10%
- Response time > 5 seconds (95th percentile)
- Database connections > 150
- Memory usage > 95%
- Disk space < 10%

### Grafana Dashboards

#### Key Dashboards
1. **Application Overview**: Request metrics, error rates, response times
2. **Infrastructure**: Server resources, container metrics
3. **Database**: PostgreSQL performance, connection metrics
4. **Redis**: Cache performance, memory usage
5. **Business Metrics**: Campaign generation statistics

#### Custom Dashboards
```json
{
  "dashboard": {
    "title": "SMS Campaigns Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{job=\"sms-campaigns-app\"}[5m])"
          }
        ]
      }
    ]
  }
}
```

### Log Management

#### Log Levels
- **ERROR**: Application errors, failed requests
- **WARN**: Performance issues, security events
- **INFO**: General application events
- **DEBUG**: Detailed debugging information

#### Log Aggregation
```yaml
# Vector configuration
sources:
  app_logs:
    type: file
    include: ["/app/logs/*.log"]

transforms:
  parse_json:
    type: remap
    inputs: ["app_logs"]
    source: ". = parse_json!(.message)"

sinks:
  loki:
    type: loki
    inputs: ["parse_json"]
    endpoint: "http://loki:3100/loki/api/v1/push"
```

## Backup and Recovery

### Backup Strategy

#### Automated Backups
```bash
# Daily full backups
0 2 * * * /path/to/backup.sh

# Weekly full backup with monthly retention
0 3 * * 0 /path/to/backup.sh --monthly

# Hourly transaction log backups
0 * * * * /path/to/backup-wal.sh
```

#### Backup Components
1. **Database**: Full dump + transaction logs
2. **Redis**: RDB files + AOF files
3. **Configuration**: All config files and secrets
4. **Logs**: Application and system logs
5. **Metadata**: Backup information and timestamps

### Recovery Procedures

#### Database Recovery
```bash
# Stop application
kubectl scale deployment sms-campaigns-app --replicas=0

# Restore from backup
./scripts/restore.sh database backup_file.dump

# Verify restore
psql -h localhost -U postgres -d sms_campaigns -c "SELECT COUNT(*) FROM campaigns;"

# Restart application
kubectl scale deployment sms-campaigns-app --replicas=3
```

#### Disaster Recovery
1. **Assess Impact**: Determine scope and timeline
2. **Communicate**: Notify stakeholders
3. **Isolate**: Prevent further damage
4. **Restore**: Recover from latest backups
5. **Verify**: Test system functionality
6. **Review**: Analyze and improve procedures

## Security Configuration

### Network Security

#### Firewall Rules
```bash
# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow SSH (restrict to management IPs)
ufw allow from 192.168.1.0/24 to any port 22

# Database access (internal only)
ufw allow from 10.0.0.0/8 to any port 5432
ufw allow from 10.0.0.0/8 to any port 6379
```

#### TLS Configuration
```yaml
# Traefik TLS configuration
tls:
  options:
    modern:
      minVersion: "VersionTLS12"
      cipherSuites:
        - "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
        - "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
        - "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305"
```

### Application Security

#### Security Headers
```python
# Security middleware configuration
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'"
}
```

#### Rate Limiting
```yaml
# Rate limiting configuration
rate_limiting:
  requests_per_minute: 100
  burst_size: 150
  whitelist:
    - "192.168.1.0/24"
    - "10.0.0.0/8"
```

### Secrets Management

#### Kubernetes Secrets
```yaml
# Encrypted secrets
apiVersion: bitnami.com/v1alpha1
kind: SealedSecret
metadata:
  name: app-secrets
  namespace: sms-campaigns
spec:
  encryptedData:
    SECRET_KEY: AgBy3i4OJSWK+PiTySYZZA9rO43cGDEQAx...
```

#### Environment Variables
```bash
# Use external secret management
export DATABASE_URL=$(aws secretsmanager get-secret-value --secret-id prod/db-url --query SecretString --output text)
export OPENAI_API_KEY=$(vault kv get -field=api_key secret/llm/openai)
```

## Performance Tuning

### Application Optimization

#### Gunicorn Configuration
```python
# Gunicorn settings
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 120
keepalive = 2
```

#### Database Optimization
```sql
-- Create indexes
CREATE INDEX idx_campaigns_created_at ON campaigns(created_at);
CREATE INDEX idx_users_segment_id ON users(segment_id);
CREATE INDEX idx_messages_status ON messages(status);

-- Analyze tables
ANALYZE campaigns;
ANALYZE users;
ANALYZE messages;
```

#### Redis Optimization
```conf
# Redis optimization
tcp-keepalive 300
timeout 0
tcp-backlog 511
databases 1
maxmemory-policy allkeys-lru
```

### Infrastructure Optimization

#### Container Resource Limits
```yaml
# Optimal resource allocation
resources:
  requests:
    cpu: 250m
    memory: 256Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

#### Autoscaling Configuration
```yaml
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: sms-campaigns-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: sms-campaigns-app
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Troubleshooting

### Common Issues

#### Application Won't Start
```bash
# Check pod status
kubectl get pods -n sms-campaigns

# Check pod logs
kubectl logs deployment/sms-campaigns-app -n sms-campaigns

# Check events
kubectl get events -n sms-campaigns --sort-by='.lastTimestamp'

# Check configuration
kubectl describe deployment sms-campaigns-app -n sms-campaigns
```

#### Database Connection Issues
```bash
# Test database connectivity
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- python -c "
import psycopg2
conn = psycopg2.connect('$DATABASE_URL')
print('Database connection successful')
"

# Check database logs
kubectl logs deployment/postgres -n sms-campaigns

# Check database status
kubectl exec -it deployment/postgres -n sms-campaigns -- pg_isready
```

#### High Memory Usage
```bash
# Check memory usage
kubectl top pods -n sms-campaigns

# Check container metrics
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- ps aux

# Check for memory leaks
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- python -c "
import psutil
process = psutil.Process()
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

#### Performance Issues
```bash
# Check response times
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- \
  curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Check database query performance
kubectl exec -it deployment/postgres -n sms-campaigns -- \
  psql -U postgres -d sms_campaigns -c "
  SELECT query, mean_time, calls
  FROM pg_stat_statements
  ORDER BY mean_time DESC
  LIMIT 10;
"

# Check application logs for errors
kubectl logs deployment/sms-campaigns-app -n sms-campaigns | grep ERROR
```

### Debug Commands

#### Application Debugging
```bash
# Enable debug mode
kubectl set env deployment/sms-campaigns-app DEBUG=true -n sms-campaigns

# Port forward for local debugging
kubectl port-forward deployment/sms-campaigns-app 8000:8000 -n sms-campaigns

# Execute in container for debugging
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- /bin/bash
```

#### Network Debugging
```bash
# Test service connectivity
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- \
  wget -qO- http://postgres:5432

# Check DNS resolution
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- \
  nslookup postgres

# Test load balancer connectivity
kubectl exec -it deployment/sms-campaigns-app -n sms-campaigns -- \
  curl -v https://api.yourdomain.com/health
```

### Monitoring Debugging

#### Prometheus Debugging
```bash
# Check Prometheus targets
kubectl exec -it deployment/prometheus -n monitoring -- \
  curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, lastError: .lastError}'

# Check alerting rules
kubectl exec -it deployment/prometheus -n monitoring -- \
  curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name: .name, state: .state}'
```

#### Grafana Debugging
```bash
# Check data source connectivity
kubectl exec -it deployment/grafana -n monitoring -- \
  curl -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:3000/api/datasources/proxy/1/api/v1/query \
  -d 'query=up'

# Check dashboard health
kubectl logs deployment/grafana -n monitoring | grep -E "(error|warn)"
```

This deployment guide provides comprehensive instructions for deploying the SMS Campaign Generation System in production environments. Follow the sections sequentially for a successful deployment.