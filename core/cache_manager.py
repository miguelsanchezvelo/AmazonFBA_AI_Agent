#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Caché Inteligente con Redis
Reduce costos de API en 80%+ mediante caché automático
"""

import json
import hashlib
import functools
from typing import Any, Callable, Optional, Dict
from datetime import timedelta
import logging

# Redis imports
try:
    import redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️  Redis no disponible. Instalar con: pip install redis")

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Gestor de caché inteligente con Redis.
    
    Features:
    - Caché automático con decorators
    - Invalidación por TTL
    - Fallback a memoria si Redis no disponible
    - Serialización automática JSON
    - Key generation basado en parámetros
    
    Examples:
        >>> cache = CacheManager()
        >>> 
        >>> @cache.cached(ttl=3600, key_prefix="products")
        >>> def search_products(keyword: str):
        >>>     return expensive_api_call(keyword)
        >>>
        >>> # Primera llamada: hace request real
        >>> result1 = search_products("yoga mat")
        >>> 
        >>> # Segunda llamada: retorna de caché (instantáneo)
        >>> result2 = search_products("yoga mat")
    """
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        use_memory_fallback: bool = True
    ):
        """
        Inicializa el cache manager.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (opcional)
            use_memory_fallback: Si True, usa dict en memoria si Redis falla
        """
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Any] = {}
        self.use_memory_fallback = use_memory_fallback
        self.connected = False
        
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=host,
                    port=port,
                    db=db,
                    password=password,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                self.connected = True
                logger.info("✅ Conectado a Redis en %s:%s", host, port)
            except (RedisConnectionError, Exception) as e:
                logger.warning("⚠️  No se pudo conectar a Redis: %s", e)
                if use_memory_fallback:
                    logger.info("📦 Usando caché en memoria como fallback")
                self.redis_client = None
        else:
            logger.warning("⚠️  Redis no disponible. Usando caché en memoria")
    
    def _generate_cache_key(
        self, 
        prefix: str, 
        func_name: str, 
        args: tuple, 
        kwargs: dict
    ) -> str:
        """
        Genera clave única de caché basada en función y parámetros.
        
        Args:
            prefix: Prefijo para agrupar keys relacionadas
            func_name: Nombre de la función
            args: Argumentos posicionales
            kwargs: Argumentos nombrados
            
        Returns:
            Clave de caché única
        """
        # Crear representación determinística de parámetros
        params_str = json.dumps({
            'args': args,
            'kwargs': sorted(kwargs.items())
        }, sort_keys=True, default=str)
        
        # Hash para key más corta
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:12]
        
        return f"{prefix}:{func_name}:{params_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Obtiene valor del caché.
        
        Args:
            key: Clave de caché
            
        Returns:
            Valor cacheado o None si no existe
        """
        # Intentar Redis primero
        if self.connected and self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    logger.debug("✅ Cache HIT (Redis): %s", key)
                    return json.loads(value)
                logger.debug("❌ Cache MISS (Redis): %s", key)
                return None
            except Exception as e:
                logger.warning("Error obteniendo de Redis: %s", e)
        
        # Fallback a memoria
        if self.use_memory_fallback and key in self.memory_cache:
            logger.debug("✅ Cache HIT (Memory): %s", key)
            return self.memory_cache[key]
        
        logger.debug("❌ Cache MISS (Memory): %s", key)
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Guarda valor en caché.
        
        Args:
            key: Clave de caché
            value: Valor a cachear (debe ser JSON-serializable)
            ttl: Tiempo de vida en segundos (None = sin expiración)
            
        Returns:
            True si se guardó exitosamente
        """
        try:
            serialized_value = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.error("Error serializando valor para caché: %s", e)
            return False
        
        # Intentar guardar en Redis
        if self.connected and self.redis_client:
            try:
                if ttl:
                    self.redis_client.setex(key, ttl, serialized_value)
                else:
                    self.redis_client.set(key, serialized_value)
                logger.debug("💾 Guardado en Redis: %s (TTL: %s)", key, ttl)
                return True
            except Exception as e:
                logger.warning("Error guardando en Redis: %s", e)
        
        # Fallback a memoria
        if self.use_memory_fallback:
            self.memory_cache[key] = value
            logger.debug("💾 Guardado en Memory: %s", key)
            return True
        
        return False
    
    def delete(self, key: str) -> bool:
        """
        Elimina valor del caché.
        
        Args:
            key: Clave de caché
            
        Returns:
            True si se eliminó
        """
        deleted = False
        
        # Eliminar de Redis
        if self.connected and self.redis_client:
            try:
                deleted = bool(self.redis_client.delete(key))
            except Exception as e:
                logger.warning("Error eliminando de Redis: %s", e)
        
        # Eliminar de memoria
        if key in self.memory_cache:
            del self.memory_cache[key]
            deleted = True
        
        return deleted
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Limpia caché completamente o por patrón.
        
        Args:
            pattern: Patrón de keys a eliminar (ej: "serpapi:*")
            
        Returns:
            Número de keys eliminadas
        """
        count = 0
        
        if self.connected and self.redis_client:
            try:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        count = self.redis_client.delete(*keys)
                else:
                    self.redis_client.flushdb()
                    count = -1  # Indica flush completo
                logger.info("🗑️  Limpiadas %s keys de Redis", count)
            except Exception as e:
                logger.warning("Error limpiando Redis: %s", e)
        
        # Limpiar memoria
        if pattern:
            import fnmatch
            memory_keys = [
                k for k in self.memory_cache.keys() 
                if fnmatch.fnmatch(k, pattern)
            ]
            for key in memory_keys:
                del self.memory_cache[key]
            count += len(memory_keys)
        else:
            count += len(self.memory_cache)
            self.memory_cache.clear()
        
        return count
    
    def cached(
        self, 
        ttl: int = 3600,
        key_prefix: str = "cache",
        ignore_errors: bool = True
    ) -> Callable:
        """
        Decorator para cachear automáticamente resultados de funciones.
        
        Args:
            ttl: Tiempo de vida del caché en segundos (default: 1 hora)
            key_prefix: Prefijo para las keys de caché
            ignore_errors: Si True, retorna resultado sin caché si hay error
            
        Returns:
            Decorator function
            
        Examples:
            >>> @cache.cached(ttl=3600, key_prefix="api")
            >>> def expensive_api_call(param):
            >>>     return api.search(param)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generar cache key
                cache_key = self._generate_cache_key(
                    key_prefix,
                    func.__name__,
                    args,
                    kwargs
                )
                
                # Intentar obtener de caché
                try:
                    cached_result = self.get(cache_key)
                    if cached_result is not None:
                        logger.info(
                            "📦 Cache HIT: %s (ahorrando API call)", 
                            func.__name__
                        )
                        return cached_result
                except Exception as e:
                    logger.warning("Error obteniendo de caché: %s", e)
                    if not ignore_errors:
                        raise
                
                # Cache miss - ejecutar función
                logger.info("🌐 Cache MISS: %s (ejecutando función)", func.__name__)
                result = func(*args, **kwargs)
                
                # Guardar resultado en caché
                try:
                    self.set(cache_key, result, ttl=ttl)
                    logger.info(
                        "💾 Resultado cacheado: %s (TTL: %ds)", 
                        func.__name__, 
                        ttl
                    )
                except Exception as e:
                    logger.warning("Error guardando en caché: %s", e)
                    if not ignore_errors:
                        raise
                
                return result
            
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            Dict con estadísticas
        """
        stats = {
            'redis_connected': self.connected,
            'memory_cache_size': len(self.memory_cache),
            'using_fallback': self.use_memory_fallback and not self.connected
        }
        
        if self.connected and self.redis_client:
            try:
                info = self.redis_client.info('stats')
                stats.update({
                    'redis_total_keys': self.redis_client.dbsize(),
                    'redis_hits': info.get('keyspace_hits', 0),
                    'redis_misses': info.get('keyspace_misses', 0),
                })
                
                # Calcular hit rate
                hits = stats['redis_hits']
                misses = stats['redis_misses']
                total = hits + misses
                if total > 0:
                    stats['hit_rate'] = round(hits / total * 100, 2)
                else:
                    stats['hit_rate'] = 0.0
                    
            except Exception as e:
                logger.warning("Error obteniendo stats de Redis: %s", e)
        
        return stats


# Instancia global del cache manager
_global_cache = None

def get_cache() -> CacheManager:
    """
    Obtiene instancia global del cache manager (singleton).
    
    Returns:
        CacheManager instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager()
    return _global_cache


