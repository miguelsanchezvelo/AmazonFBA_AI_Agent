#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for database repositories.

Tests repository pattern implementations with async operations.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from backend.database.repository import (
    ProductRepository, AnalysisRepository, SupplierRepository,
    InventoryRepository, EventRepository, APICacheRepository
)
from backend.database.models import Product, Analysis, Supplier, Inventory, Event, APICache


@pytest.mark.asyncio
class TestProductRepository:
    """Test ProductRepository."""
    
    async def test_create_product(self, async_session):
        """Test creating a product."""
        repo = ProductRepository(async_session)
        
        product_data = {
            'asin': 'B08TEST001',
            'title': 'Test Product',
            'price': 29.99,
            'rating': 4.5,
            'reviews': 100
        }
        
        product = await repo.create(product_data)
        
        assert product.asin == 'B08TEST001'
        assert product.title == 'Test Product'
        assert product.price == 29.99
    
    async def test_get_by_asin(self, async_session):
        """Test getting product by ASIN."""
        repo = ProductRepository(async_session)
        
        # Create product
        product = await repo.create({
            'asin': 'B08TEST002',
            'title': 'Test Product 2',
            'price': 39.99
        })
        
        # Get product
        found = await repo.get_by_asin('B08TEST002')
        
        assert found is not None
        assert found.asin == 'B08TEST002'
        assert found.id == product.id
    
    async def test_search_products(self, async_session):
        """Test searching products."""
        repo = ProductRepository(async_session)
        
        # Create test products
        await repo.create({
            'asin': 'B08TEST003',
            'title': 'Electronics Product',
            'price': 49.99,
            'category': 'Electronics'
        })
        
        # Search by category
        results = await repo.search({'category': 'Electronics'})
        
        assert len(results) >= 1
        assert all(p.category == 'Electronics' for p in results)


@pytest.mark.asyncio
class TestAnalysisRepository:
    """Test AnalysisRepository."""
    
    async def test_create_analysis(self, async_session):
        """Test creating an analysis."""
        # Create product first
        product_repo = ProductRepository(async_session)
        product = await product_repo.create({
            'asin': 'B08TEST004',
            'title': 'Test Product',
            'price': 29.99
        })
        
        # Create analysis
        analysis_repo = AnalysisRepository(async_session)
        analysis = await analysis_repo.create({
            'product_id': product.id,
            'analysis_type': 'market',
            'data': {'competition': 'low'},
            'confidence_score': 0.85
        })
        
        assert analysis.product_id == product.id
        assert analysis.analysis_type == 'market'
        assert analysis.data == {'competition': 'low'}


@pytest.mark.asyncio
class TestSupplierRepository:
    """Test SupplierRepository."""
    
    async def test_create_supplier(self, async_session):
        """Test creating a supplier."""
        repo = SupplierRepository(async_session)
        
        supplier = await repo.create({
            'name': 'Test Supplier',
            'email': 'test@supplier.com',
            'country': 'China',
            'rating': 4.5
        })
        
        assert supplier.name == 'Test Supplier'
        assert supplier.email == 'test@supplier.com'
    
    async def test_get_by_email(self, async_session):
        """Test getting supplier by email."""
        repo = SupplierRepository(async_session)
        
        # Create supplier
        supplier = await repo.create({
            'name': 'Test Supplier 2',
            'email': 'test2@supplier.com',
            'country': 'China'
        })
        
        # Get supplier
        found = await repo.get_by_email('test2@supplier.com')
        
        assert found is not None
        assert found.email == 'test2@supplier.com'
        assert found.id == supplier.id


@pytest.mark.asyncio
class TestEventRepository:
    """Test EventRepository."""
    
    async def test_create_event(self, async_session):
        """Test creating an event."""
        repo = EventRepository(async_session)
        
        event = await repo.create({
            'event_type': 'product_discovered',
            'payload': {'asin': 'B08TEST005'}
        })
        
        assert event.event_type == 'product_discovered'
        assert event.status == 'pending'
        assert event.payload == {'asin': 'B08TEST005'}
    
    async def test_get_pending_events(self, async_session):
        """Test getting pending events."""
        repo = EventRepository(async_session)
        
        # Create pending event
        await repo.create({
            'event_type': 'test_event',
            'payload': {}
        })
        
        # Get pending events
        pending = await repo.get_pending()
        
        assert len(pending) >= 1
        assert all(e.status == 'pending' for e in pending)


@pytest.mark.asyncio
class TestAPICacheRepository:
    """Test APICacheRepository."""
    
    async def test_set_get_cache(self, async_session):
        """Test setting and getting cache."""
        repo = APICacheRepository(async_session)
        
        # Set cache
        cache = await repo.set(
            key='test:cache:key',
            value={'data': 'test'},
            ttl=3600
        )
        
        assert cache.key == 'test:cache:key'
        
        # Get cache
        value = await repo.get('test:cache:key')
        
        assert value is not None
        assert value == {'data': 'test'}

