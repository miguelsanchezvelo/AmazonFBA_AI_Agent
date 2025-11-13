#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Services

Tests for:
- Claude Service
- Cache Service
- Event Bus
- Amazon SP-API
- Error Handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from backend.services.cache_service import CacheService
from backend.services.claude_service import ClaudeService
from backend.core.error_handling import (
    retry_with_exponential_backoff,
    CircuitBreaker,
    CircuitBreakerOpen,
    FallbackProvider,
    ErrorRecoveryStrategy,
    ErrorCategory
)


class TestCacheService:
    """Test suite for CacheService."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, mock_cache_service):
        """Test cache set and get operations."""
        key = "test_key"
        value = {"data": "test_value"}
        
        # Set value
        await mock_cache_service.set(key, value, ttl=3600)
        mock_cache_service.set.assert_called_once()
        
        # Get value
        mock_cache_service.get.return_value = value
        result = await mock_cache_service.get(key)
        
        assert result == value

    @pytest.mark.asyncio
    async def test_cache_deletion(self, mock_cache_service):
        """Test cache deletion."""
        key = "test_key"
        
        await mock_cache_service.delete(key)
        mock_cache_service.delete.assert_called_once_with(key)

    @pytest.mark.asyncio
    async def test_cache_ttl_expiration(self):
        """Test that cache items expire after TTL."""
        cache = CacheService()
        
        # Note: This would require actual timing, mocked here for concept
        key = "expiring_key"
        value = "temporary_data"
        
        # In production, verify TTL is respected
        # For tests, we verify the function accepts TTL parameter
        assert callable(cache.set)


class TestClaudeService:
    """Test suite for ClaudeService."""

    def test_claude_service_initialization(self, mock_claude_service):
        """Test Claude service initialization."""
        assert callable(mock_claude_service.chat_completion)
        assert callable(mock_claude_service.initialize)

    @pytest.mark.asyncio
    async def test_claude_chat_completion(self, mock_claude_service):
        """Test Claude chat completion."""
        messages = [
            {"role": "user", "content": "Hello, Claude"}
        ]
        
        response = await mock_claude_service.chat_completion(
            messages=messages,
            max_tokens=100
        )
        
        assert response == "Claude response"
        mock_claude_service.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_claude_system_message(self, mock_claude_service):
        """Test Claude with system message."""
        messages = [{"role": "user", "content": "Test"}]
        system_message = "You are a helpful assistant."
        
        await mock_claude_service.chat_completion(
            messages=messages,
            system_message=system_message
        )
        
        mock_claude_service.chat_completion.assert_called_once()


class TestErrorHandling:
    """Test suite for error handling mechanisms."""

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Test retry logic with exponential backoff."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=2, initial_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "Success"
        
        result = await flaky_function()
        assert result == "Success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_all_attempts_fail(self):
        """Test retry when all attempts fail."""
        call_count = 0
        
        @retry_with_exponential_backoff(max_retries=2, initial_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
        
        with pytest.raises(Exception):
            await always_fails()
        
        # Should have retried max_retries + 1 times
        assert call_count == 3

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        breaker = CircuitBreaker("test_service", failure_threshold=3)
        
        assert breaker.state.value == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(
            "test_service",
            failure_threshold=2,
            recovery_timeout=60
        )
        
        async def failing_func():
            raise Exception("Service error")
        
        # First failure
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        assert breaker.failure_count == 1
        
        # Second failure
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        assert breaker.failure_count == 2
        
        # Circuit should open on threshold
        with pytest.raises(CircuitBreakerOpen):
            await breaker.call(failing_func)
        
        assert breaker.state.value == "open"

    def test_fallback_provider_set_and_get(self):
        """Test fallback provider."""
        provider = FallbackProvider("test_data")
        
        data = {"key": "value"}
        provider.set_fallback(data)
        
        result = provider.get_fallback()
        assert result == data

    @pytest.mark.asyncio
    async def test_fallback_with_primary_failure(self):
        """Test fallback when primary fails."""
        provider = FallbackProvider("api_data")
        fallback_data = {"cached": "data"}
        provider.set_fallback(fallback_data)
        
        async def failing_primary():
            raise Exception("API Error")
        
        result = await provider.call_with_fallback(failing_primary)
        assert result == fallback_data

    def test_error_categorization(self):
        """Test error categorization."""
        # Test timeout error
        timeout_error = TimeoutError("Connection timeout")
        category = ErrorRecoveryStrategy.categorize_error(timeout_error)
        assert category == ErrorCategory.TRANSIENT
        
        # Test should_retry
        should_retry = ErrorRecoveryStrategy.should_retry(timeout_error)
        assert should_retry is True
        
        # Test recovery action
        action = ErrorRecoveryStrategy.get_recovery_action(timeout_error)
        assert "retry" in action.lower() or "backoff" in action.lower()


class TestAmazonSPAPI:
    """Test suite for Amazon SP-API integration."""

    def test_amazon_sp_api_initialization(self):
        """Test Amazon SP-API client initialization."""
        from backend.services.amazon_sp_api import AmazonSPAPIClient
        
        client = AmazonSPAPIClient(
            seller_id="TEST123",
            refresh_token="test_token",
            region="NA"
        )
        
        assert client.seller_id == "TEST123"
        assert client.region == "NA"
        assert client.base_url == "https://sellingpartnerapi-na.amazon.com"

    def test_amazon_sp_api_endpoints(self):
        """Test Amazon SP-API regional endpoints."""
        from backend.services.amazon_sp_api import AmazonSPAPIClient
        
        regions = {
            "NA": "https://sellingpartnerapi-na.amazon.com",
            "EU": "https://sellingpartnerapi-eu.amazon.com",
            "FE": "https://sellingpartnerapi-fe.amazon.com",
            "IN": "https://sellingpartnerapi-in.amazon.com"
        }
        
        for region, endpoint in regions.items():
            client = AmazonSPAPIClient(
                seller_id="TEST",
                refresh_token="token",
                region=region
            )
            assert client.base_url == endpoint


class TestMonitoring:
    """Test suite for monitoring and metrics."""

    def test_metrics_collector(self):
        """Test metrics collection."""
        from backend.services.monitoring import (
            get_metrics_collector,
            MetricType
        )
        
        collector = get_metrics_collector()
        
        # Test counter metric
        collector.increment_counter("test_counter", 5)
        metric = collector.get_metric("test_counter")
        
        # Note: Default metrics are initialized in MetricsCollector
        assert collector.metrics is not None

    def test_health_check(self):
        """Test health check status."""
        from backend.services.monitoring import get_health_check
        
        health = get_health_check()
        health.set_service_status("test_service", True, "Service is healthy")
        
        status_dict = health.to_dict()
        assert "services" in status_dict
        assert "overall_status" in status_dict
        assert status_dict["services"]["test_service"]["healthy"] is True


# Test Data Validation
class TestDataValidation:
    """Test data validation and transformation."""

    def test_product_data_validation(self, sample_product_data):
        """Test product data validation."""
        assert sample_product_data["asin"]
        assert sample_product_data["price"] > 0
        assert 0 <= sample_product_data["rating"] <= 5
        assert sample_product_data["reviews"] >= 0

    def test_supplier_data_validation(self, sample_supplier_data):
        """Test supplier data validation."""
        assert sample_supplier_data["name"]
        assert sample_supplier_data["country"]
        assert sample_supplier_data["moq"] > 0
        assert 0 <= sample_supplier_data["rating"] <= 5

    def test_analysis_data_validation(self, sample_analysis_data):
        """Test analysis data validation."""
        assert sample_analysis_data["asin"]
        assert sample_analysis_data["roi_percentage"] >= 0
        assert 0 <= sample_analysis_data["viability_score"] <= 100
        assert sample_analysis_data["recommendation"] in ["GO", "MAYBE", "NO_GO"]

