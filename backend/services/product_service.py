#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Product Service - Business logic para productos.

Maneja operaciones de productos, descubrimiento y búsqueda.
"""

import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
import logging

from backend.models.product import (
    ProductResponse,
    ProductCreate,
    ProductUpdate,
    ProductSearchRequest,
    ProductDiscoveryRequest,
    ProductDiscoveryResponse,
    ProductListResponse
)
from backend.services.cache_service import CacheService
from backend.database.repository import ProductRepository
from backend.core.event_bus import EventBus, Event
from backend.api.config import settings

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service para operaciones de productos.
    
    Attributes:
        db: Async database session
        cache: Cache service
        repo: Product repository
    """
    
    def __init__(self, db: Optional[AsyncSession] = None, cache: Optional[CacheService] = None):
        """
        Initialize product service.
        
        Args:
            db: Async database session (optional)
            cache: Cache service (optional)
        """
        self.db = db
        self.cache = cache or CacheService()
        self.repo = ProductRepository(db) if db else None
    
    async def get_by_asin(self, asin: str) -> Optional[ProductResponse]:
        """
        Get product by ASIN.
        
        Checks cache first, then database.
        
        Args:
            asin: Product ASIN
            
        Returns:
            Product if found, None otherwise
        """
        if not self.repo:
            raise ValueError("Database session required")
        
        # Check cache first
        cache_key = self.cache.product_key(asin)
        cached = await self.cache.get(cache_key)
        
        if cached:
            logger.debug(f"Product {asin} found in cache")
            return ProductResponse(**cached)
        
        # Query from database
        product = await self.repo.get_by_asin(asin)
        if product:
            # Convert to response model
            product_dict = {
                "id": str(product.id),
                "asin": product.asin,
                "title": product.title,
                "price": float(product.price),
                "rating": product.rating,
                "reviews": product.reviews,
                "bsr": product.bsr,
                "category": product.category,
                "image_url": product.image_url,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
            }
            # Cache for future requests
            await self.cache.set(cache_key, product_dict, ttl=settings.cache_ttl_products)
            return ProductResponse(**product_dict)
        
        logger.debug(f"Product {asin} not found")
        return None
    
    async def search_products(self, request: ProductSearchRequest) -> ProductListResponse:
        """
        Search products with filters.
        
        Args:
            request: Search request with filters
            
        Returns:
            Paginated list of products
        """
        if not self.repo:
            raise ValueError("Database session required")
        
        # Generate cache key from search params
        import json
        cache_key = self.cache.search_key(
            json.dumps(request.model_dump(), sort_keys=True)
        )
        
        # Check cache
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug("Search results found in cache")
            return ProductListResponse(**cached)
        
        # Query database with filters
        filters = {}
        if request.keyword:
            filters["title"] = request.keyword
        if request.category:
            filters["category"] = request.category
        if request.min_price:
            filters["min_price"] = request.min_price
        if request.max_price:
            filters["max_price"] = request.max_price
        if request.min_rating:
            filters["min_rating"] = request.min_rating
        if request.max_bsr:
            filters["max_bsr"] = request.max_bsr
        
        db_products = await self.repo.search(filters)
        
        # Convert to response models
        products = []
        for product in db_products[request.offset:request.offset + request.limit]:
            products.append(ProductResponse(
                id=str(product.id),
                asin=product.asin,
                title=product.title,
                price=float(product.price),
                rating=product.rating,
                reviews=product.reviews,
                bsr=product.bsr,
                category=product.category,
                image_url=product.image_url,
                created_at=product.created_at.isoformat() if product.created_at else None,
                updated_at=product.updated_at.isoformat() if product.updated_at else None,
            ))
        
        total = len(db_products)
        
        result = ProductListResponse(
            products=products,
            total=total,
            limit=request.limit,
            offset=request.offset,
            has_more=total > (request.offset + request.limit)
        )
        
        # Cache results
        await self.cache.set(cache_key, result.model_dump(), ttl=300)  # 5 minutes
        
        return result
    
    async def create_product(self, product: ProductCreate) -> ProductResponse:
        """
        Create new product.
        
        Args:
            product: Product data
            
        Returns:
            Created product
            
        Raises:
            ValueError: If database session not available
        """
        if not self.repo:
            raise ValueError("Database session required")
        
        # Convert ProductCreate to dict for repository
        product_data = product.model_dump()
        # Map reviews_count to reviews
        product_data["reviews"] = product_data.pop("reviews_count", 0)
        product_data.pop("url", None)
        product_data.pop("search_keyword", None)
        product_data.pop("discovery_source", None)
        
        # Create in database
        db_product = await self.repo.create(product_data)
        
        # Convert to response model
        product_dict = {
            "id": str(db_product.id),
            "asin": db_product.asin,
            "title": db_product.title,
            "price": float(db_product.price),
            "rating": db_product.rating,
            "reviews_count": db_product.reviews,
            "bsr": db_product.bsr,
            "category": db_product.category,
            "image_url": db_product.image_url,
            "created_at": db_product.created_at.isoformat() if db_product.created_at else datetime.utcnow().isoformat(),
            "updated_at": db_product.updated_at.isoformat() if db_product.updated_at else datetime.utcnow().isoformat(),
        }
        
        response = ProductResponse(**product_dict)
        
        # Cache product
        cache_key = self.cache.product_key(product.asin)
        await self.cache.set(cache_key, product_dict, ttl=settings.cache_ttl_products)
        
        logger.info(f"Product {product.asin} created successfully")
        return response
    
    async def update_product(self, asin: str, product: ProductUpdate) -> Optional[ProductResponse]:
        """
        Update existing product.
        
        Args:
            asin: Product ASIN
            product: Updated data
            
        Returns:
            Updated product if found, None otherwise
            
        Raises:
            ValueError: If database session not available
        """
        if not self.repo:
            raise ValueError("Database session required")
        
        # Convert ProductUpdate to dict for repository
        update_data = product.model_dump(exclude_unset=True)
        # Map reviews_count to reviews if present
        if "reviews_count" in update_data:
            update_data["reviews"] = update_data.pop("reviews_count")
        update_data.pop("url", None)
        update_data.pop("search_keyword", None)
        update_data.pop("discovery_source", None)
        
        # Update in database
        db_product = await self.repo.update(asin, update_data)
        
        if not db_product:
            logger.warning(f"Product {asin} not found for update")
            return None
        
        # Convert to response model
        product_dict = {
            "id": str(db_product.id),
            "asin": db_product.asin,
            "title": db_product.title,
            "price": float(db_product.price),
            "rating": db_product.rating,
            "reviews_count": db_product.reviews,
            "bsr": db_product.bsr,
            "category": db_product.category,
            "image_url": db_product.image_url,
            "created_at": db_product.created_at.isoformat() if db_product.created_at else None,
            "updated_at": db_product.updated_at.isoformat() if db_product.updated_at else None,
        }
        
        response = ProductResponse(**product_dict)
        
        # Update cache
        cache_key = self.cache.product_key(asin)
        await self.cache.set(cache_key, product_dict, ttl=settings.cache_ttl_products)
        
        logger.info(f"Product {asin} updated successfully")
        return response
    
    async def delete_product(self, asin: str) -> bool:
        """
        Delete product.
        
        Args:
            asin: Product ASIN
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            ValueError: If database session not available
        """
        if not self.repo:
            raise ValueError("Database session required")
        
        # Delete from database
        deleted = await self.repo.delete(asin)
        
        if not deleted:
            logger.warning(f"Product {asin} not found for deletion")
            return False
        
        # Invalidate cache
        cache_key = self.cache.product_key(asin)
        await self.cache.delete(cache_key)
        
        logger.info(f"Product {asin} deleted successfully")
        return True
    
    async def start_discovery(self, request: ProductDiscoveryRequest) -> str:
        """
        Start product discovery process.
        
        Publishes event to Event Bus for Discovery Agent to process.
        
        Args:
            request: Discovery request
            
        Returns:
            Task ID for tracking
        """
        task_id = str(uuid.uuid4())
        
        # Store initial task status in cache BEFORE publishing event
        # (Agent will update this when it completes)
        await self.cache.set(
            f"discovery_task:{task_id}",
            {
                "task_id": task_id,
                "status": "pending",
                "started_at": datetime.utcnow().isoformat(),
                "request": request.model_dump()
            },
            ttl=3600  # 1 hour
        )
        logger.info(f"Discovery task {task_id} initialized")
        
        # Publish TrendDiscoveryRequested event to Event Bus
        try:
            from backend.core.event_bus import get_event_bus
            event_bus = get_event_bus()
            
            event = Event(
                event_type="TrendDiscoveryRequested",
                payload={
                    "task_id": task_id,
                    "budget": float(request.budget),
                    "categories": request.categories or [],
                    "exclude_keywords": request.exclude_keywords or [],
                    "min_demand_score": request.min_demand_score,
                    "max_competition": request.max_competition,
                    "auto_analyze": request.auto_analyze
                },
                source_agent="API"
            )
            
            if event_bus.connected or event_bus.using_fallback:
                await event_bus.publish(event)
                logger.info(f"Published TrendDiscoveryRequested event for task {task_id}")
            else:
                logger.warning("Event Bus not connected, skipping event publication")
        except Exception as e:
            logger.error(f"Failed to publish discovery event: {e}")
            # Continue anyway - task is stored in cache
        
        return task_id
    
    async def get_discovery_status(self, task_id: str) -> Optional[ProductDiscoveryResponse]:
        """
        Get discovery task status.
        
        Args:
            task_id: Discovery task ID
            
        Returns:
            Task status if found
        """
        cache_key = f"discovery_task:{task_id}"
        status = await self.cache.get(cache_key)
        
        if not status:
            return None
        
        return ProductDiscoveryResponse(
            task_id=status["task_id"],
            status=status["status"],
            products_found=status.get("products_found", 0),
            estimated_time=status.get("estimated_time"),
            message=status.get("message", "Task in progress"),
            products=status.get("products", [])  # Include discovered products
        )

