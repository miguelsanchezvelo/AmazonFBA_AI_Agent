#!/bin/bash
# Environment Validation Script
#
# Validates that all required environment variables are set
# and have valid values before deployment

set -e

ENV_FILE=${1:-.env.production}

echo "🔍 Validating Environment Configuration"
echo "=================================================="
echo "File: $ENV_FILE"
echo ""

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
export $(cat $ENV_FILE | grep -v '^#' | xargs)

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

# Function to check variable
check_var() {
    local var_name=$1
    local var_type=${2:-required}
    local var_value="${!var_name}"
    
    if [ -z "$var_value" ]; then
        if [ "$var_type" = "required" ]; then
            echo -e "  ${RED}✗${NC} $var_name is not set (REQUIRED)"
            ((ERRORS++))
        else
            echo -e "  ${YELLOW}⚠${NC} $var_name is not set (optional)"
            ((WARNINGS++))
        fi
    else
        # Check for placeholder values
        if [[ "$var_value" == *"CHANGE_ME"* ]] || [[ "$var_value" == *"your_"* ]]; then
            echo -e "  ${RED}✗${NC} $var_name contains placeholder value"
            ((ERRORS++))
        else
            echo -e "  ${GREEN}✓${NC} $var_name is set"
        fi
    fi
}

echo "Database Configuration:"
echo "----------------------------------------------"
check_var "POSTGRES_DB" "required"
check_var "POSTGRES_USER" "required"
check_var "POSTGRES_PASSWORD" "required"
check_var "DATABASE_URL" "required"

echo ""
echo "Redis Configuration:"
echo "----------------------------------------------"
check_var "REDIS_PASSWORD" "required"
check_var "REDIS_URL" "required"

echo ""
echo "API Keys:"
echo "----------------------------------------------"
check_var "SERPAPI_API_KEY" "required"
check_var "ANTHROPIC_API_KEY" "required"
check_var "OPENAI_API_KEY" "optional"

echo ""
echo "Amazon SP-API (Optional):"
echo "----------------------------------------------"
check_var "AMAZON_SELLER_ID" "optional"
check_var "AMAZON_REFRESH_TOKEN" "optional"
check_var "AWS_ACCESS_KEY_ID" "optional"
check_var "AWS_SECRET_ACCESS_KEY" "optional"

echo ""
echo "Application:"
echo "----------------------------------------------"
check_var "ENVIRONMENT" "required"
check_var "SECRET_KEY" "required"
check_var "ALLOWED_HOSTS" "required"

echo ""
echo "Frontend:"
echo "----------------------------------------------"
check_var "VITE_API_URL" "required"

echo ""
echo "Monitoring:"
echo "----------------------------------------------"
check_var "GRAFANA_PASSWORD" "required"

echo ""
echo "=================================================="

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Environment validation passed${NC}"
    echo ""
    echo "Summary:"
    echo "  Errors: $ERRORS"
    echo "  Warnings: $WARNINGS"
    echo ""
    echo "You can proceed with deployment!"
    exit 0
else
    echo -e "${RED}❌ Environment validation failed${NC}"
    echo ""
    echo "Summary:"
    echo "  Errors: $ERRORS"
    echo "  Warnings: $WARNINGS"
    echo ""
    echo "Please fix the errors before deploying."
    exit 1
fi

