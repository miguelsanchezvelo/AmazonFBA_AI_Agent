#!/bin/bash
# Production Deployment Script
#
# Usage: ./scripts/deploy.sh [environment]
# Example: ./scripts/deploy.sh production

set -e

ENVIRONMENT=${1:-production}
COMPOSE_FILE="docker-compose.prod.yml"

echo "🚀 Deploying Amazon FBA AI Agent to $ENVIRONMENT"
echo "=================================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if .env file exists
if [ ! -f ".env.$ENVIRONMENT" ]; then
    echo -e "${RED}❌ Error: .env.$ENVIRONMENT file not found${NC}"
    echo "Please create it from env.production.example"
    exit 1
fi

# Load environment variables
export $(cat .env.$ENVIRONMENT | grep -v '^#' | xargs)

echo ""
echo -e "${YELLOW}Step 1: Pre-deployment checks${NC}"
echo "----------------------------------------------"

# Check required environment variables
required_vars=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "SERPAPI_API_KEY"
    "ANTHROPIC_API_KEY"
    "SECRET_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo -e "${RED}❌ Error: $var is not set${NC}"
        exit 1
    else
        echo -e "${GREEN}✓${NC} $var is set"
    fi
done

# Validate Docker Compose configuration
echo ""
echo "Validating Docker Compose configuration..."
if docker-compose -f $COMPOSE_FILE config > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker Compose configuration is valid"
else
    echo -e "${RED}❌ Error: Invalid Docker Compose configuration${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 2: Backup current database${NC}"
echo "----------------------------------------------"
./scripts/backup.sh

echo ""
echo -e "${YELLOW}Step 3: Pull latest images${NC}"
echo "----------------------------------------------"
docker-compose -f $COMPOSE_FILE pull

echo ""
echo -e "${YELLOW}Step 4: Build custom images${NC}"
echo "----------------------------------------------"
docker-compose -f $COMPOSE_FILE build --no-cache

echo ""
echo -e "${YELLOW}Step 5: Stop existing containers${NC}"
echo "----------------------------------------------"
docker-compose -f $COMPOSE_FILE down

echo ""
echo -e "${YELLOW}Step 6: Start services${NC}"
echo "----------------------------------------------"
docker-compose -f $COMPOSE_FILE up -d

echo ""
echo -e "${YELLOW}Step 7: Run database migrations${NC}"
echo "----------------------------------------------"
docker-compose -f $COMPOSE_FILE exec -T backend alembic upgrade head

echo ""
echo -e "${YELLOW}Step 8: Health checks${NC}"
echo "----------------------------------------------"

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check backend health
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Backend is healthy"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    docker-compose -f $COMPOSE_FILE logs backend --tail=50
    exit 1
fi

# Check frontend
if curl -f http://localhost:80 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is accessible"
else
    echo -e "${RED}❌ Frontend check failed${NC}"
    docker-compose -f $COMPOSE_FILE logs frontend --tail=50
    exit 1
fi

# Check database
if docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U ${POSTGRES_USER} > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Database is ready"
else
    echo -e "${RED}❌ Database check failed${NC}"
    exit 1
fi

# Check Redis
if docker-compose -f $COMPOSE_FILE exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is ready"
else
    echo -e "${RED}❌ Redis check failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 9: Verify agent status${NC}"
echo "----------------------------------------------"
if curl -f http://localhost:8000/api/v2/dashboard/agents > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Agents are running"
else
    echo -e "${YELLOW}⚠${NC} Agent status check failed (may take time to initialize)"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo "=================================================="
echo ""
echo "Services:"
echo "  Frontend:    http://localhost:80"
echo "  Backend API: http://localhost:8000"
echo "  Prometheus:  http://localhost:9090"
echo "  Grafana:     http://localhost:3000"
echo ""
echo "To view logs:"
echo "  docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose -f $COMPOSE_FILE down"
echo ""

