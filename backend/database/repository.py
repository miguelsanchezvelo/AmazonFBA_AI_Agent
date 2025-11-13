#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Repository Pattern Implementation for Database Access.

Implementa repositorios con async/await para todas las operaciones de base de datos.
Cada repositorio encapsula la lógica de acceso a datos para un modelo específico.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.models import (
    Product, Analysis, Supplier, Inventory, Event, APICache,
    supplier_product_association
)

logger = logging.getLogger(__name__)


class ProductRepository:
    """Repository for Product model operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize ProductRepository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_asin(self, asin: str) -> Optional[Product]:
        """
        Get product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            Product instance if found, None otherwise
            
        Examples:
            >>> repo = ProductRepository(session)
            >>> product = await repo.get_by_asin("B08EXAMPLE")
        """
        try:
            result = await self.session.execute(
                select(Product).where(Product.asin == asin)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting product by ASIN {asin}: {e}")
            raise
    
    async def search(self, filters: Dict[str, Any]) -> List[Product]:
        """
        Search products with filters.
        
        Args:
            filters: Dictionary with filter criteria
                - asin: Filter by ASIN (partial match)
                - title: Filter by title (partial match)
                - category: Filter by category
                - min_price: Minimum price
                - max_price: Maximum price
                - min_rating: Minimum rating
                
        Returns:
            List of matching Product instances
            
        Examples:
            >>> repo = ProductRepository(session)
            >>> products = await repo.search({
            ...     "category": "Electronics",
            ...     "min_price": 10.0,
            ...     "max_price": 100.0
            ... })
        """
        try:
            query = select(Product)
            
            # Apply filters
            if "asin" in filters:
                query = query.where(Product.asin.ilike(f"%{filters['asin']}%"))
            if "title" in filters:
                query = query.where(Product.title.ilike(f"%{filters['title']}%"))
            if "category" in filters:
                query = query.where(Product.category == filters["category"])
            if "min_price" in filters:
                query = query.where(Product.price >= filters["min_price"])
            if "max_price" in filters:
                query = query.where(Product.price <= filters["max_price"])
            if "min_rating" in filters:
                query = query.where(Product.rating >= filters["min_rating"])
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            raise
    
    async def create(self, product_data: Dict[str, Any]) -> Product:
        """
        Create a new product.
        
        Args:
            product_data: Dictionary with product fields
                - asin: Required
                - title: Required
                - price: Required
                - rating: Optional
                - reviews: Optional
                - bsr: Optional
                - category: Optional
                - image_url: Optional
                
        Returns:
            Created Product instance
            
        Examples:
            >>> repo = ProductRepository(session)
            >>> product = await repo.create({
            ...     "asin": "B08EXAMPLE",
            ...     "title": "Example Product",
            ...     "price": 29.99
            ... })
        """
        try:
            product = Product(**product_data)
            self.session.add(product)
            await self.session.flush()
            await self.session.refresh(product)
            logger.info(f"Created product: {product.asin}")
            return product
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            await self.session.rollback()
            raise
    
    async def update(self, asin: str, data: Dict[str, Any]) -> Optional[Product]:
        """
        Update product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            data: Dictionary with fields to update
            
        Returns:
            Updated Product instance if found, None otherwise
            
        Examples:
            >>> repo = ProductRepository(session)
            >>> product = await repo.update("B08EXAMPLE", {"price": 39.99})
        """
        try:
            # Update updated_at timestamp
            data["updated_at"] = datetime.utcnow()
            
            stmt = (
                update(Product)
                .where(Product.asin == asin)
                .values(**data)
                .returning(Product)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error updating product {asin}: {e}")
            await self.session.rollback()
            raise
    
    async def delete(self, asin: str) -> bool:
        """
        Delete product by ASIN.
        
        Args:
            asin: Amazon Standard Identification Number
            
        Returns:
            True if deleted, False if not found
            
        Examples:
            >>> repo = ProductRepository(session)
            >>> deleted = await repo.delete("B08EXAMPLE")
        """
        try:
            stmt = delete(Product).where(Product.asin == asin)
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting product {asin}: {e}")
            await self.session.rollback()
            raise
    
    async def bulk_create(self, products: List[Dict[str, Any]]) -> List[Product]:
        """
        Bulk create products for better performance.
        
        Args:
            products: List of dictionaries with product data
            
        Returns:
            List of created Product instances
            
        Examples:
            >>> repo = ProductRepository(session)
            >>> products = await repo.bulk_create([
            ...     {"asin": "B08EXAMPLE1", "title": "Product 1", "price": 29.99},
            ...     {"asin": "B08EXAMPLE2", "title": "Product 2", "price": 39.99}
            ... ])
        """
        try:
            product_objects = [Product(**product_data) for product_data in products]
            self.session.add_all(product_objects)
            await self.session.flush()
            
            # Refresh all objects to get IDs
            for product in product_objects:
                await self.session.refresh(product)
            
            logger.info(f"Bulk created {len(product_objects)} products")
            return product_objects
        except Exception as e:
            logger.error(f"Error bulk creating products: {e}")
            await self.session.rollback()
            raise


class AnalysisRepository:
    """Repository for Analysis model operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize AnalysisRepository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_product_id(self, product_id: UUID) -> List[Analysis]:
        """
        Get all analyses for a product.
        
        Args:
            product_id: Product UUID
            
        Returns:
            List of Analysis instances
            
        Examples:
            >>> repo = AnalysisRepository(session)
            >>> analyses = await repo.get_by_product_id(product_id)
        """
        try:
            result = await self.session.execute(
                select(Analysis)
                .where(Analysis.product_id == product_id)
                .order_by(Analysis.created_at.desc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting analyses for product {product_id}: {e}")
            raise
    
    async def get_latest_by_type(self, product_id: UUID, analysis_type: str) -> Optional[Analysis]:
        """
        Get latest analysis of specific type for a product.
        
        Args:
            product_id: Product UUID
            analysis_type: Type of analysis ('market', 'profitability', 'demand', etc.)
            
        Returns:
            Latest Analysis instance if found, None otherwise
            
        Examples:
            >>> repo = AnalysisRepository(session)
            >>> analysis = await repo.get_latest_by_type(product_id, "market")
        """
        try:
            result = await self.session.execute(
                select(Analysis)
                .where(
                    and_(
                        Analysis.product_id == product_id,
                        Analysis.analysis_type == analysis_type
                    )
                )
                .order_by(Analysis.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting latest {analysis_type} analysis for product {product_id}: {e}")
            raise
    
    async def create(self, analysis_data: Dict[str, Any]) -> Analysis:
        """
        Create a new analysis.
        
        Args:
            analysis_data: Dictionary with analysis fields
                - product_id: Required
                - analysis_type: Required
                - data: Required (JSON)
                - confidence_score: Optional
                
        Returns:
            Created Analysis instance
            
        Examples:
            >>> repo = AnalysisRepository(session)
            >>> analysis = await repo.create({
            ...     "product_id": product_id,
            ...     "analysis_type": "market",
            ...     "data": {"competition": "low"},
            ...     "confidence_score": 0.85
            ... })
        """
        try:
            analysis = Analysis(**analysis_data)
            self.session.add(analysis)
            await self.session.flush()
            await self.session.refresh(analysis)
            logger.info(f"Created {analysis.analysis_type} analysis for product {analysis.product_id}")
            return analysis
        except Exception as e:
            logger.error(f"Error creating analysis: {e}")
            await self.session.rollback()
            raise


class SupplierRepository:
    """Repository for Supplier model operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize SupplierRepository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_email(self, email: str) -> Optional[Supplier]:
        """
        Get supplier by email.
        
        Args:
            email: Supplier email address
            
        Returns:
            Supplier instance if found, None otherwise
            
        Examples:
            >>> repo = SupplierRepository(session)
            >>> supplier = await repo.get_by_email("contact@example.com")
        """
        try:
            result = await self.session.execute(
                select(Supplier).where(Supplier.email == email)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting supplier by email {email}: {e}")
            raise
    
    async def search(self, filters: Dict[str, Any]) -> List[Supplier]:
        """
        Search suppliers with filters.
        
        Args:
            filters: Dictionary with filter criteria
                - name: Filter by name (partial match)
                - country: Filter by country
                - min_rating: Minimum rating
                
        Returns:
            List of matching Supplier instances
            
        Examples:
            >>> repo = SupplierRepository(session)
            >>> suppliers = await repo.search({"country": "China", "min_rating": 4.0})
        """
        try:
            query = select(Supplier)
            
            # Apply filters
            if "name" in filters:
                query = query.where(Supplier.name.ilike(f"%{filters['name']}%"))
            if "country" in filters:
                query = query.where(Supplier.country == filters["country"])
            if "min_rating" in filters:
                query = query.where(Supplier.rating >= filters["min_rating"])
            
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error searching suppliers: {e}")
            raise
    
    async def create(self, supplier_data: Dict[str, Any]) -> Supplier:
        """
        Create a new supplier.
        
        Args:
            supplier_data: Dictionary with supplier fields
                - name: Required
                - email: Required (unique)
                - rating: Optional
                - country: Optional
                - communication_history: Optional (JSON)
                
        Returns:
            Created Supplier instance
            
        Examples:
            >>> repo = SupplierRepository(session)
            >>> supplier = await repo.create({
            ...     "name": "ABC Trading Co",
            ...     "email": "contact@abc.com",
            ...     "country": "China"
            ... })
        """
        try:
            supplier = Supplier(**supplier_data)
            self.session.add(supplier)
            await self.session.flush()
            await self.session.refresh(supplier)
            logger.info(f"Created supplier: {supplier.email}")
            return supplier
        except Exception as e:
            logger.error(f"Error creating supplier: {e}")
            await self.session.rollback()
            raise
    
    async def add_product(self, supplier_id: UUID, product_id: UUID) -> bool:
        """
        Add product to supplier (many-to-many relationship).
        
        Args:
            supplier_id: Supplier UUID
            product_id: Product UUID
            
        Returns:
            True if added successfully, False otherwise
            
        Examples:
            >>> repo = SupplierRepository(session)
            >>> added = await repo.add_product(supplier_id, product_id)
        """
        try:
            # Check if association already exists
            stmt = select(supplier_product_association).where(
                and_(
                    supplier_product_association.c.supplier_id == supplier_id,
                    supplier_product_association.c.product_id == product_id
                )
            )
            result = await self.session.execute(stmt)
            if result.first():
                return False  # Already exists
            
            # Insert association
            stmt = supplier_product_association.insert().values(
                supplier_id=supplier_id,
                product_id=product_id
            )
            await self.session.execute(stmt)
            await self.session.flush()
            logger.info(f"Added product {product_id} to supplier {supplier_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding product to supplier: {e}")
            await self.session.rollback()
            raise


class InventoryRepository:
    """Repository for Inventory model operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize InventoryRepository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_product_id(self, product_id: UUID) -> Optional[Inventory]:
        """
        Get inventory for a product.
        
        Args:
            product_id: Product UUID
            
        Returns:
            Inventory instance if found, None otherwise
            
        Examples:
            >>> repo = InventoryRepository(session)
            >>> inventory = await repo.get_by_product_id(product_id)
        """
        try:
            result = await self.session.execute(
                select(Inventory).where(Inventory.product_id == product_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting inventory for product {product_id}: {e}")
            raise
    
    async def update_quantity(self, product_id: UUID, quantity: int) -> Optional[Inventory]:
        """
        Update inventory quantity for a product.
        
        Args:
            product_id: Product UUID
            quantity: New quantity value
            
        Returns:
            Updated Inventory instance if found, None otherwise
            
        Examples:
            >>> repo = InventoryRepository(session)
            >>> inventory = await repo.update_quantity(product_id, 100)
        """
        try:
            stmt = (
                update(Inventory)
                .where(Inventory.product_id == product_id)
                .values(
                    quantity=quantity,
                    updated_at=datetime.utcnow()
                )
                .returning(Inventory)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error updating inventory quantity for product {product_id}: {e}")
            await self.session.rollback()
            raise
    
    async def get_low_stock(self, reorder_point: int) -> List[Inventory]:
        """
        Get all inventory items with quantity below reorder point.
        
        Args:
            reorder_point: Minimum stock level threshold
            
        Returns:
            List of Inventory instances with low stock
            
        Examples:
            >>> repo = InventoryRepository(session)
            >>> low_stock = await repo.get_low_stock(reorder_point=50)
        """
        try:
            result = await self.session.execute(
                select(Inventory)
                .where(Inventory.quantity <= reorder_point)
                .order_by(Inventory.quantity.asc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting low stock inventory: {e}")
            raise


class EventRepository:
    """Repository for Event model operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize EventRepository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def create(self, event_data: Dict[str, Any]) -> Event:
        """
        Create a new event.
        
        Args:
            event_data: Dictionary with event fields
                - event_type: Required
                - payload: Required (JSON)
                - status: Optional (default: 'pending')
                
        Returns:
            Created Event instance
            
        Examples:
            >>> repo = EventRepository(session)
            >>> event = await repo.create({
            ...     "event_type": "product_discovered",
            ...     "payload": {"asin": "B08EXAMPLE"}
            ... })
        """
        try:
            if "status" not in event_data:
                event_data["status"] = "pending"
            
            event = Event(**event_data)
            self.session.add(event)
            await self.session.flush()
            await self.session.refresh(event)
            logger.info(f"Created event: {event.event_type} ({event.id})")
            return event
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            await self.session.rollback()
            raise
    
    async def get_pending(self) -> List[Event]:
        """
        Get all pending events.
        
        Returns:
            List of pending Event instances
            
        Examples:
            >>> repo = EventRepository(session)
            >>> pending = await repo.get_pending()
        """
        try:
            result = await self.session.execute(
                select(Event)
                .where(Event.status == "pending")
                .order_by(Event.created_at.asc())
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting pending events: {e}")
            raise
    
    async def mark_processed(self, event_id: UUID) -> Optional[Event]:
        """
        Mark event as processed.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Updated Event instance if found, None otherwise
            
        Examples:
            >>> repo = EventRepository(session)
            >>> event = await repo.mark_processed(event_id)
        """
        try:
            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .values(
                    status="processed",
                    processed_at=datetime.utcnow()
                )
                .returning(Event)
            )
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error marking event {event_id} as processed: {e}")
            await self.session.rollback()
            raise
    
    async def get_by_type(self, event_type: str, limit: int = 100) -> List[Event]:
        """
        Get events by type.
        
        Args:
            event_type: Type of event
            limit: Maximum number of events to return
            
        Returns:
            List of Event instances
            
        Examples:
            >>> repo = EventRepository(session)
            >>> events = await repo.get_by_type("product_discovered", limit=50)
        """
        try:
            result = await self.session.execute(
                select(Event)
                .where(Event.event_type == event_type)
                .order_by(Event.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Error getting events by type {event_type}: {e}")
            raise


class APICacheRepository:
    """Repository for APICache model operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize APICacheRepository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached value by key if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
            
        Examples:
            >>> repo = APICacheRepository(session)
            >>> value = await repo.get("serpapi:product:B08EXAMPLE")
        """
        try:
            result = await self.session.execute(
                select(APICache)
                .where(
                    and_(
                        APICache.key == key,
                        APICache.expires_at > datetime.utcnow()
                    )
                )
            )
            cache = result.scalar_one_or_none()
            if cache:
                return cache.value
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            raise
    
    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> APICache:
        """
        Set cache value with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be stored as JSON)
            ttl: Time to live in seconds
            
        Returns:
            Created or updated APICache instance
            
        Examples:
            >>> repo = APICacheRepository(session)
            >>> cache = await repo.set(
            ...     "serpapi:product:B08EXAMPLE",
            ...     {"asin": "B08EXAMPLE", "price": 29.99},
            ...     ttl=3600
            ... )
        """
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            # Check if exists
            result = await self.session.execute(
                select(APICache).where(APICache.key == key)
            )
            cache = result.scalar_one_or_none()
            
            if cache:
                # Update existing
                cache.value = value
                cache.ttl = ttl
                cache.expires_at = expires_at
            else:
                # Create new
                cache = APICache(
                    key=key,
                    value=value,
                    ttl=ttl,
                    expires_at=expires_at
                )
                self.session.add(cache)
            
            await self.session.flush()
            await self.session.refresh(cache)
            return cache
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
            await self.session.rollback()
            raise
    
    async def delete_expired(self) -> int:
        """
        Delete expired cache entries.
        
        Returns:
            Number of deleted entries
            
        Examples:
            >>> repo = APICacheRepository(session)
            >>> deleted = await repo.delete_expired()
        """
        try:
            stmt = delete(APICache).where(APICache.expires_at < datetime.utcnow())
            result = await self.session.execute(stmt)
            await self.session.flush()
            count = result.rowcount
            logger.info(f"Deleted {count} expired cache entries")
            return count
        except Exception as e:
            logger.error(f"Error deleting expired cache: {e}")
            await self.session.rollback()
            raise

