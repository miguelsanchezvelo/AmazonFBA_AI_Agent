# Testing Guide

Comprehensive test suite for the Amazon FBA AI Agent system.

## Test Structure

```
backend/tests/
├── conftest.py              # Shared fixtures and configuration
├── requirements.txt         # Test dependencies
├── unit/                    # Unit tests
│   ├── test_agents.py      # Agent logic tests
│   ├── test_services.py    # Service tests
│   └── test_utils.py       # Utility function tests
├── integration/            # Integration tests
│   ├── test_api_endpoints.py  # API endpoint tests
│   └── test_workflows.py   # Workflow interaction tests
└── e2e/                    # End-to-end tests
    ├── test_workflows.py   # Complete business workflows
    └── test_scenarios.py   # Real-world scenarios
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r backend/tests/requirements.txt
```

### Run All Tests

```bash
pytest backend/tests/
```

### Run by Category

```bash
# Unit tests only
pytest backend/tests/unit/ -v

# Integration tests only
pytest backend/tests/integration/ -v

# E2E tests only
pytest backend/tests/e2e/ -v

# By marker
pytest -m unit
pytest -m integration
pytest -m e2e
```

### Run with Coverage

```bash
pytest backend/tests/ --cov=backend --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Run Specific Test

```bash
pytest backend/tests/unit/test_agents.py::TestDiscoveryAgent::test_discovery_agent_initialization -v
```

### Run Tests in Parallel

```bash
pytest backend/tests/ -n auto
```

### Run with Timeout

```bash
pytest backend/tests/ --timeout=300
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.asyncio` - Async tests
- `@pytest.mark.slow` - Slow/long-running tests

## Fixtures Available

See `conftest.py` for available fixtures:

- `mock_logger` - Mock logger
- `mock_cache_service` - Mock cache
- `mock_event_bus` - Mock event bus
- `mock_database_session` - Mock DB session
- `mock_claude_service` - Mock Claude
- `sample_product_data` - Sample product
- `sample_supplier_data` - Sample supplier
- `sample_analysis_data` - Sample analysis
- `sample_inventory_data` - Sample inventory

## Coverage Reports

```bash
# Generate coverage report
pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

## Continuous Integration

Tests can be run in CI/CD pipelines:

```bash
# Exit with failure if coverage < 80%
pytest backend/tests/ --cov=backend --cov-fail-under=80
```

## Writing New Tests

1. Create test file in appropriate directory
2. Use fixtures from `conftest.py`
3. Add appropriate marker: `@pytest.mark.unit`, `@pytest.mark.integration`, etc.
4. Use descriptive test names: `test_<function>_<scenario>`
5. Include docstrings

Example:

```python
@pytest.mark.unit
async def test_agent_initialization(mock_logger):
    """Test that agent initializes with correct configuration."""
    agent = DiscoveryAgent(serpapi_key="test-key")
    assert agent.name == "DiscoveryAgent"
```

## Troubleshooting

### Tests Hang
- Add `--timeout=300` flag
- Check for infinite loops in code
- Verify async mocks are configured correctly

### Import Errors
- Ensure `__init__.py` files exist in test directories
- Check Python path configuration

### Flaky Tests
- Use `pytest-rerunfailures` plugin
- Increase timeouts for slow operations
- Mock external services properly

## Performance

- Unit tests should be fast (< 100ms each)
- Integration tests (100ms - 1s)
- E2E tests (> 1s)

Run only fast tests:
```bash
pytest backend/tests/ -m "not slow"
```

## Test Results

Tests are considered passing if:
- ✅ All assertions pass
- ✅ No exceptions raised
- ✅ Expected mocks were called
- ✅ Coverage meets minimum threshold

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [pytest-cov](https://pytest-cov.readthedocs.io/)

