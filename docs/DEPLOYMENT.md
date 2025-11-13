# 🚀 Amazon FBA AI Agent V2 - Deployment Guide

**Version:** 2.0.0  
**Last Updated:** 2025-10-29

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Compose Setup](#docker-compose-setup)
4. [Staging Deployment](#staging-deployment)
5. [Production Deployment](#production-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Monitoring Setup](#monitoring-setup)
8. [Scaling Guidelines](#scaling-guidelines)
9. [Backup & Restore](#backup--restore)
10. [Rollback Procedure](#rollback-procedure)
11. [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisites

### Required Software

- **Docker** 20.10+ and **Docker Compose** 2.0+
- **Kubernetes** 1.24+ (for production)
- **kubectl** configured (for K8s)
- **PostgreSQL** 15+ (or use Docker)
- **Redis** 7+ (or use Docker)
- **Python** 3.11+ (for local development)

### Required Accounts & Keys

- **SerpAPI** account and API key
- **OpenAI** account and API key (optional)
- **Domain name** (for production)
- **SSL certificate** (for production)

---

## 💻 Local Development Setup

### Quick Start (5 minutes)

```bash
# 1. Clone repository
git clone <repository-url>
cd AmazonFBA_AI_Agent

# 2. Copy environment file
cp .env.example .env
# Edit .env with your API keys

# 3. Start services with Docker Compose
docker-compose up -d

# 4. Wait for services to be healthy
docker-compose ps

# 5. Initialize database
docker-compose exec backend python -m alembic upgrade head

# 6. Access services
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/api/v2/docs
# - Redis: localhost:6379
# - PostgreSQL: localhost:5432
```

### Manual Setup (Without Docker)

```bash
# 1. Install PostgreSQL
# macOS:
brew install postgresql
brew services start postgresql

# Ubuntu:
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# 2. Install Redis
# macOS:
brew install redis
brew services start redis

# Ubuntu:
sudo apt install redis-server
sudo systemctl start redis

# 3. Create database
createdb fba_db
createuser fba_user --pwprompt

# 4. Install Python dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 5. Set environment variables
export DATABASE_URL="postgresql://fba_user:password@localhost:5432/fba_db"
export REDIS_URL="redis://localhost:6379"
export SERPAPI_KEY="your-key"
export OPENAI_API_KEY="sk-your-key"

# 6. Initialize database
python -m alembic upgrade head

# 7. Start backend
python -m uvicorn backend.api.main:app --reload --port 8000

# 8. Start agents (separate terminal)
python -m backend.core.orchestrator
```

---

## 🐳 Docker Compose Setup

### Basic Setup

The `docker-compose.yml` file includes all services:

```yaml
services:
  - postgres:       # Database
  - redis:          # Cache & Event Bus
  - backend:        # FastAPI API server
  - frontend:       # React frontend (if available)
  - worker:         # Agents orchestrator
  - prometheus:     # Metrics
  - grafana:        # Visualization
```

### Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### Environment Variables

Create `.env` file:

```bash
# Database
POSTGRES_USER=fba_user
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=fba_db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# API Keys
SERPAPI_KEY=your-serpapi-key
OPENAI_API_KEY=sk-your-openai-key

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### Health Checks

```bash
# Check all services
docker-compose ps

# Check specific service
docker-compose exec backend curl http://localhost:8000/api/v2/health

# Check database
docker-compose exec postgres pg_isready -U fba_user

# Check Redis
docker-compose exec redis redis-cli ping
```

---

## 🧪 Staging Deployment

### Overview

Staging environment is for testing before production. Uses Kubernetes with:
- 2-3 replicas per service
- Basic monitoring
- Staging database
- Test API keys

### Steps

#### 1. Build Docker Images

```bash
# Build backend image
docker build -t fba-backend:v2.0.0 -f infrastructure/docker/Dockerfile.backend .

# Build frontend image (if available)
docker build -t fba-frontend:v2.0.0 -f infrastructure/docker/Dockerfile.frontend .

# Tag for registry
docker tag fba-backend:v2.0.0 registry.example.com/fba-backend:v2.0.0
docker tag fba-frontend:v2.0.0 registry.example.com/fba-frontend:v2.0.0

# Push to registry
docker push registry.example.com/fba-backend:v2.0.0
docker push registry.example.com/fba-frontend:v2.0.0
```

#### 2. Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace fba-staging

# Apply base configuration
kubectl apply -k k8s/staging/

# Wait for deployment
kubectl rollout status deployment/backend -n fba-staging
kubectl rollout status deployment/agents -n fba-staging
```

#### 3. Configure Secrets

```bash
# Create secrets
kubectl create secret generic fba-secrets -n fba-staging \
  --from-literal=serpapi-key=your-key \
  --from-literal=openai-key=sk-your-key \
  --from-literal=jwt-secret=your-secret

# Create database secret
kubectl create secret generic fba-db -n fba-staging \
  --from-literal=username=fba_user \
  --from-literal=password=your-password
```

#### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n fba-staging

# Check services
kubectl get services -n fba-staging

# Check logs
kubectl logs -f deployment/backend -n fba-staging
kubectl logs -f deployment/agents -n fba-staging

# Test API
kubectl port-forward svc/backend 8000:8000 -n fba-staging
curl http://localhost:8000/api/v2/health
```

---

## 🏭 Production Deployment

### Overview

Production deployment uses:
- Kubernetes cluster
- Multiple replicas (auto-scaling)
- Production database with backups
- SSL/TLS certificates
- Monitoring & alerting
- CI/CD pipeline

### Prerequisites

1. **Kubernetes Cluster**
   - Minimum 3 nodes
   - 8GB RAM per node
   - 4 CPU cores per node

2. **Container Registry**
   - Docker Hub, AWS ECR, or GCR
   - Images tagged with versions

3. **Domain & SSL**
   - Domain name configured
   - SSL certificate (Let's Encrypt recommended)

4. **Monitoring**
   - Prometheus installed
   - Grafana configured
   - Alertmanager configured

### Deployment Steps

#### 1. Prepare Production Config

```bash
# Update k8s/production/kustomization.yaml
namespace: fba-production

resources:
  - ../base

replicas:
  - name: backend
    count: 3
  - name: agents
    count: 5

configMapGenerator:
  - name: app-config
    literals:
      - ENV=production
      - LOG_LEVEL=info
```

#### 2. Set Production Secrets

```bash
# Create secrets (use secure method)
kubectl create secret generic fba-secrets -n fba-production \
  --from-file=serpapi-key=./secrets/serpapi-key.txt \
  --from-file=openai-key=./secrets/openai-key.txt \
  --from-file=jwt-secret=./secrets/jwt-secret.txt

# Database credentials
kubectl create secret generic fba-db -n fba-production \
  --from-file=username=./secrets/db-username.txt \
  --from-file=password=./secrets/db-password.txt
```

#### 3. Deploy Database

```bash
# Deploy PostgreSQL (or use managed service)
kubectl apply -f infrastructure/k8s/postgres-production.yaml

# Wait for database
kubectl wait --for=condition=ready pod -l app=postgres -n fba-production --timeout=300s

# Run migrations
kubectl run migrations --image=registry.example.com/fba-backend:v2.0.0 \
  --restart=Never \
  --rm -it \
  --env="DATABASE_URL=postgresql://..." \
  -- python -m alembic upgrade head
```

#### 4. Deploy Application

```bash
# Apply production configuration
kubectl apply -k k8s/production/

# Wait for rollout
kubectl rollout status deployment/backend -n fba-production --timeout=10m
kubectl rollout status deployment/agents -n fba-production --timeout=10m

# Verify
kubectl get pods -n fba-production
kubectl get services -n fba-production
```

#### 5. Configure Ingress

```bash
# Apply ingress configuration
kubectl apply -f infrastructure/k8s/ingress-production.yaml

# Verify ingress
kubectl get ingress -n fba-production

# Test external access
curl https://api.yourdomain.com/api/v2/health
```

#### 6. Setup Monitoring

```bash
# Deploy Prometheus
kubectl apply -f infrastructure/monitoring/prometheus/

# Deploy Grafana
kubectl apply -f infrastructure/monitoring/grafana/

# Import dashboards
kubectl apply -f infrastructure/monitoring/grafana/dashboards/
```

---

## ☸️ Kubernetes Deployment

### Cluster Requirements

- **Nodes:** 3+ nodes
- **CPU:** 4+ cores per node
- **RAM:** 8GB+ per node
- **Storage:** 100GB+ per node

### Namespace Setup

```bash
# Create namespace
kubectl create namespace fba-production

# Label namespace
kubectl label namespace fba-production environment=production
```

### Resource Limits

```yaml
# Example resource limits
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2000m"
    memory: "2Gi"
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Deployment Manifests

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: registry.example.com/fba-backend:v2.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: fba-db
              key: url
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /api/v2/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v2/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## 📊 Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'backend'
    kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
            - fba-production
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        action: keep
        regex: backend
```

### Grafana Dashboards

Import dashboards from `infrastructure/monitoring/grafana/dashboards/`:

- **System Overview** - Overall system health
- **Agent Metrics** - Per-agent performance
- **API Metrics** - Request/response metrics
- **Database Metrics** - PostgreSQL performance
- **Cache Metrics** - Redis performance

### Alertmanager Rules

```yaml
# alerts.yml
groups:
  - name: fba_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
      
      - alert: AgentDown
        expr: agent_status == 0
        for: 1m
        annotations:
          summary: "Agent {{ $labels.agent }} is down"
```

---

## 📈 Scaling Guidelines

### Horizontal Scaling

**Backend API:**
- **Min replicas:** 3
- **Max replicas:** 20
- **Scale when:** CPU > 70% or Requests > 1000/min
- **Scale down:** When CPU < 30% for 10 minutes

**Agents:**
- **Min replicas:** 5 (1 per agent type)
- **Max replicas:** 50
- **Scale when:** Queue depth > 100 or CPU > 80%
- **Scale down:** When queue depth < 10 for 10 minutes

### Vertical Scaling

**Backend API:**
- **Development:** 1 CPU, 1GB RAM
- **Staging:** 1 CPU, 2GB RAM
- **Production:** 2 CPU, 4GB RAM

**PostgreSQL:**
- **Development:** 1 CPU, 2GB RAM
- **Staging:** 2 CPU, 4GB RAM
- **Production:** 4 CPU, 16GB RAM

### Database Scaling

**Phase 1 (0-10K products):**
- Single PostgreSQL instance
- Connection pooling (PgBouncer)
- Regular backups

**Phase 2 (10K-100K products):**
- Read replicas
- Connection pooling
- Automated backups

**Phase 3 (100K+ products):**
- Sharding by category
- Read replicas
- Consider TimescaleDB for time-series

---

## 💾 Backup & Restore

### Database Backup

```bash
# Manual backup
pg_dump -h localhost -U fba_user -d fba_db > backup_$(date +%Y%m%d).sql

# Automated backup (cron)
0 2 * * * pg_dump -h localhost -U fba_user -d fba_db | gzip > /backups/fba_db_$(date +\%Y\%m\%d).sql.gz
```

### Kubernetes Backup

```bash
# Backup PostgreSQL (if using StatefulSet)
kubectl exec -n fba-production postgres-0 -- pg_dump -U fba_user fba_db > backup.sql

# Backup secrets
kubectl get secrets -n fba-production -o yaml > secrets-backup.yaml
```

### Restore Database

```bash
# Restore from backup
psql -h localhost -U fba_user -d fba_db < backup_20251029.sql

# Or in Kubernetes
kubectl exec -i -n fba-production postgres-0 -- psql -U fba_user fba_db < backup.sql
```

### Redis Backup

```bash
# Redis persistence is enabled by default
# Manual backup
redis-cli --rdb /backups/redis_dump_$(date +%Y%m%d).rdb

# Restore
redis-cli --rdb /backups/redis_dump_20251029.rdb
```

---

## ⏪ Rollback Procedure

### Application Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/backend -n fba-production

# Rollback to specific revision
kubectl rollout undo deployment/backend --to-revision=3 -n fba-production

# Check rollout history
kubectl rollout history deployment/backend -n fba-production
```

### Database Rollback

```bash
# Run down migrations
kubectl run migrations --image=registry.example.com/fba-backend:v2.0.0 \
  --restart=Never \
  --rm -it \
  --env="DATABASE_URL=postgresql://..." \
  -- python -m alembic downgrade -1

# Or restore from backup
psql -h localhost -U fba_user -d fba_db < backup_before_migration.sql
```

### Emergency Rollback

```bash
# 1. Scale down current version
kubectl scale deployment backend --replicas=0 -n fba-production

# 2. Deploy previous version
kubectl set image deployment/backend backend=registry.example.com/fba-backend:v1.9.0 -n fba-production

# 3. Scale up
kubectl scale deployment backend --replicas=3 -n fba-production

# 4. Verify
kubectl rollout status deployment/backend -n fba-production
```

---

## 🔧 Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n fba-production

# Check logs
kubectl logs <pod-name> -n fba-production

# Common causes:
# - Image pull errors (check image tag)
# - Resource limits (check resources)
# - ConfigMap/Secret errors (check env vars)
```

#### Database Connection Issues

```bash
# Test connection
kubectl run debug --image=postgres:15 --rm -it --restart=Never \
  -- psql -h postgres-service -U fba_user -d fba_db

# Check service
kubectl get svc postgres -n fba-production

# Check secrets
kubectl get secret fba-db -n fba-production -o yaml
```

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n fba-production

# Increase limits
kubectl patch deployment backend -n fba-production -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"backend","resources":{"limits":{"memory":"4Gi"}}}]}}}}}'
```

#### Event Bus Not Working

```bash
# Check Redis
kubectl exec -it redis-0 -n fba-production -- redis-cli ping

# Check Event Bus connection
kubectl logs deployment/agents -n fba-production | grep "EventBus"

# Verify Redis URL
kubectl get configmap app-config -n fba-production -o yaml
```

---

## 📚 Related Documentation

- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup
- [API.md](./API.md) - API documentation
- [ARCHITECTURE_V2.md](./ARCHITECTURE_V2.md) - Architecture overview

---

## 🆘 Support

For deployment issues:
- Check logs: `kubectl logs -f deployment/backend -n fba-production`
- Review monitoring: Grafana dashboards
- GitHub Issues: [Link]

