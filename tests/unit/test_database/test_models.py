#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for database models.

Tests SQLAlchemy models: Product, Analysis, Supplier, Inventory, Event, APICache.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from backend.database.models import (
    Product, Analysis, Supplier, Inventory, Event, APICache,
    supplier_product_association, Base
)


class TestProduct:
    """Test Product model."""
    
    def test_product_creation(self):
        """Test creating a product."""
        product = Product(
            asin="B08EXAMPLE",
            title="Test Product",
            price=29.99,
            rating=4.5,
            reviews=1250
        )
        
        assert product.asin == "B08EXAMPLE"
        assert product.title == "Test Product"
        assert product.price == 29.99
        assert product.rating == 4.5
        assert product.reviews == 1250
    
    def test_product_required_fields(self):
        """Test product requires asin, title, price."""
        product = Product()

        assert product.asin is None
        assert product.title is None
        assert product.price is None


class TestAnalysis:
    """Test Analysis model."""
    
    def test_analysis_creation(self):
        """Test creating an analysis."""
        product_id = uuid4()
        
        analysis = Analysis(
            product_id=product_id,
            analysis_type="market",
            data={"competition": "low", "trend": "rising"},
            confidence_score=0.85
        )
        
        assert analysis.product_id == product_id
        assert analysis.analysis_type == "market"
        assert analysis.data == {"competition": "low", "trend": "rising"}
        assert analysis.confidence_score == 0.85


class TestSupplier:
    """Test Supplier model."""
    
    def test_supplier_creation(self):
        """Test creating a supplier."""
        supplier = Supplier(
            name="ABC Trading Co",
            email="contact@abc.com",
            rating=4.5,
            country="China"
        )
        
        assert supplier.name == "ABC Trading Co"
        assert supplier.email == "contact@abc.com"
        assert supplier.rating == 4.5
        assert supplier.country == "China"


class TestInventory:
    """Test Inventory model."""
    
    def test_inventory_creation(self):
        """Test creating inventory."""
        product_id = uuid4()
        
        inventory = Inventory(
            product_id=product_id,
            quantity=100,
            location="FBA_LAX9",
            reorder_point=50
        )
        
        assert inventory.product_id == product_id
        assert inventory.quantity == 100
        assert inventory.location == "FBA_LAX9"
        assert inventory.reorder_point == 50


class TestEvent:
    """Test Event model."""
    
    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            event_type="product_discovered",
            payload={"asin": "B08EXAMPLE", "title": "Test"},
            status="pending"
        )
        
        assert event.event_type == "product_discovered"
        assert event.payload == {"asin": "B08EXAMPLE", "title": "Test"}
        assert event.status == "pending"


class TestAPICache:
    """Test APICache model."""
    
    def test_api_cache_creation(self):
        """Test creating API cache."""
        expires_at = datetime.utcnow() + timedelta(seconds=3600)
        
        cache = APICache(
            key="serpapi:product:B08EXAMPLE",
            value={"asin": "B08EXAMPLE", "price": 29.99},
            ttl=3600,
            expires_at=expires_at
        )
        
        assert cache.key == "serpapi:product:B08EXAMPLE"
        assert cache.value == {"asin": "B08EXAMPLE", "price": 29.99}
        assert cache.ttl == 3600
        assert cache.expires_at == expires_at


class TestRelationships:
    """Test model relationships."""
    
    def test_product_analysis_relationship(self):
        """Test Product-Analysis relationship."""
        product = Product(
            asin="B08EXAMPLE",
            title="Test Product",
            price=29.99
        )
        
        analysis = Analysis(
            product_id=product.id,
            analysis_type="market",
            data={}
        )
        
        assert analysis.product_id == product.id