# Alias para uso más simple
cache = get_cache()


if __name__ == "__main__":
    # Demo del sistema de cache
    import time
    
    print("=" * 60)
    print("DEMO: Sistema de Cache Inteligente")
    print("=" * 60)
    
    # Crear cache manager
    cache_manager = CacheManager()
    
    # Funcion de ejemplo (simula API call lenta)
    @cache_manager.cached(ttl=10, key_prefix="demo")
    def slow_api_call(query: str) -> dict:
        """Simula una API call que toma tiempo."""
        print(f"  -> Ejecutando API call para: {query}")
        time.sleep(2)  # Simula latencia
        return {
            'query': query,
            'results': [f'Result {i} for {query}' for i in range(3)],
            'timestamp': time.time()
        }
    
    # Primera llamada - cache miss
    print("\n1. Primera llamada (cache miss):")
    start = time.time()
    result1 = slow_api_call("yoga mat")
    elapsed1 = time.time() - start
    print(f"  OK Completado en {elapsed1:.2f}s")
    print(f"  Resultado: {result1['results'][0]}")
    
    # Segunda llamada - cache hit
    print("\n2. Segunda llamada (cache hit):")
    start = time.time()
    result2 = slow_api_call("yoga mat")
    elapsed2 = time.time() - start
    print(f"  OK Completado en {elapsed2:.2f}s")
    print(f"  Resultado: {result2['results'][0]}")
    
    # Mostrar mejora
    if elapsed2 > 0:
        speedup = elapsed1 / elapsed2
        print(f"\nSpeedup: {speedup:.1f}x mas rapido con cache")
    else:
        print(f"\nSpeedup: INSTANTANEO (cache hit) - ahorro de {elapsed1:.2f}s")
    
    # Stats
    print("\nEstadisticas del cache:")
    stats = cache_manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nDemo completado exitosamente!")

