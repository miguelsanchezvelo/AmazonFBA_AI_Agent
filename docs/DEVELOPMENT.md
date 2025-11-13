# 💻 Amazon FBA AI Agent V2 - Development Guide

**Version:** 2.0.0  
**Last Updated:** 2025-10-29

---

## 📋 Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Coding Guidelines](#coding-guidelines)
4. [Testing Guidelines](#testing-guidelines)
5. [Git Workflow](#git-workflow)
6. [Debugging Tips](#debugging-tips)
7. [Adding New Features](#adding-new-features)

---

## 🛠️ Development Environment Setup

### Prerequisites

- **Python** 3.11+
- **Node.js** 18+ (for frontend)
- **PostgreSQL** 15+ (or Docker)
- **Redis** 7+ (or Docker)
- **Git** 2.30+

### Step-by-Step Setup

#### 1. Clone Repository

```bash
git clone <repository-url>
cd AmazonFBA_AI_Agent
```

#### 2. Create Virtual Environment

```bash
# Python virtual environment
python -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
# Backend dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt
```

#### 4. Setup Local Services

```bash
# Option A: Docker Compose (Recommended)
docker-compose up -d postgres redis

# Option B: Manual installation
# See DEPLOYMENT.md for manual setup
```

#### 5. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your configuration
# Required:
# - DATABASE_URL
# - REDIS_URL
# - SERPAPI_KEY
# - OPENAI_API_KEY (optional)
```

#### 6. Initialize Database

```bash
# Run migrations
python -m alembic upgrade head

# Seed test data (optional)
python scripts/seed_data.py
```

#### 7. Start Development Server

```bash
# Backend API (auto-reload enabled)
python -m uvicorn backend.api.main:app --reload --port 8000

# Agents (separate terminal)
python -m backend.core.orchestrator
```

#### 8. Verify Setup

```bash
# Test API
curl http://localhost:8000/api/v2/health

# Test database
python -c "from backend.database.session import Session; print('DB OK')"

# Test Redis
python -c "import redis; r = redis.Redis(); print(r.ping())"
```

---

## 📁 Project Structure

```
AmazonFBA_AI_Agent/
├── backend/                 # Backend Python code
│   ├── api/               # FastAPI application
│   │   ├── main.py        # Application entry point
│   │   ├── config.py     # Configuration
│   │   ├── dependencies.py  # Dependency injection
│   │   └── routes/        # API routes
│   ├── agents/            # Agent implementations
│   │   ├── base_agent.py  # Base agent class
│   │   ├── discovery_agent.py
│   │   ├── analysis_agent.py
│   │   ├── supplier_agent.py
│   │   ├── pricing_agent.py
│   │   └── inventory_agent.py
│   ├── core/              # Core services
│   │   ├── event_bus.py   # Event bus implementation
│   │   └── orchestrator.py  # Agent orchestrator
│   ├── database/           # Database layer
│   │   ├── models.py      # SQLAlchemy models
│   │   ├── session.py     # DB session management
│   │   └── migrations/    # Alembic migrations
│   ├── models/             # Pydantic models
│   │   ├── product.py
│   │   ├── analysis.py
│   │   └── events.py
│   ├── services/           # Business logic
│   │   ├── product_service.py
│   │   └── cache_service.py
│   └── tests/              # Test files
│       ├── unit/
│       ├── integration/
│       └── e2e/
├── frontend/               # Frontend React code (if available)
├── infrastructure/         # Infrastructure as code
│   ├── docker/            # Dockerfiles
│   ├── k8s/               # Kubernetes manifests
│   └── monitoring/        # Monitoring configs
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── docker-compose.yml      # Local development
├── requirements.txt        # Python dependencies
└── README_V2.md           # Main README
```

---

## 📝 Coding Guidelines

### Python Style Guide

We follow **PEP 8** with some modifications:

#### General Rules

- **Line length:** Maximum 100 characters
- **Indentation:** 4 spaces (no tabs)
- **Imports:** Alphabetically sorted, grouped (stdlib, third-party, local)

#### Example

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module docstring.

Provide brief description of module purpose.
"""

# Standard library imports
import asyncio
from typing import Dict, List, Optional

# Third-party imports
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Local imports
from backend.models.product import ProductResponse
from backend.services.product_service import ProductService


class MyClass:
    """
    Class docstring.
    
    Detailed description of class purpose and usage.
    
    Attributes:
        name: Name of the instance
        value: Numeric value
        
    Examples:
        >>> obj = MyClass("test", 42)
        >>> print(obj.name)
        'test'
    """
    
    def __init__(self, name: str, value: int):
        """
        Initialize instance.
        
        Args:
            name: Name of the instance
            value: Numeric value (must be > 0)
            
        Raises:
            ValueError: If value <= 0
        """
        if value <= 0:
            raise ValueError("Value must be positive")
        
        self.name = name
        self.value = value
    
    def calculate(self, factor: float) -> float:
        """
        Calculate result.
        
        Args:
            factor: Multiplication factor
            
        Returns:
            Calculated result
            
        Examples:
            >>> obj = MyClass("test", 10)
            >>> obj.calculate(2.5)
            25.0
        """
        return self.value * factor
```

### Docstrings Format

Use **Google-style** docstrings:

```python
def function_name(param1: str, param2: int = 10) -> bool:
    """
    Brief description of function.
    
    Longer description explaining what the function does,
    including any important details or considerations.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is not an integer
        
    Examples:
        >>> result = function_name("test", 5)
        >>> print(result)
        True
    """
    pass
```

### Type Hints

Always use type hints:

```python
from typing import Dict, List, Optional, Any

def process_data(
    data: Dict[str, Any],
    filter_keys: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """Process data with optional filtering."""
    pass
```

### Naming Conventions

- **Classes:** `PascalCase` - `ProductService`, `DiscoveryAgent`
- **Functions/Methods:** `snake_case` - `get_product`, `process_event`
- **Constants:** `UPPER_SNAKE_CASE` - `MAX_RETRIES`, `DEFAULT_TIMEOUT`
- **Variables:** `snake_case` - `product_list`, `user_id`
- **Private:** Prefix with `_` - `_internal_method`, `_cache_key`

### Code Organization

1. **Imports** (stdlib → third-party → local)
2. **Constants**
3. **Type definitions**
4. **Classes/Functions**
5. **Main execution** (if script)

---

## 🧪 Testing Guidelines

### Test Structure

```
backend/tests/
├── unit/              # Unit tests (isolated)
│   ├── test_agents/
│   ├── test_services/
│   └── test_models/
├── integration/       # Integration tests (with DB/Redis)
│   ├── test_api/
│   └── test_agents/
└── e2e/              # End-to-end tests
    └── test_pipeline/
```

### Writing Unit Tests

```python
import pytest
from unittest.mock import Mock, patch
from backend.agents.discovery_agent import DiscoveryAgent

@pytest.mark.asyncio
async def test_discovery_agent_filters_products():
    """
    Test that DiscoveryAgent filters products correctly.
    
    Verifies:
    - Products below minimum rating are filtered out
    - Products above maximum price are filtered out
    """
    # Arrange
    agent = DiscoveryAgent(min_rating=4.0, max_price=100)
    await agent.initialize()
    
    products = [
        {"rating": 4.5, "price": 50, "asin": "B001"},
        {"rating": 3.5, "price": 50, "asin": "B002"},  # Should be filtered
        {"rating": 4.5, "price": 150, "asin": "B003"},  # Should be filtered
    ]
    
    # Act
    filtered = agent._filter_products(products)
    
    # Assert
    assert len(filtered) == 1
    assert filtered[0]["asin"] == "B001"
```

### Writing Integration Tests

```python
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

def test_list_products(client):
    """Test GET /api/v2/products endpoint."""
    response = client.get("/api/v2/products?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "products" in data
    assert len(data["products"]) <= 10
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest backend/tests/unit/test_agents/test_discovery_agent.py

# Run with coverage
pytest --cov=backend --cov-report=html

# Run with verbose output
pytest -v

# Run only failed tests
pytest --lf
```

### Coverage Goals

- **Unit tests:** 80%+ coverage
- **Integration tests:** 60%+ coverage
- **Overall:** 75%+ coverage

---

## 🔀 Git Workflow

### Branch Naming

- **Feature:** `feature/description` - `feature/add-product-filtering`
- **Bugfix:** `bugfix/description` - `bugfix/fix-memory-leak`
- **Hotfix:** `hotfix/description` - `hotfix/fix-critical-bug`
- **Release:** `release/v2.0.0`

### Commit Messages

Use conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

**Examples:**

```
feat(agents): add product discovery caching

Implement Redis caching for product discovery results
to reduce API costs and improve response times.

Closes #123

fix(api): handle database connection errors

Return 503 error when database is unavailable instead
of 500 internal server error.

Refs #456
```

### Pull Request Process

1. **Create branch** from `main`
2. **Make changes** and commit
3. **Push branch** and create PR
4. **Wait for review** and address feedback
5. **Merge** after approval

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No linting errors
- [ ] CI passes
- [ ] Self-reviewed code

---

## 🐛 Debugging Tips

### Backend Debugging

#### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Use Debugger

```python
import pdb; pdb.set_trace()  # Python debugger

# Or use VS Code debugger
# Set breakpoints and run with debugger
```

#### Check Logs

```bash
# View application logs
tail -f logs/app.log

# View agent logs
tail -f logs/agents/discovery_agent.log

# Docker logs
docker-compose logs -f backend
```

### Frontend Debugging

```javascript
// Browser DevTools
console.log('Debug info:', data);

// React DevTools
// Install browser extension

// Network requests
// Check Network tab in DevTools
```

### Agent Debugging

```python
# Enable agent debug logging
from backend.agents.discovery_agent import DiscoveryAgent

agent = DiscoveryAgent()
agent.logger.setLevel(logging.DEBUG)
await agent.start()

# Test event processing
event = {
    "event_type": "TrendDiscoveryRequested",
    "payload": {"budget": 1000}
}
result = await agent.process_event(event)
print(result)
```

### Database Debugging

```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Use database client
psql -h localhost -U fba_user -d fba_db

# Check queries
SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
```

### Event Bus Debugging

```python
# Check Event Bus connection
from backend.core.event_bus import EventBus

bus = EventBus()
await bus.connect()
print(bus.connected)
print(bus.get_metrics())

# Monitor events
async def debug_handler(event):
    print(f"Event received: {event['event_type']}")

await bus.subscribe("ProductDiscovered", debug_handler)
```

---

## ➕ Adding New Features

### 1. Create Feature Branch

```bash
git checkout -b feature/my-new-feature
```

### 2. Implement Feature

- Write code following guidelines
- Add docstrings
- Add type hints
- Write tests

### 3. Test Locally

```bash
# Run unit tests
pytest backend/tests/unit/

# Run integration tests
pytest backend/tests/integration/

# Check linting
flake8 backend/
mypy backend/

# Test manually
python -m uvicorn backend.api.main:app --reload
```

### 4. Update Documentation

- Update API.md if adding endpoints
- Update AGENTS.md if adding agents
- Add code examples

### 5. Create Pull Request

- Write clear description
- Link related issues
- Request review

### Example: Adding New Agent

1. **Create agent file:**
   ```python
   # backend/agents/new_agent.py
   from backend.agents.base_agent import BaseAgent
   
   class NewAgent(BaseAgent):
       def __init__(self):
           super().__init__(
               name="NewAgent",
               subscribed_events={"SomeEvent"}
           )
       
       async def process_event(self, event):
           # Implementation
           pass
   ```

2. **Register agent:**
   ```python
   # backend/core/orchestrator.py
   from backend.agents.new_agent import NewAgent
   
   orchestrator.register_agent(NewAgent())
   ```

3. **Add tests:**
   ```python
   # backend/tests/unit/test_agents/test_new_agent.py
   def test_new_agent():
       # Tests
       pass
   ```

4. **Update documentation:**
   - Add to AGENTS.md
   - Add event types to events.py

---

## 📚 Related Documentation

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [API.md](./API.md) - API documentation
- [AGENTS.md](./AGENTS.md) - Agent documentation

---

## 🆘 Support

For development questions:
- GitHub Discussions: [Link]
- Slack: #dev-help
- Email: dev@example.com

