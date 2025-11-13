#!/bin/bash
# Health Check Script for Production
#
# Monitors all services and reports status
# Can be run manually or via cron

set -e

COMPOSE_FILE="docker-compose.prod.yml"
BACKEND_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:80"

echo "🏥 Health Check - Amazon FBA AI Agent"
echo "=================================================="
echo "Time: $(date)"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ALL_HEALTHY=true

# Check Docker services
echo "Docker Services:"
echo "----------------------------------------------"

services=("postgres" "redis" "backend" "frontend" "prometheus" "grafana")

for service in "${services[@]}"; do
    if docker-compose -f $COMPOSE_FILE ps | grep -q "$service.*Up"; then
        echo -e "  ${GREEN}✓${NC} $service is running"
    else
        echo -e "  ${RED}✗${NC} $service is down"
        ALL_HEALTHY=false
    fi
done

# Check HTTP endpoints
echo ""
echo "HTTP Endpoints:"
echo "----------------------------------------------"

# Backend health
if curl -sf $BACKEND_URL/health > /dev/null; then
    echo -e "  ${GREEN}✓${NC} Backend API is healthy"
else
    echo -e "  ${RED}✗${NC} Backend API is not responding"
    ALL_HEALTHY=false
fi

# Frontend
if curl -sf $FRONTEND_URL > /dev/null; then
    echo -e "  ${GREEN}✓${NC} Frontend is accessible"
else
    echo -e "  ${RED}✗${NC} Frontend is not accessible"
    ALL_HEALTHY=false
fi

# Agent status
echo ""
echo "Agent Status:"
echo "----------------------------------------------"

AGENT_STATUS=$(curl -sf $BACKEND_URL/api/v2/dashboard/agents 2>/dev/null || echo "{}")

if [ "$AGENT_STATUS" != "{}" ]; then
    echo -e "  ${GREEN}✓${NC} Agents are responding"
    
    # Parse agent details (requires jq)
    if command -v jq &> /dev/null; then
        echo "$AGENT_STATUS" | jq -r '.agents | to_entries[] | "    \(.key): \(.value.status)"' 2>/dev/null || true
    fi
else
    echo -e "  ${YELLOW}⚠${NC} Unable to fetch agent status"
fi

# Database connections
echo ""
echo "Database:"
echo "----------------------------------------------"

DB_CONNECTIONS=$(docker-compose -f $COMPOSE_FILE exec -T postgres psql -U ${POSTGRES_USER:-fba_user} -d ${POSTGRES_DB:-fba_production} -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='${POSTGRES_DB:-fba_production}';" 2>/dev/null | tr -d ' \n' || echo "N/A")

if [ "$DB_CONNECTIONS" != "N/A" ]; then
    echo -e "  ${GREEN}✓${NC} Active connections: $DB_CONNECTIONS"
else
    echo -e "  ${RED}✗${NC} Unable to query database"
    ALL_HEALTHY=false
fi

# Disk usage
echo ""
echo "Disk Usage:"
echo "----------------------------------------------"

if command -v df &> /dev/null; then
    DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
    
    if [ "$DISK_USAGE" -lt 80 ]; then
        echo -e "  ${GREEN}✓${NC} Disk usage: ${DISK_USAGE}%"
    elif [ "$DISK_USAGE" -lt 90 ]; then
        echo -e "  ${YELLOW}⚠${NC} Disk usage: ${DISK_USAGE}% (warning)"
    else
        echo -e "  ${RED}✗${NC} Disk usage: ${DISK_USAGE}% (critical)"
        ALL_HEALTHY=false
    fi
fi

# Memory usage
echo ""
echo "Memory Usage:"
echo "----------------------------------------------"

if command -v free &> /dev/null; then
    MEM_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100)}')
    
    if [ "$MEM_USAGE" -lt 80 ]; then
        echo -e "  ${GREEN}✓${NC} Memory usage: ${MEM_USAGE}%"
    elif [ "$MEM_USAGE" -lt 90 ]; then
        echo -e "  ${YELLOW}⚠${NC} Memory usage: ${MEM_USAGE}% (warning)"
    else
        echo -e "  ${RED}✗${NC} Memory usage: ${MEM_USAGE}% (critical)"
    fi
fi

# Final summary
echo ""
echo "=================================================="

if [ "$ALL_HEALTHY" = true ]; then
    echo -e "${GREEN}✅ All systems healthy${NC}"
    echo "=================================================="
    exit 0
else
    echo -e "${RED}❌ Some systems are unhealthy${NC}"
    echo "=================================================="
    echo ""
    echo "Check logs with:"
    echo "  docker-compose -f $COMPOSE_FILE logs --tail=100"
    exit 1
fi

