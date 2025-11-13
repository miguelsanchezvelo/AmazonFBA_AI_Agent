#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cache Service - Integración con core/cache_manager.py.

Wrapper del CacheManager existente para uso en servicios del backend.
"""

import sys
from pathlib import Path
import asyncio
from typing import Any, Optional
import logging

# Add parent directory to path to import from core
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.cache_manager import CacheManager
from backend.api.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service wrapper para CacheManager.
    
    Proporciona interfaz simplificada para usar caché en servicios del backend.
    
    Examples:
        >>> cache = CacheService()
        >>> await cache.set("product:B08N5WRWNW", product_data, ttl=3600)
        >>> data = await cache.get("product:B08N5WRWNW")
    """
    _shared_manager: CacheManager | None = None

    def __init__(self):
        """
        Initialize cache service.
        
        Crea instancia de CacheManager con configuración del settings.
        """
        if CacheService._shared_manager is None:
            CacheService._shared_manager = CacheManager(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db
            )

        self.manager = CacheService._shared_manager
        logger.info("Cache service initialized")

    async def connect(self) -> bool:
        """Ensure cache backend is ready, supporting memory fallback."""
        if self.manager.connected:
            return True

        if self.manager.use_memory_fallback:
            logger.info("Cache service using in-memory fallback")
            return True

        return False

    async def disconnect(self) -> None:
        """Close Redis connection if established."""
        if self.manager.redis_client and self.manager.connected:
            try:
                await asyncio.to_thread(self.manager.redis_client.close)
            except Exception as exc:  # pragma: no cover
                logger.warning("Cache disconnect error: %s", exc)

        self.manager.connected = False
        self.manager.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            return self.manager.get(key)
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Run sync operation in thread pool to avoid blocking
            result = await asyncio.to_thread(
                self.manager.set, 
                key, 
                value, 
                ttl=ttl or settings.cache_ttl_products
            )
            logger.info(f"Cache SET: {key} - Result: {result}")
            return result
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if successful
        """
        try:
            self.manager.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.
        
        Args:
            pattern: Pattern to match (e.g., "product:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            return self.manager.clear(pattern)
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        try:
            return self.manager.get_stats()
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}
    
    # Cache key generators for consistency
    
    @staticmethod
    def product_key(asin: str) -> str:
        """Generate cache key for product."""
        return f"product:{asin}"
    
    @staticmethod
    def analysis_key(asin: str) -> str:
        """Generate cache key for analysis."""
        return f"analysis:{asin}"
    
    @staticmethod
    def supplier_key(supplier_id: int) -> str:
        """Generate cache key for supplier."""
        return f"supplier:{supplier_id}"
    
    @staticmethod
    def inventory_key(asin: str) -> str:
        """Generate cache key for inventory."""
        return f"inventory:{asin}"
    
    @staticmethod
    def search_key(query: str) -> str:
        """Generate cache key for search."""
        import hashlib
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return f"search:{query_hash}"

