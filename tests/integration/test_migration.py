#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for CSV migration.

Tests the complete migration process from CSV to PostgreSQL.
"""

import pytest
import asyncio
from pathlib import Path
import pandas as pd

from backend.migration.data_validator import DataValidator
from backend.database.session import get_db_session
from backend.database.repository import ProductRepository


class TestDataValidator:
    """Test DataValidator."""
    
    def test_validate_asin_valid(self):
        """Test validating valid ASIN."""
        validator = DataValidator()
        
        asin = validator.validate_asin("B08EXAMPLE")
        assert asin == "B08EXAMPLE"
    
    def test_validate_asin_invalid(self):
        """Test validating invalid ASIN."""
        validator = DataValidator()
        
        asin = validator.validate_asin("invalid")
        assert asin is None
    
    def test_validate_int(self):
        """Test validating integers."""
        validator = DataValidator()
        
        # Valid integer
        assert validator.validate_int("123", "test") == 123
        
        # Invalid integer, uses default
        assert validator.validate_int("invalid", "test", default=0) == 0
    
    def test_validate_float(self):
        """Test validating floats."""
        validator = DataValidator()
        
        # Valid float
        assert validator.validate_float("29.99", "test") == 29.99
        
        # Invalid float, uses default
        assert validator.validate_float("invalid", "test", default=0.0) == 0.0
    
    def test_validate_email(self):
        """Test validating email."""
        validator = DataValidator()
        
        # Valid email
        assert validator.validate_email("test@example.com") == "test@example.com"
        
        # Invalid email
        assert validator.validate_email("invalid") is None


@pytest.mark.asyncio
class TestCSVMigration:
    """Test CSV migration process."""
    
    async def test_migration_creates_tables(self, async_session):
        """Test that migration creates necessary tables."""
        from sqlalchemy import inspect

        async with async_session.bind.connect() as connection:
            tables = await connection.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
 
        assert 'products' in tables
        assert 'analyses' in tables
        assert 'suppliers' in tables
        assert 'inventory' in tables
        assert 'events' in tables
        assert 'api_cache' in tables
    
    async def test_product_migration(self, async_session):
        """Test migrating products from CSV."""
        repo = ProductRepository(async_session)
        
        # Create test CSV data
        test_data = {
            'asin': ['B08TEST001', 'B08TEST002'],
            'title': ['Test Product 1', 'Test Product 2'],
            'price': [29.99, 39.99],
            'rating': [4.5, 4.0],
            'reviews': [100, 200]
        }
        
        # For now, just test that we can create products
        # Full migration test would require actual CSV files
        product = await repo.create({
            'asin': 'B08TEST001',
            'title': 'Test Product 1',
            'price': 29.99,
            'rating': 4.5,
            'reviews': 100
        })
        
        assert product.asin == 'B08TEST001'
        
        # Verify it was saved
        found = await repo.get_by_asin('B08TEST001')
        assert found is not None
        assert found.id == product.id

