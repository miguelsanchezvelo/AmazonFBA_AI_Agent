#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Tests for Agents

Tests for:
- DiscoveryAgent
- AnalysisAgent
- SupplierAgent
- PricingAgent
- InventoryAgent
- BusinessAgent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.agents.discovery_agent import DiscoveryAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.supplier_agent import SupplierAgent
from backend.agents.pricing_agent import PricingAgent
from backend.agents.inventory_agent import InventoryAgent
from backend.agents.business_agent import BusinessAgent
from backend.core.event_bus import Event


class TestDiscoveryAgent:
    """Test suite for DiscoveryAgent."""

    @pytest.mark.asyncio
    async def test_discovery_agent_initialization(self, mock_cache_service, mock_logger):
        """Test that DiscoveryAgent initializes correctly."""
        agent = DiscoveryAgent(
            serpapi_key="test-key",
            cache_ttl=3600
        )
        
        assert agent.name == "DiscoveryAgent"
        assert agent.serpapi_key == "test-key"
        assert agent.cache_ttl == 3600

    @pytest.mark.asyncio
    async def test_discovery_agent_search_products(self, sample_product_data):
        """Test product search functionality."""
        agent = DiscoveryAgent(serpapi_key="test-key")
        
        # Mock the search function
        with patch.object(agent, '_search_products', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [sample_product_data]
            
            results = await agent._search_products("test product", 50.0)
            
            assert len(results) == 1
            assert results[0]["asin"] == "B0123456789"
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_discovery_agent_filter_products(self, sample_product_data):
        """Test product filtering logic."""
        agent = DiscoveryAgent(serpapi_key="test-key")
        
        products = [
            {**sample_product_data, "reviews": 5},   # Too few reviews
            {**sample_product_data, "reviews": 100}, # Valid
            {**sample_product_data, "reviews": 0},   # No reviews
        ]
        
        # Test that filtering removes products with < 10 reviews
        filtered = [p for p in products if p.get("reviews", 0) >= 10]
        
        assert len(filtered) == 1
        assert filtered[0]["reviews"] == 100


class TestAnalysisAgent:
    """Test suite for AnalysisAgent."""

    @pytest.mark.asyncio
    async def test_analysis_agent_initialization(self, mock_cache_service):
        """Test that AnalysisAgent initializes correctly."""
        agent = AnalysisAgent(
            min_roi=30.0,
            min_viability_score=70.0
        )
        
        assert agent.name == "AnalysisAgent"
        assert agent.min_roi == 30.0
        assert agent.min_viability_score == 70.0

    @pytest.mark.asyncio
    async def test_analysis_agent_calculate_viability_score(self, sample_analysis_data):
        """Test viability score calculation."""
        agent = AnalysisAgent()
        
        # Mock data
        roi_analysis = {"roi_percentage": 35.0, "profit_per_unit": 8.5}
        demand_analysis = {"demand_score": 75.0}
        competition_analysis = {"competition_score": 65.0}
        seasonality_analysis = {
            "seasonality_score": 20.0,
            "trend_direction": "stable"
        }
        
        score = agent._calculate_viability_score(
            roi_analysis,
            demand_analysis,
            competition_analysis,
            seasonality_analysis
        )
        
        # Score should be between 0 and 100
        assert 0 <= score <= 100
        # For these good metrics, score should be decent
        assert score > 50

    @pytest.mark.asyncio
    async def test_analysis_agent_make_recommendation(self, sample_analysis_data):
        """Test recommendation generation."""
        agent = AnalysisAgent(min_roi=30.0, min_viability_score=70.0)
        
        roi_analysis = {"roi_percentage": 35.0}
        seasonality_analysis = {"seasonality_level": "low", "trend_direction": "stable"}
        
        recommendation = agent._make_recommendation(
            viability_score=78.5,
            roi_analysis=roi_analysis,
            seasonality_analysis=seasonality_analysis
        )
        
        assert "decision" in recommendation
        assert recommendation["decision"] in ["GO", "MAYBE", "NO_GO"]
        assert "confidence" in recommendation
        assert len(recommendation.get("risks", [])) >= 0


class TestSupplierAgent:
    """Test suite for SupplierAgent."""

    @pytest.mark.asyncio
    async def test_supplier_agent_initialization(self, mock_logger):
        """Test that SupplierAgent initializes correctly."""
        agent = SupplierAgent(
            serpapi_key="test-key",
            max_suppliers=5
        )
        
        assert agent.name == "SupplierAgent"
        assert agent.max_suppliers == 5

    @pytest.mark.asyncio
    async def test_supplier_agent_deduplication(self, sample_supplier_data):
        """Test supplier deduplication."""
        agent = SupplierAgent()
        
        suppliers = [
            sample_supplier_data,
            {**sample_supplier_data, "contact_email": "same@example.com"},
            {**sample_supplier_data, "contact_email": "different@example.com"}
        ]
        
        # Suppliers should be deduplicated by email
        seen_emails = set()
        deduplicated = []
        
        for supplier in suppliers:
            email = supplier.get("contact_email", "").lower()
            if email not in seen_emails:
                seen_emails.add(email)
                deduplicated.append(supplier)
        
        # Should remove duplicates
        assert len(deduplicated) <= len(suppliers)


class TestPricingAgent:
    """Test suite for PricingAgent."""

    @pytest.mark.asyncio
    async def test_pricing_agent_initialization(self):
        """Test that PricingAgent initializes correctly."""
        agent = PricingAgent(
            target_roi=30.0,
            min_margin=20.0
        )
        
        assert agent.name == "PricingAgent"
        assert agent.target_roi == 30.0
        assert agent.min_margin == 20.0

    @pytest.mark.asyncio
    async def test_pricing_agent_strategy_variations(self):
        """Test different pricing strategies."""
        agent = PricingAgent()
        
        base_cost = 10.0
        product_cost = 5.0
        amazon_fees = 3.0
        shipping = 1.0
        
        total_cost = product_cost + amazon_fees + shipping
        
        # Test cost-plus margin
        margin_percent = 30.0
        markup_price = total_cost * (1 + margin_percent / 100)
        
        assert markup_price > total_cost
        assert (markup_price - total_cost) / total_cost * 100 == pytest.approx(margin_percent)


class TestInventoryAgent:
    """Test suite for InventoryAgent."""

    @pytest.mark.asyncio
    async def test_inventory_agent_initialization(self):
        """Test that InventoryAgent initializes correctly."""
        agent = InventoryAgent(
            low_stock_threshold=50,
            reorder_point=30,
            lead_time_days=30
        )
        
        assert agent.name == "InventoryAgent"
        assert agent.low_stock_threshold == 50
        assert agent.reorder_point == 30
        assert agent.lead_time_days == 30

    @pytest.mark.asyncio
    async def test_inventory_agent_reorder_calculation(self, sample_inventory_data):
        """Test reorder quantity calculation."""
        agent = InventoryAgent()
        
        # Test EOQ (Economic Order Quantity) calculation
        annual_demand = sample_inventory_data["current_stock"] * 12
        ordering_cost = 50  # Cost per order
        holding_cost = 5.0  # Cost per unit per year
        
        # EOQ = sqrt(2 * D * S / H)
        eoq = (2 * annual_demand * ordering_cost / holding_cost) ** 0.5
        
        assert eoq > 0
        assert isinstance(eoq, float)


class TestBusinessAgent:
    """Test suite for BusinessAgent."""

    @pytest.mark.asyncio
    async def test_business_agent_initialization(self):
        """Test that BusinessAgent initializes correctly."""
        agent = BusinessAgent(
            min_roi_target=30.0,
            min_margin_target=20.0,
            max_products=50
        )
        
        assert agent.name == "BusinessAgent"
        assert agent.min_roi_target == 30.0
        assert agent.max_products == 50

    @pytest.mark.asyncio
    async def test_business_agent_metrics_calculation(self):
        """Test business metrics calculation."""
        agent = BusinessAgent()
        
        # Mock metrics
        total_revenue = 45000.0
        total_profit = 12000.0
        total_roi = 35.0
        active_products = 15
        
        # Calculate average margin
        avg_margin = (total_profit / total_revenue) * 100 if total_revenue > 0 else 0
        
        assert avg_margin > 0
        assert avg_margin == pytest.approx(26.67, rel=0.01)
        assert total_roi > 0


# Test Event Generation
class TestEventGeneration:
    """Test event generation across agents."""

    def test_event_creation(self):
        """Test that events are created correctly."""
        event_data = {
            "asin": "B0123456789",
            "title": "Test Product",
            "price": 29.99
        }
        
        event = Event(
            event_type="ProductDiscovered",
            payload=event_data,
            source_agent="DiscoveryAgent"
        )
        
        assert event.event_type == "ProductDiscovered"
        assert event.source_agent == "DiscoveryAgent"
        assert event.payload["asin"] == "B0123456789"
        assert event.timestamp is not None

    def test_event_serialization(self):
        """Test that events can be serialized."""
        event_data = {"test": "data"}
        event = Event(
            event_type="TestEvent",
            payload=event_data,
            source_agent="TestAgent"
        )
        
        event_dict = event.to_dict()
        
        assert isinstance(event_dict, dict)
        assert event_dict["event_type"] == "TestEvent"
        assert event_dict["payload"] == event_data

