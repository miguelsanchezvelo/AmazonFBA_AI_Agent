#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pytest Configuration and Fixtures

Provides shared test utilities, fixtures, and configuration
for all test suites (unit, integration, E2E).
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
import logging

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def mock_cache_service():
    """Provide a mock cache service."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.clear = AsyncMock()
    cache.connect = AsyncMock()
    cache.disconnect = AsyncMock()
    return cache


@pytest.fixture
def mock_event_bus():
    """Provide a mock event bus."""
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = AsyncMock()
    event_bus.connect = AsyncMock()
    event_bus.disconnect = AsyncMock()
    return event_bus


@pytest.fixture
def mock_database_session():
    """Provide a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_claude_service():
    """Provide a mock Claude service."""
    service = AsyncMock()
    service.initialize = AsyncMock()
    service.chat_completion = AsyncMock(return_value="Claude response")
    return service


@pytest.fixture
def mock_serpapi_client():
    """Provide a mock SerpAPI client."""
    client = AsyncMock()
    client.search = AsyncMock(return_value={
        "organic_results": [
            {
                "position": 1,
                "title": "Test Product",
                "asin": "B0123456789",
                "price": 29.99,
                "rating": 4.5,
                "reviews": 100
            }
        ]
    })
    return client


@pytest.fixture
def sample_product_data():
    """Provide sample product data for testing."""
    return {
        "asin": "B0123456789",
        "title": "Test Product - Premium Quality Item",
        "price": 29.99,
        "rating": 4.5,
        "reviews": 150,
        "bsr": 12345,
        "category": "Test Category",
        "image_url": "https://example.com/image.jpg"
    }


@pytest.fixture
def sample_supplier_data():
    """Provide sample supplier data for testing."""
    return {
        "name": "Test Supplier Inc",
        "country": "China",
        "rating": 4.8,
        "moq": 100,
        "price_per_unit": 10.0,
        "years_in_business": 5,
        "certifications": ["ISO9001", "CE"],
        "contact_email": "supplier@example.com",
        "website": "https://supplier.example.com"
    }


@pytest.fixture
def sample_analysis_data():
    """Provide sample analysis data for testing."""
    return {
        "asin": "B0123456789",
        "roi_percentage": 35.0,
        "profit_per_unit": 8.5,
        "demand_score": 75.0,
        "demand_level": "medium",
        "estimated_monthly_sales": 50,
        "competition_score": 65.0,
        "competition_level": "medium",
        "seasonality_level": "low",
        "trend_direction": "stable",
        "viability_score": 78.5,
        "recommendation": "GO"
    }


@pytest.fixture
def sample_inventory_data():
    """Provide sample inventory data for testing."""
    return {
        "asin": "B0123456789",
        "current_stock": 250,
        "reorder_point": 100,
        "lead_time_days": 30,
        "last_reorder_date": "2024-11-01",
        "total_value": 7500.0
    }

